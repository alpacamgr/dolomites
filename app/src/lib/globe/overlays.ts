/**
 * Vector overlays on the globe (ADR 0005, contract 1.2):
 *  - plates/{age}.json at the nearest integer Ma, at radius 1.003 with depth
 *    test so lines hide behind the globe. Fetch, parse and lon/lat -> xyz
 *    conversion run in a worker; converted segment buffers are cached for
 *    +-5 Ma around the current age. GPU geometry and LineSegments2 objects are
 *    created lazily, only for styles that are switched on AND present at the
 *    shown age, so an age with nothing to draw has no line objects in the scene.
 *      boundaries by type, on by default. PALEOMAP has no topologies older
 *                 than 100 Ma: boundaryNote() says so, nothing is substituted.
 *                 Subduction polarity is "unknown" in the data: no teeth drawn.
 *      landmass   "Continental crust outline, PALEOMAP", off by default. Files
 *                 without a landmass feature fall back to the continent polygons
 *                 at lower opacity.
 *      continent  "Tectonic blocks, PALEOMAP", off by default, very faint.
 *      coastline  off by default (the PALEOMAP build has none).
 *  - the Dolomites marker (dot + ring, constant pixel size) and a short trail (last TRAIL_WINDOW_MA of drift)
 *    of the reconstructed path for ages older than the current one, from
 *    dolomites-path.json. Updating them per frame allocates nothing.
 */
import * as THREE from 'three';
import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
import { Line2 } from 'three/examples/jsm/lines/Line2.js';
import { LineGeometry } from 'three/examples/jsm/lines/LineGeometry.js';
import { lonLatToArray } from './geo';
import { buildPlateBuffers, PLATE_KINDS, type PlateKind } from './plates-geometry';
import type { PlatesRequest, PlatesResponse } from './plates.worker';
import { fetchJson } from './fetch-json';

export interface OverlaysConfig {
  showLandmass: boolean;
  showBlocks: boolean;
  showCoastlines: boolean;
  showBoundaries: boolean;
  showTrail: boolean;
  showMarker: boolean;
}

interface PlatesIndex { ages_ma: number[]; path_pattern?: string; model?: string }
interface PathSample { ma: number; lat: number; lon: number }
interface Meta { attribution?: unknown; label?: unknown }

const LINE_RADIUS = 1.003;
const TRAIL_RADIUS = 1.0045;
/** The trail shows only the last TRAIL_WINDOW_MA of drift before the displayed age, so it never
 *  runs across continents of that age (the full 300 Myr path is in an absolute frame). */
const TRAIL_WINDOW_MA = 30;
const MARKER_RADIUS = 1.006;
const CACHE_WINDOW = 5;
const PREFETCH = 3;
const MAX_JOBS = 2;
const MAX_ATTEMPTS = 4;
const BOUNDARY_KINDS: readonly PlateKind[] = ['subduction', 'ridge', 'transform', 'other'];

const STYLE: Record<PlateKind, { color: number; width: number; opacity: number }> = {
  // faint enough to give the paleogeography texture a coast to read against without overpowering it
  landmass: { color: 0xf7f3e8, width: 1.0, opacity: 0.28 },
  continent: { color: 0xe8eef8, width: 0.8, opacity: 0.16 },
  coastline: { color: 0xfbf7ea, width: 1.0, opacity: 0.5 },
  subduction: { color: 0xff6a4d, width: 1.6, opacity: 0.9 },
  ridge: { color: 0x7fd8ff, width: 1.3, opacity: 0.85 },
  transform: { color: 0xffd36e, width: 1.1, opacity: 0.85 },
  other: { color: 0xc9b8ff, width: 0.8, opacity: 0.3 },  // untyped PALEOMAP plate edges: kept (they are model boundaries) but visually recessive
};
const LANDMASS_FALLBACK_OPACITY = 0.3;

interface GeoEntry {
  age: number;
  state: 'loading' | 'ready' | 'error';
  segs: Partial<Record<PlateKind, Float32Array>>;
  geoms: Partial<Record<PlateKind, LineSegmentsGeometry>>;
  hasBoundaries: boolean;
  attempts: number;
  retryAt: number;
}

export class Overlays {
  readonly group = new THREE.Group();
  private readonly lines: Partial<Record<PlateKind, LineSegments2>> = {};
  private readonly cache = new Map<number, GeoEntry>();
  private ages: number[] = [];
  private pattern = 'plates/{age}.json';
  private modelName = 'plate';
  private attributionText: string | null = null;
  private boundaryNoteText = '';
  private indexState: 'idle' | 'loading' | 'ready' | 'failed' = 'idle';
  private timeKnown = false;
  private shownAge = -1;
  private targetAge = -1;
  private direction: 1 | -1 = -1;
  private lastMa = 0;
  private resW = 1;
  private resH = 1;
  private readonly config: OverlaysConfig = {
    showLandmass: false, showBlocks: false, showCoastlines: false, showBoundaries: true, showTrail: true, showMarker: true,
  };

  private worker: Worker | null = null;
  private readonly jobs = new Map<number, (r: PlatesResponse) => void>();
  private jobId = 0;
  private activeJobs = 0;
  private retryTimer = 0;
  private disposed = false;

  private pathMa: Float32Array | null = null;
  private pathUnit: Float32Array | null = null;
  private pathIdx = 0;
  private readonly marker = new THREE.Group();
  private readonly trailMaterial: LineMaterial;
  private trail: Line2 | null = null;
  private trailBase: Float32Array | null = null;
  private trailEdited = -1;
  private trailStart = 0; // first visible trail segment (older segments are collapsed)
  private readonly tmp = new THREE.Vector3();

  constructor(private readonly globeBase: string, private readonly onChanged: () => void) {
    this.group.name = 'overlays';
    this.trailMaterial = new LineMaterial({
      color: 0xffd24a, linewidth: 1.6, opacity: 0.5, transparent: true, depthTest: true, depthWrite: false, worldUnits: false,
    });
    this.buildMarker();
  }

  /** Load index, meta and the Dolomites path (small JSON). Geometry loads on setAge. */
  async load(): Promise<void> {
    if (this.indexState !== 'idle') return;
    this.indexState = 'loading';
    const b = this.globeBase;
    const [idx, meta, path] = await Promise.all([
      fetchJson<PlatesIndex>(`${b}/plates/index.json`).catch((e) => { console.warn('[globe] plates index unavailable', e); return null; }),
      fetchJson<Meta>(`${b}/plates/meta.json`).catch(() => null),
      fetchJson<{ samples?: PathSample[] }>(`${b}/dolomites-path.json`).catch(() => null),
    ]);
    if (this.disposed) return;
    if (idx && Array.isArray(idx.ages_ma)) {
      this.ages = idx.ages_ma.filter((a) => Number.isFinite(a)).sort((x, y) => x - y);
      if (idx.path_pattern) this.pattern = idx.path_pattern;
      if (idx.model) this.modelName = /paleomap/i.test(idx.model) ? 'PALEOMAP' : idx.model;
    }
    this.boundaryNoteText = `Plate boundaries: not available for this age in the ${this.modelName} model`;
    this.attributionText = formatAttribution(meta);
    if (path?.samples?.length) this.setPath(path.samples);
    this.indexState = this.ages.length ? 'ready' : 'failed';
    this.initWorker();
    if (this.timeKnown) this.setAge(this.lastMa, this.direction, true);
    this.onChanged();
  }

  setAge(ma: number, direction: 1 | -1, force = false): void {
    this.lastMa = ma;
    this.direction = direction;
    this.timeKnown = true;
    this.updateDolomites(ma);
    if (!this.ages.length) return;
    const want = this.nearestAge(Math.round(ma));
    if (want === this.targetAge && !force) return;
    this.targetAge = want;
    const e = this.cache.get(want);
    if (e && e.state === 'ready') this.show(e);
    this.pump();
  }

  isLoading(): boolean {
    if (this.indexState === 'loading') return true;
    if (!this.timeKnown || this.targetAge < 0 || this.targetAge === this.shownAge) return false;
    const e = this.cache.get(this.targetAge);
    return !(e && e.state === 'error' && e.attempts >= MAX_ATTEMPTS);
  }

  shownPlatesAge(): number | null { return this.shownAge >= 0 ? this.shownAge : null; }

  /** Number of line objects currently in the scene (dev stats). */
  lineObjects(): number {
    let n = 0;
    for (const k of PLATE_KINDS) if (this.lines[k]?.parent) n++;
    return n;
  }

  anyVisible(): boolean {
    const c = this.config;
    return c.showLandmass || c.showBlocks || c.showCoastlines || c.showBoundaries || c.showTrail || c.showMarker;
  }

  /** Cached display string (no allocation per call). */
  attribution(): string | null { return this.attributionText; }

  /** Status line when boundaries are switched on but the model has none at the shown age. */
  boundaryNote(): string | null {
    if (!this.config.showBoundaries || this.shownAge < 0) return null;
    const e = this.cache.get(this.shownAge);
    return e && !e.hasBoundaries ? this.boundaryNoteText : null;
  }

  setConfig(c: Partial<OverlaysConfig>) {
    Object.assign(this.config, c);
    this.refresh();
    this.onChanged();
  }

  setResolution(width: number, height: number) {
    this.resW = width;
    this.resH = height;
    for (const k of PLATE_KINDS) (this.lines[k]?.material as LineMaterial | undefined)?.resolution.set(width, height);
    this.trailMaterial.resolution.set(width, height);
  }

  /** World units per CSS pixel near the sub-camera point; keeps the marker ~constant on screen. */
  setMarkerScale(worldPerPx: number) {
    this.marker.scale.setScalar(worldPerPx);
  }

  /** Drop cached geometry except what is on screen (pause()). */
  releaseCache() {
    for (const [age, e] of Array.from(this.cache.entries())) {
      if (age === this.shownAge || e.state === 'loading') continue;
      disposeEntry(e);
      this.cache.delete(age);
    }
  }

  dispose() {
    this.disposed = true;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.worker?.terminate();
    this.worker = null;
    this.jobs.clear();
    for (const e of this.cache.values()) disposeEntry(e);
    this.cache.clear();
    for (const k of PLATE_KINDS) (this.lines[k]?.material as LineMaterial | undefined)?.dispose();
    this.trail?.geometry.dispose();
    this.trailMaterial.dispose();
    this.marker.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (mesh.isMesh) { mesh.geometry.dispose(); (mesh.material as THREE.Material).dispose(); }
    });
    this.group.clear();
  }

  // ---------------------------------------------------------------- plates

  private geomFor(e: GeoEntry, k: PlateKind): LineSegmentsGeometry | null {
    const have = e.geoms[k];
    if (have) return have;
    const arr = e.segs[k];
    if (!arr || arr.length < 6) return null;
    const g = new LineSegmentsGeometry();
    g.setPositions(arr);
    e.geoms[k] = g;
    return g;
  }

  /** Attach exactly the line objects that have something to draw; detach the rest. */
  private refresh() {
    const c = this.config;
    const e = this.shownAge >= 0 ? this.cache.get(this.shownAge) : undefined;
    const landSrc: PlateKind | null = !e ? null : e.segs.landmass ? 'landmass' : e.segs.continent ? 'continent' : null;
    const fallback = landSrc === 'continent';
    for (const k of PLATE_KINDS) {
      let on: boolean;
      let src: PlateKind = k;
      if (k === 'landmass') { on = c.showLandmass && !!landSrc && !(fallback && c.showBlocks); src = landSrc ?? k; }
      else if (k === 'continent') on = c.showBlocks;
      else if (k === 'coastline') on = c.showCoastlines;
      else on = c.showBoundaries;
      const g = on && e ? this.geomFor(e, src) : null;
      let line = this.lines[k];
      if (g) {
        if (!line) {
          const s = STYLE[k];
          const m = new LineMaterial({
            color: s.color, linewidth: s.width, opacity: s.opacity, transparent: true,
            depthTest: true, depthWrite: false, worldUnits: false,
          });
          m.resolution.set(this.resW, this.resH);
          line = new LineSegments2(g, m);
          line.frustumCulled = false;
          line.renderOrder = BOUNDARY_KINDS.includes(k) ? 3 : 2;
          this.lines[k] = line;
        }
        line.geometry = g;
        if (k === 'landmass') (line.material as LineMaterial).opacity = fallback ? LANDMASS_FALLBACK_OPACITY : STYLE.landmass.opacity;
        if (!line.parent) this.group.add(line);
      } else if (line?.parent) {
        this.group.remove(line);
      }
    }
    if (this.trail) this.trail.visible = c.showTrail;
    this.marker.visible = c.showMarker && this.pathMa !== null;
  }

  private nearestAge(ma: number): number {
    const a = this.ages;
    let lo = 0, hi = a.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (a[mid] < ma) lo = mid + 1; else hi = mid;
    }
    if (lo > 0 && Math.abs(a[lo - 1] - ma) <= Math.abs(a[lo] - ma)) lo--;
    return a[lo];
  }

  private show(e: GeoEntry) {
    this.shownAge = e.age;
    this.refresh();
    this.onChanged();
  }

  private pump() {
    if (this.disposed || !this.ages.length || this.targetAge < 0 || this.indexState !== 'ready') return;
    const idx = this.ages.indexOf(this.targetAge);
    const now = performance.now();
    for (let k = 0; k <= PREFETCH && this.activeJobs < MAX_JOBS; k++) {
      const i = idx + k * this.direction;
      if (i < 0 || i >= this.ages.length) break;
      const age = this.ages[i];
      const e = this.cache.get(age);
      if (e && (e.state !== 'error' || e.attempts >= MAX_ATTEMPTS || now < e.retryAt)) continue;
      this.start(age, e);
    }
  }

  private start(age: number, prev: GeoEntry | undefined) {
    const e: GeoEntry = prev ?? { age, state: 'loading', segs: {}, geoms: {}, hasBoundaries: false, attempts: 0, retryAt: 0 };
    e.state = 'loading';
    this.cache.set(age, e);
    this.activeJobs++;
    const rel = this.pattern.replace('{age}', String(age)).replace(/^globe\//, '');
    void this.runJob(`${this.globeBase}/${rel}`, e.attempts > 0).then((res) => {
      this.activeJobs--;
      if (this.disposed) return;
      if (this.cache.get(age) === e) {
        if (res.ok) {
          for (const k of PLATE_KINDS) {
            const arr = res.segments[k];
            if (arr && arr.length >= 6) e.segs[k] = arr;
          }
          e.hasBoundaries = BOUNDARY_KINDS.some((k) => !!e.segs[k]);
          e.state = 'ready';
          const closer = this.shownAge < 0 || Math.abs(age - this.targetAge) < Math.abs(this.shownAge - this.targetAge);
          if (age === this.targetAge || closer) this.show(e);
        } else {
          // Typically a file caught mid-rewrite by the pipeline: retry with backoff.
          e.state = 'error';
          e.attempts++;
          e.retryAt = performance.now() + 400 * e.attempts;
          if (e.attempts >= MAX_ATTEMPTS) console.warn(`[globe] plates ${age} Ma unavailable: ${res.error}`);
          else if (!this.retryTimer) this.retryTimer = window.setTimeout(() => { this.retryTimer = 0; this.pump(); }, 450 * e.attempts);
        }
      }
      this.prune();
      this.pump();
      this.onChanged();
    });
  }

  private prune() {
    for (const [age, e] of Array.from(this.cache.entries())) {
      if (e.state === 'loading' || age === this.shownAge) continue;
      if (Math.abs(age - this.targetAge) > CACHE_WINDOW) {
        disposeEntry(e);
        this.cache.delete(age);
      }
    }
  }

  private initWorker() {
    if (this.worker || typeof Worker === 'undefined') return;
    try {
      const w = new Worker(new URL('./plates.worker.ts', import.meta.url), { type: 'module' });
      w.onmessage = (ev: MessageEvent<PlatesResponse>) => {
        const cb = this.jobs.get(ev.data.id);
        if (cb) { this.jobs.delete(ev.data.id); cb(ev.data); }
      };
      w.onerror = (ev) => {
        console.warn('[globe] plates worker failed; converting on the main thread', ev.message);
        w.terminate();
        this.worker = null;
        for (const [id, cb] of Array.from(this.jobs.entries())) cb({ id, ok: false, error: 'worker error' });
        this.jobs.clear();
      };
      this.worker = w;
    } catch {
      this.worker = null;
    }
  }

  private runJob(url: string, reload: boolean): Promise<PlatesResponse> {
    const id = ++this.jobId;
    const w = this.worker;
    if (w) {
      return new Promise((resolve) => {
        this.jobs.set(id, resolve);
        const req: PlatesRequest = { id, url, radius: LINE_RADIUS, reload };
        w.postMessage(req);
      });
    }
    return (async (): Promise<PlatesResponse> => {
      try {
        const r = await fetch(url, reload ? { cache: 'reload' } : undefined);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const { segments } = buildPlateBuffers(JSON.parse(await r.text()), LINE_RADIUS);
        return { id, ok: true, segments };
      } catch (err) {
        return { id, ok: false, error: String(err) };
      }
    })();
  }

  // ------------------------------------------------------------- Dolomites

  private buildMarker() {
    const mat = (color: number, opacity: number) =>
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, side: THREE.DoubleSide });
    // Geometry in CSS pixels; setMarkerScale converts to world units.
    const halo = new THREE.Mesh(new THREE.RingGeometry(3.2, 9.5, 40), mat(0x0b0f18, 0.35));
    const ring = new THREE.Mesh(new THREE.RingGeometry(6.4, 8.2, 40), mat(0xffd24a, 0.95));
    const dot = new THREE.Mesh(new THREE.CircleGeometry(3.0, 24), mat(0xffd24a, 1));
    halo.renderOrder = 5;
    ring.renderOrder = 6;
    dot.renderOrder = 6;
    this.marker.add(halo, ring, dot);
    this.marker.visible = false;
    this.marker.scale.setScalar(0.001);
    this.group.add(this.marker);
  }

  private setPath(samples: PathSample[]) {
    const s = samples
      .filter((x) => Number.isFinite(x.ma) && Number.isFinite(x.lat) && Number.isFinite(x.lon))
      .sort((a, b) => a.ma - b.ma);
    const n = s.length;
    if (!n) return;
    this.pathMa = Float32Array.from(s, (x) => x.ma);
    this.pathUnit = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) lonLatToArray(s[i].lon, s[i].lat, this.pathUnit, i * 3);
    if (n >= 2) {
      // Points ordered oldest -> youngest, so instanceCount trims the young end.
      const pts = new Float32Array(n * 3);
      for (let j = 0; j < n; j++) {
        const k = (n - 1 - j) * 3;
        pts[j * 3] = this.pathUnit[k] * TRAIL_RADIUS;
        pts[j * 3 + 1] = this.pathUnit[k + 1] * TRAIL_RADIUS;
        pts[j * 3 + 2] = this.pathUnit[k + 2] * TRAIL_RADIUS;
      }
      const geom = new LineGeometry();
      geom.setPositions(pts);
      this.trail = new Line2(geom, this.trailMaterial);
      this.trail.frustumCulled = false;
      this.trail.renderOrder = 4;
      const buf = (geom.attributes.instanceStart as THREE.InterleavedBufferAttribute).data;
      this.trailBase = (buf.array as Float32Array).slice();
      this.trailStart = 0;
      this.group.add(this.trail);
    }
    this.updateDolomites(this.lastMa);
    this.refresh();
  }

  private updateDolomites(ma: number) {
    const pm = this.pathMa;
    const pu = this.pathUnit;
    if (!pm || !pu) return;
    const n = pm.length;
    let i = 0;
    let t = 0;
    if (n > 1) {
      i = Math.min(this.pathIdx, n - 2);
      while (i > 0 && pm[i] > ma) i--;
      while (i < n - 2 && pm[i + 1] < ma) i++;
      this.pathIdx = i;
      const span = pm[i + 1] - pm[i];
      t = span > 0 ? Math.min(1, Math.max(0, (ma - pm[i]) / span)) : 0;
    }
    const o = i * 3;
    const o2 = n > 1 ? o + 3 : o;
    this.tmp.set(
      pu[o] + (pu[o2] - pu[o]) * t,
      pu[o + 1] + (pu[o2 + 1] - pu[o + 1]) * t,
      pu[o + 2] + (pu[o2 + 2] - pu[o + 2]) * t,
    ).normalize();
    this.marker.position.copy(this.tmp).multiplyScalar(MARKER_RADIUS);
    this.marker.lookAt(0, 0, 0);

    const trail = this.trail;
    const base = this.trailBase;
    if (!trail || !base || n < 2) return;
    const buf = (trail.geometry.attributes.instanceStart as THREE.InterleavedBufferAttribute).data;
    const arr = buf.array as Float32Array;
    const j = n - 2 - i; // segment that ends at the younger sample i
    const prevEdited = this.trailEdited;
    if (this.trailEdited >= 0 && this.trailEdited !== j) {
      const r = this.trailEdited * 6 + 3;
      arr[r] = base[r]; arr[r + 1] = base[r + 1]; arr[r + 2] = base[r + 2];
      buf.addUpdateRange(r, 3);
    }
    const w = j * 6 + 3;
    arr[w] = this.tmp.x * TRAIL_RADIUS;
    arr[w + 1] = this.tmp.y * TRAIL_RADIUS;
    arr[w + 2] = this.tmp.z * TRAIL_RADIUS;
    buf.addUpdateRange(w, 3);
    buf.needsUpdate = true;
    this.trailEdited = j;

    // Window: segments whose older end lies more than TRAIL_WINDOW_MA before `ma` are hidden by moving both
    // of their ends onto the window's first point. Zero-length Line2 segments still draw a round dot, so they
    // must all sit on one spot that the visible trail already covers.
    const limit = ma + TRAIL_WINDOW_MA;
    let lo = 0;
    let hi = n - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (pm[mid] <= limit) lo = mid; else hi = mid - 1; }
    const start = Math.min(n - 1 - lo, j);
    if (start !== this.trailStart || (prevEdited >= 0 && prevEdited < start)) {
      const s6 = start * 6;
      const px = base[s6];
      const py = base[s6 + 1];
      const pz = base[s6 + 2];
      for (let k = 0; k < start; k++) {
        const o6 = k * 6;
        arr[o6] = px; arr[o6 + 1] = py; arr[o6 + 2] = pz;
        arr[o6 + 3] = px; arr[o6 + 4] = py; arr[o6 + 5] = pz;
      }
      for (let k = start; k < this.trailStart; k++) { // visible again: restore from the base copy
        const o6 = k * 6;
        const count = k === j ? 3 : 6; // keep the current segment's end on the marker
        for (let q = 0; q < count; q++) arr[o6 + q] = base[o6 + q];
      }
      buf.addUpdateRange(0, Math.max(start, this.trailStart) * 6);
      buf.needsUpdate = true;
      this.trailStart = start;
    }
    trail.geometry.instanceCount = j + 1;
  }
}

function formatAttribution(meta: Meta | null): string | null {
  if (!meta || meta.attribution == null) return null;
  const text = typeof meta.attribution === 'string'
    ? meta.attribution
    : Object.values(meta.attribution as Record<string, unknown>).map(String).join(' ');
  const label = typeof meta.label === 'string' ? meta.label : 'modeled';
  // meta.json strings may already start with a layer name ("Plate reconstruction: ...")
  const named = /^[A-Z][A-Za-z ]{2,40}:\s/.test(text) ? text : `Plate reconstruction: ${text}`;
  return `${named} (${label})`;
}

function disposeEntry(e: GeoEntry) {
  for (const k of PLATE_KINDS) e.geoms[k]?.dispose();
  e.geoms = {};
  e.segs = {};
}
