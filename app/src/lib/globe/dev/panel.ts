/**
 * Wiring for the dev page (src/pages/dev/globe.astro). Development only.
 * URL parameters for reproducible screenshots: ?data=sample&t=240&lat=..&lon=..&dist=..&size=2k
 */
import { createGlobeEngine, type GlobeRuntime, type OverlaysConfig } from '../index';
import type { SceneEngine } from '../../scene-api';

type Engine = SceneEngine & GlobeRuntime;

interface ScrubResult {
  frames: number; seconds: number; fps: number; medianMs: number; p95Ms: number; p99Ms: number; worstMs: number;
  framesOver17ms: number; framesOver25ms: number; framesOver50ms: number; longTasks: number; longestTaskMs: number;
  renders: number; uploads: number; maxUploadMs: number; size: string;
}

const $ = <T extends HTMLElement = HTMLElement>(id: string): T => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`missing #${id}`);
  return el as T;
};

const stage = $('stage');
const timeInput = $<HTMLInputElement>('time');
const timeVal = $('time-value');
const fpsEl = $('fps');
const loadingEl = $('loading');
const statusEl = $('loading-inline');
const attrEl = $('attributions');
const sizeSel = $<HTMLSelectElement>('size');
const dataSel = $<HTMLSelectElement>('data');
const playBtn = $<HTMLButtonElement>('play');
const scrubBtn = $<HTMLButtonElement>('scrub');
const scrubOut = $('scrub-result');

const params = new URLSearchParams(location.search);
const num = (k: string): number | null => {
  const v = params.get(k);
  return v === null || v === '' || Number.isNaN(Number(v)) ? null : Number(v);
};

let engine: Engine | null = null;
let offStatus: (() => void) | null = null;

async function resolveDataBase(requested: string): Promise<string> {
  if (requested !== '/data') return requested;
  try {
    const r = await fetch('/data/globe/textures/index.json', { cache: 'no-store' });
    if (r.ok) return requested;
  } catch { /* fall through */ }
  console.warn('[dev] real globe data missing, using the labelled sample set');
  return '/data/_sample';
}

function setTime(v: number) {
  timeInput.value = String(v);
  timeVal.textContent = `${v.toFixed(1)} Ma`;
  engine?.setTime('ma', v);
}

function applyToggles(e: Engine) {
  document.querySelectorAll<HTMLInputElement>('[data-toggle]').forEach((cb) => applyToggle(e, cb));
}

function applyToggle(e: Engine, cb: HTMLInputElement) {
  const key = cb.dataset.toggle ?? '';
  const v = cb.checked;
  if (key === 'atmosphere') e.setAtmosphereEnabled(v);
  else if (key === 'normals') e.setNormalMapsEnabled(v);
  else if (key === 'stars') e.setStarsEnabled(v);
  else if (key === 'locked') e.setLocked(v);
  else e.setOverlayConfig({ [key]: v } as Partial<OverlaysConfig>);
}

async function boot(requested: string) {
  offStatus?.();
  engine?.dispose();
  engine = null;
  const base = await resolveDataBase(requested);
  dataSel.value = base;
  const forced = params.get('size');
  const e = createGlobeEngine({
    dataBase: base,
    textureSize: forced === '4k' || forced === '2k' ? forced : undefined,
    debug: true,
  });
  engine = e;
  await e.mount(stage);
  sizeSel.value = e.currentSize();
  applyToggles(e);
  offStatus = e.onStatus((s) => {
    loadingEl.classList.toggle('on', s.loading);
    statusEl.textContent = s.loading ? 'Loading textures / plates ...' : 'Ready.';
    attrEl.replaceChildren(...s.attributions.map((a) => {
      const d = document.createElement('div');
      d.textContent = a;
      return d;
    }));
  });
  const lat = num('lat'), lon = num('lon'), dist = num('dist');
  if (lat !== null || lon !== null || dist !== null) e.setCamera({ lat: lat ?? 20, lon: lon ?? 10, distance: dist ?? 2.6 }, 0);
  const t = num('t');
  setTime(t ?? parseFloat(timeInput.value));
}

// ---- meters: page frame rate (what the viewer sees) and engine renders
let frames = 0;
let lastT = performance.now();
let lastRenders = 0;
function tick(now: number) {
  frames++;
  if (now - lastT >= 500) {
    const st = engine?.stats();
    const rps = st ? ((st.renders - lastRenders) * 1000) / (now - lastT) : 0;
    lastRenders = st?.renders ?? 0;
    fpsEl.textContent = `${Math.round((frames * 1000) / (now - lastT))} fps | ${Math.round(rps)} renders/s | render ${st ? st.lastRenderMs.toFixed(1) : '-'} ms | upload ${st ? st.lastUploadMs.toFixed(0) : '-'} ms | ${st?.size ?? ''}`;
    frames = 0;
    lastT = now;
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

timeInput.addEventListener('input', () => setTime(parseFloat(timeInput.value)));

let playing = false;
playBtn.addEventListener('click', () => {
  playing = !playing;
  playBtn.textContent = playing ? 'Pause' : 'Play';
  let prev = performance.now();
  const step = (now: number) => {
    if (!playing) return;
    let v = parseFloat(timeInput.value) - ((now - prev) / 1000) * 10; // 10 Myr per second toward the present
    prev = now;
    if (v < 0) v = 300;
    setTime(v);
    requestAnimationFrame(step);
  };
  if (playing) requestAnimationFrame(step);
});

async function scrubTest(): Promise<ScrubResult | null> {
  const e = engine;
  if (!e) return null;
  playing = false;
  playBtn.textContent = 'Play';
  scrubOut.textContent = 'running 300 -> 0 Ma over 10 s ...';
  const intervals: number[] = [];
  const tasks: number[] = [];
  let obs: PerformanceObserver | null = null;
  try {
    obs = new PerformanceObserver((list) => { for (const en of list.getEntries()) tasks.push(en.duration); });
    obs.observe({ type: 'longtask', buffered: false });
  } catch { obs = null; }
  e.resetUploadStats();
  const s0 = e.stats();
  const dur = 10000;
  const start = performance.now();
  await new Promise<void>((resolve) => {
    let last = start;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      setTime(300 * (1 - t));
      intervals.push(now - last);
      last = now;
      if (t < 1) requestAnimationFrame(step);
      else resolve();
    };
    requestAnimationFrame(step);
  });
  obs?.disconnect();
  intervals.shift();
  const s1 = e.stats();
  const sorted = intervals.slice().sort((a, b) => a - b);
  const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * p))];
  const seconds = intervals.reduce((a, b) => a + b, 0) / 1000;
  const r: ScrubResult = {
    frames: intervals.length,
    seconds: +seconds.toFixed(2),
    fps: +(intervals.length / seconds).toFixed(1),
    medianMs: +q(0.5).toFixed(2), p95Ms: +q(0.95).toFixed(2), p99Ms: +q(0.99).toFixed(2), worstMs: +sorted[sorted.length - 1].toFixed(1),
    framesOver17ms: intervals.filter((x) => x > 17).length,
    framesOver25ms: intervals.filter((x) => x > 25).length,
    framesOver50ms: intervals.filter((x) => x > 50).length,
    longTasks: tasks.length,
    longestTaskMs: tasks.length ? Math.round(Math.max(...tasks)) : 0,
    renders: s1.renders - s0.renders,
    uploads: s1.uploads - s0.uploads,
    maxUploadMs: +s1.maxUploadMs.toFixed(1),
    size: s1.size,
  };
  (window as unknown as { __scrubResult?: ScrubResult }).__scrubResult = r;
  scrubOut.textContent = `${r.fps} fps, median ${r.medianMs} ms, p95 ${r.p95Ms} ms, worst ${r.worstMs} ms, >25ms: ${r.framesOver25ms}, long tasks: ${r.longTasks} (max ${r.longestTaskMs} ms), uploads ${r.uploads} (max ${r.maxUploadMs} ms)`;
  console.log('[scrub 300->0 Ma / 10 s]', r);
  return r;
}
scrubBtn.addEventListener('click', () => { void scrubTest(); });
(window as unknown as { __scrubTest?: () => Promise<ScrubResult | null> }).__scrubTest = scrubTest;

const presets: Record<string, { lat: number; lon: number; distance: number }> = {
  europe: { lat: 46, lon: 11, distance: 2.2 },
  pangea: { lat: 5, lon: 15, distance: 2.8 },
  pacific: { lat: 0, lon: -160, distance: 2.6 },
  antimeridian: { lat: 0, lon: 180, distance: 2.6 },
  southpole: { lat: -85, lon: 0, distance: 2.6 },
};
document.querySelectorAll<HTMLButtonElement>('[data-preset]').forEach((b) => {
  b.addEventListener('click', () => {
    const p = presets[b.dataset.preset ?? ''];
    if (p) engine?.setCamera(p, 900);
  });
});

document.querySelectorAll<HTMLInputElement>('[data-toggle]').forEach((cb) => {
  cb.addEventListener('change', () => { if (engine) applyToggle(engine, cb); });
});

sizeSel.addEventListener('change', () => engine?.setTextureSize(sizeSel.value as '4k' | '2k'));
dataSel.addEventListener('change', () => { void boot(dataSel.value); });

void boot(params.get('data') === 'sample' ? '/data/_sample' : '/data');
