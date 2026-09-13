/**
 * Globe engine: a whole-Earth three.js scene that plays 300 Myr of
 * paleogeography (5 Myr texture slices) with plate-model overlays.
 * Implements SceneEngine (../scene-api.ts), kind 'globe'.
 *
 * Crossfade: for time t Ma, a = floor(t/5)*5, b = a+5, mix = (t-a)/5. The
 * shader samples both slices and mixes. The displayed pair only changes when
 * both textures of the new pair are on the GPU; until then the last valid pair
 * stays (leaning on the slice it shares with the wanted pair), and before the
 * first pair arrives the globe is a neutral shaded sphere that fades into the
 * paleogeography.
 *
 * Rendering on demand: requestAnimationFrame runs only while the camera
 * moves, a fade runs or a texture waits for upload; setTime/setCamera/loads
 * schedule single frames. Idle = no GPU work. The frame path allocates nothing.
 */
import * as THREE from 'three';
import type { SceneEngine, SceneState, EngineStatus, TimeUnit, GlobeCamera, TerrainCamera, LayerRef } from '../scene-api';
import { createStubEngine } from '../stub-engine';
import { globeVertexShader, globeFragmentShader, atmosphereVertexShader, atmosphereFragmentShader } from './shaders';
import { TextureStore, type TexturesIndex, type TexRequest } from './textures';
import { GlobeControls, type GlobeView } from './controls';
import { createStars } from './stars';
import { Overlays, type OverlaysConfig } from './overlays';
import { fetchJson } from './fetch-json';

export type { OverlaysConfig };

export interface GlobeOptions {
  /** base URL of the data directory, default '/data'. '/data/_sample' selects the labelled stand-in set. */
  dataBase?: string;
  /** force texture size; default picks by device */
  textureSize?: '4k' | '2k';
  /** atmosphere glow, default true */
  atmosphere?: boolean;
  /** normal-map lighting when the pipeline provides normal maps, default true */
  normalMaps?: boolean;
  /** procedural star background, default true */
  stars?: boolean;
  /** camera distance limits in Earth radii, default 1.6 and 4.0; the minimum is raised per viewport and texture size (ADR 0004, see applyDistanceLimits) */
  minDistance?: number;
  maxDistance?: number;
  /** disable user camera input (story controller), default false */
  locked?: boolean;
  /** devicePixelRatio cap, default and maximum 2 */
  maxPixelRatio?: number;
  /** expose internals as window.__globeDebug (dev page only) */
  debug?: boolean;
  /** prefers-reduced-motion: chapter camera changes jump instead of easing, default false */
  reduceMotion?: boolean;
  /** flat UI strings (content/ui) for the gesture hint; English fallbacks are built in */
  strings?: Record<string, string>;
}

export interface GlobeStats {
  renders: number;
  lastRenderMs: number;
  uploads: number;
  lastUploadMs: number;
  maxUploadMs: number;
  shownPair: [number, number] | null;
  overlayAge: number | null;
  /** plate line objects attached to the scene (0 when nothing to draw) */
  lineObjects: number;
  loading: boolean;
  size: '4k' | '2k';
}

/** Extra controls used by the dev page; the story controller only needs SceneEngine. */
export interface GlobeRuntime {
  setTextureSize(size: '4k' | '2k'): void;
  currentSize(): '4k' | '2k';
  setAtmosphereEnabled(v: boolean): void;
  setNormalMapsEnabled(v: boolean): void;
  setStarsEnabled(v: boolean): void;
  setOverlayConfig(c: Partial<OverlaysConfig>): void;
  setLocked(v: boolean): void;
  stats(): GlobeStats;
  /** reset the max upload time (dev scrub test) */
  resetUploadStats(): void;
}

const SLICE_MA = 5;
const FOV_DEG = 45;
const NORMAL_AMOUNT = 0.8;
const CAMERA_EASE_MS = 1200;
/** Framing floor: at least this much stage height is empty around the sphere (rail + legend + air).
 *  distance >= 1 / (FIT_FRACTION * tan(FOV / 2)) keeps the sphere at ≤ FIT_FRACTION of stage height. */
const FIT_FRACTION = 0.72;
/** Normal maps are requested only once a slice pair has been stable this long: halves GPU uploads while scrubbing. */
const NORMAL_DELAY_MS = 300;
const DEFAULT_VIEW: GlobeView = { lat: 20, lon: 10, distance: 2.6 };

interface TexMeta { attribution?: unknown; label?: unknown }
interface AttrEntry { min: number; max: number; text: string }

/** 4k where the drawing buffer is large enough to show it, 2k otherwise or on low-memory devices. */
export function pickTextureSize(): '4k' | '2k' {
  if (typeof window === 'undefined') return '2k';
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const longSide = Math.max(window.screen?.width ?? 0, window.screen?.height ?? 0) * dpr;
  const mem = (navigator as Navigator & { deviceMemory?: number }).deviceMemory;
  if (mem !== undefined && mem < 4) return '2k';
  return longSide >= 2000 ? '4k' : '2k';
}

function parseAgeRange(key: string): [number, number] | null {
  const m = /^(\d+(?:\.\d+)?)(?:\.\.(\d+(?:\.\d+)?))?\s*ma$/i.exec(key.trim());
  if (!m) return null;
  const a = parseFloat(m[1]);
  const b = m[2] ? parseFloat(m[2]) : a;
  return [Math.min(a, b), Math.max(a, b)];
}

/** meta.json attribution/label may be plain strings or objects keyed by age range ("0Ma", "5..300Ma"). */
function textureAttributions(meta: TexMeta | null): AttrEntry[] {
  if (!meta || meta.attribution == null) return [];
  const labels = meta.label;
  const labelOf = (k: string | null) =>
    typeof labels === 'string' ? labels
      : k && labels && typeof labels === 'object' ? String((labels as Record<string, unknown>)[k] ?? '') : '';
  if (typeof meta.attribution === 'string') {
    return [{ min: -Infinity, max: Infinity, text: `Paleogeography: ${meta.attribution} (${labelOf(null) || 'interpreted'})` }];
  }
  const out: AttrEntry[] = [];
  for (const [k, v] of Object.entries(meta.attribution as Record<string, unknown>)) {
    const r = parseAgeRange(k);
    const name = !r ? 'Paleogeography' : r[1] === 0 ? 'Present-day relief (0 Ma)' : `Paleogeography (${r[0]}-${r[1]} Ma)`;
    out.push({ min: r ? r[0] : -Infinity, max: r ? r[1] : Infinity, text: `${name}: ${String(v)} (${labelOf(k) || 'unlabelled'})` });
  }
  return out;
}

export function createGlobeEngine(options: GlobeOptions = {}): SceneEngine & GlobeRuntime {
  const dataBase = (options.dataBase ?? '/data').replace(/\/+$/, '');
  const globeBase = `${dataBase}/globe`;
  const maxPixelRatio = Math.min(2, options.maxPixelRatio ?? 2);
  const minDistance = options.minDistance ?? 1.6;
  const maxDistance = options.maxDistance ?? 4.0;

  let fallback: SceneEngine | null = null;
  let container: HTMLElement | null = null;
  let renderer: THREE.WebGLRenderer | null = null;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(FOV_DEG, 1, 0.05, 200);
  const lightDir = new THREE.Vector3(-0.5, 0.5, 0.7).normalize();
  let globeMat: THREE.ShaderMaterial | null = null;
  let atmoMat: THREE.ShaderMaterial | null = null;
  let globeMesh: THREE.Mesh | null = null;
  let atmoMesh: THREE.Mesh | null = null;
  let stars: THREE.Points | null = null;
  let blankTex: THREE.DataTexture | null = null;
  let flatNormalTex: THREE.DataTexture | null = null;
  let controls: GlobeControls | null = null;
  let overlays: Overlays | null = null;
  let store: TextureStore | null = null;
  let ro: ResizeObserver | null = null;
  let viewportH = 1;
  let locked = !!options.locked;

  let texIndex: TexturesIndex | null = null;
  let ageSet = new Set<number>();
  let minAge = 0;
  let maxAge = 300;
  let texAttr: AttrEntry[] = [];
  let indexState: 'idle' | 'loading' | 'ready' | 'failed' = 'idle';
  let indexPromise: Promise<void> | null = null;

  let size: '4k' | '2k' = options.textureSize ?? pickTextureSize();
  let normalsOn = options.normalMaps !== false;
  let pendingView: GlobeView | null = null;
  let pendingLayers: LayerRef[] | null = null;
  let hadState = false;

  let timeKnown = false;
  let targetMa = 0;
  let direction: 1 | -1 = -1;
  let wantA = 0;
  let wantB = SLICE_MA;
  let wantMix = 0;
  let wA = -1, wB = -1, wDir = 0, wNormals = false; // last wanted-list inputs
  let shownA = -1;
  let shownB = -1;
  let readyFade = 0;
  const normalStrength = new Map<number, number>();
  let sliceChangedAt = 0;
  let normalTimer: ReturnType<typeof setTimeout> | null = null;
  let preloadAges: number[] = [];
  let preloadWaiters: Array<{ ages: number[]; resolve: () => void }> = [];
  let protA: THREE.Texture | null = null, protB: THREE.Texture | null = null;
  let protNA: THREE.Texture | null = null, protNB: THREE.Texture | null = null;

  let rafId = 0;
  let dirty = true;
  let paused = false;
  let mounted = false;
  let disposed = false;
  let lastFrame = 0;
  let renders = 0;
  let lastRenderMs = 0;

  const listeners = new Set<(s: EngineStatus) => void>();
  let status: EngineStatus = { loading: true, attributions: [] };
  let statusKey = -1;
  let waiters: Array<() => void> = [];

  const capacity = (s: '4k' | '2k') => (s === '4k' ? 6 : 10);
  const toMa = (unit: TimeUnit, value: number) => (unit === 'ka' ? value / 1000 : value);

  // ------------------------------------------------------------ loop

  function markDirty() {
    dirty = true;
    schedule();
  }

  function schedule() {
    if (rafId || disposed || !mounted) return;
    if (paused && !(store && store.pendingUploads() > 0)) return;
    rafId = requestAnimationFrame(frame);
  }

  function frame(now: number) {
    rafId = 0;
    if (!renderer || disposed) return;
    const dt = lastFrame ? Math.min(64, now - lastFrame) : 16.7;
    lastFrame = now;
    // One texture upload per frame at most, never in the same frame as a big swap.
    let uploadsLeft = false;
    if (store && store.pendingUploads() > 0) {
      store.uploadOne(renderer);
      uploadsLeft = store.pendingUploads() > 0;
    }
    if (paused) {
      lastFrame = 0;
      if (uploadsLeft) schedule();
      return;
    }
    if (controls && controls.step(dt, now)) {
      onCameraChanged();
      dirty = true;
    }
    const fading = stepFades(dt);
    if (fading) dirty = true;
    if (dirty) {
      const t0 = performance.now();
      renderer.render(scene, camera);
      lastRenderMs = performance.now() - t0;
      renders++;
      dirty = false;
    }
    if (uploadsLeft || fading || (controls !== null && controls.isAnimating())) schedule();
    else lastFrame = 0;
  }

  function onCameraChanged() {
    if (!controls) return;
    controls.writeCamera(camera);
    camera.updateMatrixWorld();
    // Key light fixed relative to the view (upper left, in front): the visible
    // hemisphere is always lit, so the story never shows a night side by accident.
    const e = camera.matrixWorld.elements;
    lightDir.set(
      -0.55 * e[0] + 0.5 * e[4] + 0.67 * e[8],
      -0.55 * e[1] + 0.5 * e[5] + 0.67 * e[9],
      -0.55 * e[2] + 0.5 * e[6] + 0.67 * e[10],
    ).normalize();
    overlays?.setMarkerScale(worldPerPx());
  }

  function worldPerPx(): number {
    const alt = Math.max(0.05, (controls?.view.distance ?? 2.6) - 1);
    return (alt * FOV_DEG * Math.PI) / 180 / Math.max(1, viewportH);
  }

  function stepStrength(age: number, target: number, dt: number): boolean {
    if (age < 0) return false;
    const cur = normalStrength.get(age) ?? 0;
    if (cur === target) return false;
    normalStrength.set(age, target > cur ? Math.min(target, cur + dt / 350) : Math.max(target, cur - dt / 350));
    return true;
  }

  function stepFades(dt: number): boolean {
    if (!globeMat || shownA < 0) return false;
    const u = globeMat.uniforms;
    let changed = false;
    if (readyFade < 1) {
      readyFade = Math.min(1, readyFade + dt / 500);
      u.texturesReady.value = readyFade * readyFade * (3 - 2 * readyFade);
      changed = true;
    }
    const flat = flatNormalTex;
    if (stepStrength(shownA, u.normalA.value !== flat ? 1 : 0, dt)) changed = true;
    if (shownB !== shownA && stepStrength(shownB, u.normalB.value !== flat ? 1 : 0, dt)) changed = true;
    if (changed) {
      u.normalStrengthA.value = normalStrength.get(shownA) ?? 0;
      u.normalStrengthB.value = normalStrength.get(shownB) ?? 0;
    }
    return changed;
  }

  // ------------------------------------------------------------ textures

  function updateWanted(force = false) {
    if (!store || !texIndex) return;
    const normalsNow = normalsOn && performance.now() - sliceChangedAt >= NORMAL_DELAY_MS;
    if (!force && wantA === wA && wantB === wB && direction === wDir && normalsNow === wNormals) return;
    wA = wantA; wB = wantB; wDir = direction; wNormals = normalsNow;
    const list: TexRequest[] = [];
    const add = (kind: 'color' | 'normal', age: number) => {
      if (ageSet.has(age) && !list.some((r) => r.kind === kind && r.age === age)) list.push({ kind, age });
    };
    add('color', wantA);
    add('color', wantB);
    if (normalsNow && store.hasNormals()) { add('normal', wantA); add('normal', wantB); }
    // next two slices in the direction of time movement, then the previous one
    if (direction < 0) { add('color', wantA - SLICE_MA); add('color', wantA - 2 * SLICE_MA); add('color', wantB + SLICE_MA); }
    else { add('color', wantB + SLICE_MA); add('color', wantB + 2 * SLICE_MA); add('color', wantA - SLICE_MA); }
    for (const a of preloadAges) if (list.length < capacity(size)) add('color', a);
    store.setWanted(list);
  }

  /** Bind the best available pair. Called on time changes and when textures settle. */
  function sync() {
    if (!globeMat || !store) return;
    const u = globeMat.uniforms;
    const ta = store.get('color', wantA);
    const tb = wantB === wantA ? ta : store.get('color', wantB);
    if (ta && tb) {
      if (shownA !== wantA || shownB !== wantB) {
        u.mapA.value = ta;
        u.mapB.value = tb;
        shownA = wantA;
        shownB = wantB;
        for (const k of Array.from(normalStrength.keys())) if (k !== shownA && k !== shownB) normalStrength.delete(k);
      }
      u.mixAmount.value = wantMix;
    } else if (shownA >= 0) {
      // keep the last valid pair; if it shares a slice with the wanted pair, show that slice
      if (shownA === wantB) u.mixAmount.value = 0;
      else if (shownB === wantA) u.mixAmount.value = 1;
    }
    if (shownA >= 0) {
      const na = normalsOn ? store.get('normal', shownA) : null;
      const nb = normalsOn ? store.get('normal', shownB) : null;
      u.normalA.value = na ?? flatNormalTex;
      u.normalB.value = nb ?? flatNormalTex;
      u.normalStrengthA.value = normalStrength.get(shownA) ?? 0;
      u.normalStrengthB.value = normalStrength.get(shownB) ?? 0;
      const a = u.mapA.value as THREE.Texture, b = u.mapB.value as THREE.Texture;
      if (a !== protA || b !== protB || na !== protNA || nb !== protNB) {
        protA = a; protB = b; protNA = na; protNB = nb;
        store.protect([a, b, na, nb].filter((t): t is THREE.Texture => !!t));
      }
    }
  }

  function onTextureSettled() {
    sync();
    if (preloadWaiters.length && store) {
      const s = store;
      preloadWaiters = preloadWaiters.filter((w) => {
        const done = w.ages.every((age) => s.get('color', age) || s.failed('color', age));
        if (done) w.resolve();
        return !done;
      });
    }
    markDirty();
    refreshStatus();
  }

  function applyTime(ma: number) {
    const m = Math.min(maxAge, Math.max(minAge, ma));
    if (timeKnown && m !== targetMa) direction = m < targetMa ? -1 : 1;
    timeKnown = true;
    targetMa = m;
    const a = Math.floor(m / SLICE_MA) * SLICE_MA;
    const b = a + SLICE_MA > maxAge ? a : a + SLICE_MA;
    if (a !== wantA || b !== wantB) sliceChangedAt = performance.now();
    wantA = a;
    wantB = b;
    wantMix = b === a ? 0 : (m - a) / SLICE_MA;
    updateWanted();
    if (normalsOn && !normalTimer && store?.hasNormals()) normalTimer = setTimeout(normalCheck, NORMAL_DELAY_MS);
    sync();
    overlays?.setAge(m, direction);
    markDirty();
    refreshStatus();
  }

  function normalCheck() {
    normalTimer = null;
    if (disposed) return;
    const wait = NORMAL_DELAY_MS - (performance.now() - sliceChangedAt);
    if (wait > 0) { normalTimer = setTimeout(normalCheck, wait + 10); return; }
    updateWanted();
  }

  function ensureIndex(): Promise<void> {
    if (indexPromise) return indexPromise;
    indexState = 'loading';
    indexPromise = (async () => {
      try {
        const [idx, meta] = await Promise.all([
          fetchJson<TexturesIndex>(`${globeBase}/textures/index.json`),
          fetchJson<TexMeta>(`${globeBase}/textures/meta.json`).catch(() => null),
        ]);
        if (disposed) return;
        texIndex = idx;
        ageSet = new Set(idx.ages_ma);
        minAge = Math.min(...idx.ages_ma);
        maxAge = Math.max(...idx.ages_ma);
        texAttr = textureAttributions(meta);
        if (!(size in idx.sizes)) {
          const alt = Object.keys(idx.sizes).find((k) => k === '4k' || k === '2k');
          if (alt) { size = alt as '4k' | '2k'; applyDistanceLimits(); }
        }
        const maxAniso = renderer ? renderer.capabilities.getMaxAnisotropy() : 1;
        store = new TextureStore({
          globeBase, index: idx, size, colorCapacity: capacity(size), anisotropy: Math.min(8, maxAniso),
          onDecoded: schedule, onSettled: onTextureSettled,
        });
        indexState = 'ready';
      } catch (err) {
        console.warn('[globe] textures index unavailable; showing the neutral globe', err);
        indexState = 'failed';
      }
      if (timeKnown) applyTime(targetMa);
      else refreshStatus();
    })();
    return indexPromise;
  }

  // ------------------------------------------------------------ status

  function computeLoading(): boolean {
    if (indexState === 'idle' || indexState === 'loading') return true;
    if (!timeKnown) return false;
    if (overlays?.isLoading()) return true;
    if (indexState === 'failed' || !store) return false;
    if (shownA === wantA && shownB === wantB) return false;
    return !(store.failed('color', wantA) || store.failed('color', wantB));
  }

  /** Bitmask of which attribution lines apply; strings are rebuilt only when it changes. */
  function attributionKey(): number {
    let key = 0;
    for (let i = 0; i < texAttr.length && i < 20; i++) {
      if (texAttr[i].max >= wantA && texAttr[i].min <= wantB) key |= 1 << i;
    }
    if (overlays) {
      if (overlays.anyVisible() && overlays.attribution()) key |= 1 << 21;
      if (overlays.boundaryNote()) key |= 1 << 22;
    }
    return key;
  }

  function buildAttributions(): string[] {
    const out: string[] = [];
    for (const e of texAttr) if (e.max >= wantA && e.min <= wantB) out.push(e.text);
    const plates = overlays?.attribution();
    if (overlays && plates && overlays.anyVisible()) out.push(plates);
    const note = overlays?.boundaryNote();
    if (note) out.push(note);
    return out;
  }

  function refreshStatus(force = false) {
    const loading = computeLoading();
    const key = attributionKey() | (loading ? 1 << 25 : 0);
    if (key !== statusKey || force) {
      statusKey = key;
      status = { loading, attributions: buildAttributions() };
      for (const cb of listeners) cb(status);
    }
    if (!loading && waiters.length) {
      const w = waiters;
      waiters = [];
      for (const f of w) f();
    }
  }

  function whenSettled(): Promise<void> {
    refreshStatus();
    if (!status.loading || disposed) return Promise.resolve();
    return new Promise((resolve) => {
      let done = false;
      const fin = () => { if (!done) { done = true; resolve(); } };
      waiters.push(fin);
      setTimeout(fin, 15000);
    });
  }

  // ------------------------------------------------------------ layout

  function resize() {
    if (!renderer || !container) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (w < 1 || h < 1) return;
    const pr = Math.min(window.devicePixelRatio || 1, maxPixelRatio);
    if (renderer.getPixelRatio() !== pr) renderer.setPixelRatio(pr);
    renderer.setSize(w, h, false);
    viewportH = h;
    applyDistanceLimits();
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    overlays?.setResolution(w, h);
    if (stars) (stars.material as THREE.ShaderMaterial).uniforms.pixelRatio.value = pr;
    overlays?.setMarkerScale(worldPerPx());
    markDirty();
  }

  // ADR 0004: at most two CSS pixels per texture texel at the sub-camera point.
  // px per texel = (360 / texW) / ((d - 1) * FOV_DEG / viewportH)  =>  d >= 1 + 360 * H / (2 * FOV_DEG * texW)
  // Also enforce a framing floor so the sphere fits with air around it (2026-09-13 pass).
  function applyDistanceLimits() {
    if (!controls) return;
    const texW = size === '4k' ? 4096 : 2048;
    const rule = 1 + (360 * Math.max(1, viewportH)) / (2 * FOV_DEG * texW);
    const fit = fitDistance();
    controls.setDistanceLimits(Math.min(Math.max(minDistance, rule, fit), maxDistance - 0.3), maxDistance);
  }

  function fitDistance(): number {
    const half = (FOV_DEG * Math.PI) / 360;
    return 1 / (FIT_FRACTION * Math.tan(half));
  }

  /** Lift a chapter's declared distance to the framing floor so the sphere always sits inside the stage. */
  function frameView(v: GlobeCamera): { lat: number; lon: number; distance: number } {
    return { lat: v.lat, lon: v.lon, distance: Math.max(v.distance, fitDistance()) };
  }

  function applyLayers(layers: LayerRef[]) {
    if (!overlays) { pendingLayers = layers; return; }
    const tokens = new Set<string>();
    for (const l of layers) for (const t of (l.style ?? '').split('+')) if (t.trim()) tokens.add(t.trim());
    // ADR 0005: outlines only on explicit request ("landmass", "blocks"); "continents"
    // alone draws nothing. Without any plate style the defaults stay (boundaries,
    // marker and trail on). The marker and trail are not controlled by layers.
    if (!['continents', 'landmass', 'blocks', 'coastlines', 'boundaries'].some((t) => tokens.has(t))) return;
    overlays.setConfig({
      showLandmass: tokens.has('landmass'),
      showBlocks: tokens.has('blocks'),
      showCoastlines: tokens.has('coastlines'),
      showBoundaries: tokens.has('boundaries'),
    });
  }

  // ------------------------------------------------------------ engine

  const engine: SceneEngine & GlobeRuntime = {
    kind: 'globe',

    async mount(el: HTMLElement) {
      if (mounted || disposed || fallback) return;
      container = el;
      try {
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance', stencil: false });
      } catch (err) {
        console.warn('[globe] WebGL unavailable; using the placeholder engine', err);
        fallback = createStubEngine('globe');
        await fallback.mount(el);
        for (const cb of listeners) fallback.onStatus(cb);
        return;
      }
      mounted = true;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.setClearColor(0x03050b, 1);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, maxPixelRatio));
      const canvas = renderer.domElement;
      canvas.style.display = 'block';
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      el.appendChild(canvas);

      // 1x1 stand-ins keep every sampler bound before real textures arrive.
      blankTex = new THREE.DataTexture(new Uint8Array([46, 58, 78, 255]), 1, 1);
      blankTex.colorSpace = THREE.SRGBColorSpace;
      blankTex.needsUpdate = true;
      flatNormalTex = new THREE.DataTexture(new Uint8Array([128, 128, 255, 255]), 1, 1);
      flatNormalTex.needsUpdate = true;

      globeMat = new THREE.ShaderMaterial({
        vertexShader: globeVertexShader,
        fragmentShader: globeFragmentShader,
        uniforms: {
          mapA: { value: blankTex },
          mapB: { value: blankTex },
          normalA: { value: flatNormalTex },
          normalB: { value: flatNormalTex },
          mixAmount: { value: 0 },
          normalStrengthA: { value: 0 },
          normalStrengthB: { value: 0 },
          normalAmount: { value: normalsOn ? NORMAL_AMOUNT : 0 },
          texturesReady: { value: 0 },
          baseColor: { value: new THREE.Color(0x3a4a60) },
          lightDir: { value: lightDir },
          ambient: { value: 0.42 },
          wrap: { value: 0.6 },
          rimColor: { value: new THREE.Color(0xb4d0ff) },
          rimStrength: { value: 0.22 },
        },
      });
      globeMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 256, 128), globeMat);
      scene.add(globeMesh);

      atmoMat = new THREE.ShaderMaterial({
        vertexShader: atmosphereVertexShader,
        fragmentShader: atmosphereFragmentShader,
        uniforms: {
          glowColor: { value: new THREE.Color(0x8fbfff) },
          intensity: { value: 0.6 },
          innerRadius: { value: 1.0 },
          outerRadius: { value: 1.055 },
          lightDir: { value: lightDir },
        },
        side: THREE.BackSide,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      });
      atmoMesh = new THREE.Mesh(new THREE.SphereGeometry(1.06, 128, 64), atmoMat);
      atmoMesh.renderOrder = 10;
      atmoMesh.visible = options.atmosphere !== false;
      scene.add(atmoMesh);

      stars = createStars();
      stars.visible = options.stars !== false;
      scene.add(stars);

      overlays = new Overlays(globeBase, () => { markDirty(); refreshStatus(); });
      scene.add(overlays.group);
      if (pendingLayers) { applyLayers(pendingLayers); pendingLayers = null; }

      // No gesture hint: plain wheel scrolls the page silently; the reader discovers Ctrl/⌘ + wheel.
      // The full-stage veil the previous hint painted was a constant dark flash while reading
      // (docs/ux/2026-09-13-motion-and-framing.md).
      controls = new GlobeControls(canvas, markDirty, { minDistance, maxDistance, fovDeg: FOV_DEG });
      controls.setLocked(locked);
      controls.jumpTo(pendingView ?? DEFAULT_VIEW);
      pendingView = null;

      ro = new ResizeObserver(() => resize());
      ro.observe(el);
      resize();
      onCameraChanged();

      if (options.debug) {
        (window as unknown as { __globeDebug?: unknown }).__globeDebug = { renderer, scene, camera, controls, overlays, getStore: () => store };
      }

      void ensureIndex();
      void overlays.load();
      if (timeKnown) applyTime(targetMa);
      markDirty();
      refreshStatus(true);
    },

    async setState(state: SceneState) {
      if (fallback) return fallback.setState(state);
      const v = state.camera.globe;
      if (v) {
        const view = frameView(v);
        if (!controls) pendingView = view;
        else if (hadState && !options.reduceMotion) controls.easeTo(view, CAMERA_EASE_MS, performance.now());
        else controls.jumpTo(view);
        markDirty();
      }
      hadState = true;
      applyLayers(state.layers ?? []);
      preloadAges = [];
      applyTime(toMa(state.time.unit, state.time.value));
      if (!mounted) return;
      await ensureIndex();
      await whenSettled();
    },

    setTime(unit: TimeUnit, value: number) {
      if (fallback) { fallback.setTime(unit, value); return; }
      applyTime(toMa(unit, value));
    },

    setCamera(cam: GlobeCamera | TerrainCamera, durationMs = 0) {
      if (fallback) { fallback.setCamera(cam, durationMs); return; }
      if (!('distance' in cam)) return;
      const view = frameView(cam);
      if (!controls) { pendingView = view; return; }
      if (durationMs > 0) controls.easeTo(view, durationMs, performance.now());
      else controls.jumpTo(view);
      markDirty();
    },

    async preload(state: SceneState) {
      if (fallback) return fallback.preload(state);
      if (!mounted) return;
      await ensureIndex();
      if (!store) return;
      const m = Math.min(maxAge, Math.max(minAge, toMa(state.time.unit, state.time.value)));
      const a = Math.floor(m / SLICE_MA) * SLICE_MA;
      const b = Math.min(maxAge, a + SLICE_MA);
      preloadAges = a === b ? [a] : [a, b];
      updateWanted(true);
      const s = store;
      if (preloadAges.every((age) => s.get('color', age) || s.failed('color', age))) return;
      await new Promise<void>((resolve) => {
        const w = { ages: preloadAges.slice(), resolve };
        preloadWaiters.push(w);
        setTimeout(() => { preloadWaiters = preloadWaiters.filter((x) => x !== w); resolve(); }, 20000);
      });
    },

    pause() {
      if (fallback) { fallback.pause(); return; }
      paused = true;
      if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
      lastFrame = 0;
      store?.releaseUnprotected();
      overlays?.releaseCache();
    },

    resume() {
      if (fallback) { fallback.resume(); return; }
      if (!paused) return;
      paused = false;
      updateWanted(true);
      markDirty();
    },

    onStatus(cb: (s: EngineStatus) => void) {
      if (fallback) return fallback.onStatus(cb);
      listeners.add(cb);
      cb(status);
      return () => { listeners.delete(cb); };
    },

    resize() {
      if (fallback) fallback.resize();
      else resize();
    },

    dispose() {
      if (disposed) return;
      disposed = true;
      fallback?.dispose();
      fallback = null;
      if (rafId) cancelAnimationFrame(rafId);
      rafId = 0;
      if (normalTimer) clearTimeout(normalTimer);
      ro?.disconnect();
      controls?.dispose();
      overlays?.dispose();
      store?.dispose();
      globeMesh?.geometry.dispose();
      globeMat?.dispose();
      atmoMesh?.geometry.dispose();
      atmoMat?.dispose();
      if (stars) { stars.geometry.dispose(); (stars.material as THREE.Material).dispose(); }
      blankTex?.dispose();
      flatNormalTex?.dispose();
      scene.clear();
      if (renderer) {
        renderer.dispose();
        try { renderer.forceContextLoss(); } catch { /* already lost */ }
        renderer.domElement.remove();
      }
      renderer = null; controls = null; overlays = null; store = null; ro = null;
      globeMesh = null; atmoMesh = null; globeMat = null; atmoMat = null; stars = null;
      listeners.clear();
      for (const w of waiters) w();
      waiters = [];
      for (const w of preloadWaiters) w.resolve();
      preloadWaiters = [];
      if (options.debug) delete (window as unknown as { __globeDebug?: unknown }).__globeDebug;
      mounted = false;
    },

    // ---- GlobeRuntime (dev page)
    setTextureSize(s: '4k' | '2k') {
      if (s === size) return;
      size = s;
      applyDistanceLimits();
      if (!store) return;
      store.setSize(s, capacity(s));
      updateWanted(true);
      sync();
      markDirty();
      refreshStatus();
    },
    currentSize: () => size,
    setAtmosphereEnabled(v: boolean) {
      if (atmoMesh) atmoMesh.visible = v;
      markDirty();
    },
    setNormalMapsEnabled(v: boolean) {
      normalsOn = v;
      if (globeMat) globeMat.uniforms.normalAmount.value = v ? NORMAL_AMOUNT : 0;
      updateWanted(true);
      sync();
      markDirty();
    },
    setStarsEnabled(v: boolean) {
      if (stars) stars.visible = v;
      markDirty();
    },
    setOverlayConfig(c: Partial<OverlaysConfig>) {
      overlays?.setConfig(c);
      refreshStatus();
    },
    setLocked(v: boolean) {
      locked = v;
      controls?.setLocked(v);
    },
    resetUploadStats() { if (store) store.maxUploadMs = 0; },
    stats: (): GlobeStats => ({
      renders,
      lastRenderMs,
      uploads: store?.uploads ?? 0,
      lastUploadMs: store?.lastUploadMs ?? 0,
      maxUploadMs: store?.maxUploadMs ?? 0,
      shownPair: shownA >= 0 ? [shownA, shownB] : null,
      overlayAge: overlays?.shownPlatesAge() ?? null,
      lineObjects: overlays?.lineObjects() ?? 0,
      loading: status.loading,
      size,
    }),
  };
  return engine;
}
