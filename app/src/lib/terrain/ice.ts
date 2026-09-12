/**
 * Ice frames (contract 2.3): two image sources (A/B) with raster layers stacked
 * over the terrain. A new frame is decoded off-screen first, re-ramped for
 * display, uploaded into the hidden buffer, and the two layers crossfade with a
 * GPU paint transition, so scrubbing never shows a half-loaded frame. Only the
 * latest requested frame is applied; neighbours are preloaded (bounded cache).
 *
 * Display ramp: the published frames are colourised with `thickness_stops_m`
 * from index.json, whose alpha rises monotonically with thickness. Each pixel's
 * alpha is inverted back to thickness through those stops and re-coloured with
 * ICE_DISPLAY_STOPS (brighter, stronger alpha for thick ice). The model values
 * are unchanged; only the colour ramp differs, at 8-bit alpha precision.
 */
import type * as maplibregl from 'maplibre-gl';
import type { IceIndex } from './data';
import { ICE_DISPLAY_STOPS } from './palette';

const CROSSFADE_MS = 160;
const PRELOAD_RADIUS = 4;
const CACHE_MAX = 40;
const EMPTY_PNG =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

type Buf = 'a' | 'b';
type Quad = [[number, number], [number, number], [number, number], [number, number]];
type Rgba = [number, number, number, number];

function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }

/** Piecewise-linear lookup in ascending [x, value] stops. */
function sample<T extends number[]>(stops: Array<[number, T]>, x: number): number[] {
  if (x <= stops[0][0]) return stops[0][1];
  for (let i = 1; i < stops.length; i++) {
    const [x1, v1] = stops[i];
    if (x <= x1) {
      const [x0, v0] = stops[i - 1];
      const t = (x - x0) / (x1 - x0 || 1);
      return v0.map((v, k) => lerp(v, v1[k], t));
    }
  }
  return stops[stops.length - 1][1];
}

/** 256-entry RGBA lookup table from source alpha to display colour. */
function buildLut(sourceStops: IceIndex['thickness_stops_m']): Uint8ClampedArray | null {
  if (!sourceStops || sourceStops.length < 2) return null;
  // source alpha (0..255) -> thickness, from the stops' alpha channel
  const alphaToThickness: Array<[number, [number]]> = [];
  for (const [m, c] of sourceStops) {
    const a = Array.isArray(c) ? Number(c[3]) : NaN;
    if (!Number.isFinite(a)) return null;
    if (alphaToThickness.length && a <= alphaToThickness[alphaToThickness.length - 1][0]) continue;
    alphaToThickness.push([a, [m]]);
  }
  if (alphaToThickness.length < 2) return null;
  const lut = new Uint8ClampedArray(256 * 4);
  for (let a = 1; a < 256; a++) {
    const thickness = sample(alphaToThickness, a)[0];
    const [r, g, b, alpha] = sample(ICE_DISPLAY_STOPS as Array<[number, Rgba]>, thickness);
    lut.set([r, g, b, Math.round(alpha * 255)], a * 4);
  }
  return lut;
}

export class IceManager {
  private readonly map: maplibregl.Map;
  private readonly index: IceIndex;
  private readonly base: string;
  private readonly quad: Quad;
  private readonly ages: number[];
  private readonly lut: Uint8ClampedArray | null;
  private opacity = 1;
  private visible = false;
  private front: Buf = 'a';
  private shownAge: number | null = null;
  private wantedAge: number | null = null;
  private token = 0;
  private disposed = false;
  private refreshUntil = 0;
  private refreshing = false;
  /** insertion-ordered LRU of display-ready frames */
  private cache = new Map<number, Promise<ImageData | HTMLImageElement | null>>();
  /**
   * Resolves once both sources finished loading their placeholder URL. An
   * updateImage() issued before that is overwritten when the placeholder
   * load completes, leaving the layer blank.
   */
  private readonly ready: Promise<void>;

  constructor(map: maplibregl.Map, base: string, index: IceIndex, beforeId?: string) {
    this.map = map;
    this.base = base;
    this.index = index;
    this.ages = [...index.ages_ka].sort((x, y) => x - y);
    this.lut = buildLut(index.thickness_stops_m);
    if (!this.lut) console.info('[terrain.ice] no usable thickness_stops_m; showing frames as published');
    const [w, s, e, n] = index.bounds;
    // MapLibre corner order: top-left, top-right, bottom-right, bottom-left.
    this.quad = [[w, n], [e, n], [e, s], [w, s]];
    for (const b of ['a', 'b'] as Buf[]) {
      map.addSource(`ice-${b}`, { type: 'image', url: EMPTY_PNG, coordinates: this.quad });
      map.addLayer({
        id: `ice-${b}`,
        type: 'raster',
        source: `ice-${b}`,
        layout: { visibility: 'none' },
        paint: {
          'raster-opacity': 0,
          'raster-opacity-transition': { duration: CROSSFADE_MS, delay: 0 },
          'raster-fade-duration': 0,
          'raster-resampling': 'linear',
        },
      }, beforeId);
    }
    this.ready = Promise.all((['a', 'b'] as Buf[]).map((b) => new Promise<void>((resolve) => {
      const id = `ice-${b}`;
      const check = () => {
        if (!(map.getSource(id) as maplibregl.ImageSource | undefined)?.loaded()) return false;
        map.off('sourcedata', onData);
        resolve();
        return true;
      };
      const onData = (e: maplibregl.MapSourceDataEvent) => { if (e.sourceId === id) check(); };
      map.on('sourcedata', onData);
      check();
    }))).then(() => undefined);
  }

  get range(): [number, number] { return [this.ages[0], this.ages[this.ages.length - 1]]; }

  nearestAge(ka: number): number | null {
    const a = this.ages;
    if (!a.length) return null;
    let lo = 0, hi = a.length - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (a[mid] <= ka) lo = mid; else hi = mid; }
    return Math.abs(a[lo] - ka) <= Math.abs(a[hi] - ka) ? a[lo] : a[hi];
  }

  private url(age: number): string {
    return `${this.base}/${this.index.path_pattern.replace('{ka}', String(age))}`;
  }

  private recolor(img: HTMLImageElement): ImageData | HTMLImageElement {
    const lut = this.lut;
    if (!lut) return img;
    const w = img.naturalWidth, h = img.naturalHeight;
    const canvas = new OffscreenCanvas(w, h);
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) return img;
    ctx.drawImage(img, 0, 0);
    const data = ctx.getImageData(0, 0, w, h);
    const px = data.data;
    for (let i = 0; i < px.length; i += 4) {
      const j = px[i + 3] * 4;
      px[i] = lut[j]; px[i + 1] = lut[j + 1]; px[i + 2] = lut[j + 2]; px[i + 3] = lut[j + 3];
    }
    return data;
  }

  private load(age: number): Promise<ImageData | HTMLImageElement | null> {
    const hit = this.cache.get(age);
    if (hit) { this.cache.delete(age); this.cache.set(age, hit); return hit; }
    const p = new Promise<ImageData | HTMLImageElement | null>((resolve) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.src = this.url(age);
      img.decode().then(() => resolve(this.recolor(img)), () => {
        console.info(`[terrain.ice] frame ${age} ka missing`);
        resolve(null);
      });
    });
    this.cache.set(age, p);
    while (this.cache.size > CACHE_MAX) this.cache.delete(this.cache.keys().next().value as number);
    return p;
  }

  /** Decode frames around `ka` without showing them. */
  preload(ka: number): Promise<unknown> {
    const age = this.nearestAge(ka);
    if (age == null) return Promise.resolve();
    const i = this.ages.indexOf(age);
    const jobs: Promise<unknown>[] = [this.load(age)];
    for (let k = 1; k <= PRELOAD_RADIUS; k++) {
      if (i - k >= 0) jobs.push(this.load(this.ages[i - k]));
      if (i + k < this.ages.length) jobs.push(this.load(this.ages[i + k]));
    }
    return Promise.all(jobs);
  }

  /**
   * With 3D terrain MapLibre caches each terrain tile's layers in a render-to-texture
   * that is only invalidated by tile data events. An image-source updateImage() and
   * raster-opacity changes do not trigger one, so the ice would lag a frame behind at
   * a fixed camera. Release the cache every frame while a crossfade runs.
   */
  private refreshTerrain(ms: number) {
    this.refreshUntil = Math.max(this.refreshUntil, performance.now() + ms);
    if (this.refreshing) return;
    this.refreshing = true;
    const tick = () => {
      if (this.disposed) { this.refreshing = false; return; }
      this.map.terrain?.tileManager.releaseAllRTT();
      this.map.triggerRepaint();
      if (performance.now() < this.refreshUntil) requestAnimationFrame(tick);
      else this.refreshing = false;
    };
    tick();
  }

  setVisible(v: boolean) {
    if (v === this.visible) return;
    this.visible = v;
    for (const b of ['a', 'b'] as Buf[]) this.map.setLayoutProperty(`ice-${b}`, 'visibility', v ? 'visible' : 'none');
    this.refreshTerrain(0);
  }

  setOpacity(o: number) {
    const next = Math.max(0, Math.min(1, o));
    if (next === this.opacity) return;
    this.opacity = next;
    if (this.shownAge != null) {
      this.map.setPaintProperty(`ice-${this.front}`, 'raster-opacity', this.opacity);
      this.refreshTerrain(CROSSFADE_MS + 60);
    }
  }

  /** Show the frame nearest to `ka`; resolves when applied (or superseded). */
  async setTime(ka: number): Promise<void> {
    const age = this.nearestAge(ka);
    if (age == null || age === this.wantedAge) return;
    this.wantedAge = age;
    const my = ++this.token;
    void this.preload(age);
    const [img] = await Promise.all([this.load(age), this.ready]);
    if (this.disposed || my !== this.token || !img) return;
    const back: Buf = this.front === 'a' ? 'b' : 'a';
    const src = this.map.getSource(`ice-${back}`) as maplibregl.ImageSource | undefined;
    if (!src) return;
    src.updateImage({ image: img, coordinates: this.quad });
    this.map.setPaintProperty(`ice-${back}`, 'raster-opacity', this.opacity);
    this.map.setPaintProperty(`ice-${this.front}`, 'raster-opacity', 0);
    this.front = back;
    this.shownAge = age;
    this.refreshTerrain(CROSSFADE_MS + 60);
  }

  dispose() {
    this.disposed = true;
    this.cache.clear();
    for (const b of ['a', 'b'] as Buf[]) {
      if (this.map.getLayer(`ice-${b}`)) this.map.removeLayer(`ice-${b}`);
      if (this.map.getSource(`ice-${b}`)) this.map.removeSource(`ice-${b}`);
    }
  }
}
