/**
 * Control panel for /dev/terrain: layer toggles, time slider with play and a
 * scripted 120 -> 0 ka scrub, camera presets and a scripted flight, exaggeration,
 * FPS meter with frame-time stats, loading indicator, attributions, stand-in banner.
 */
import type { SceneState, TerrainCamera, LayerRef, HonestyLabel } from '../../scene-api';
import type { TerrainEngine } from '../index';

const LAYERS: Array<[id: string, name: string, label: HonestyLabel, on: boolean]> = [
  ['dolomites-terrain', 'Elevation tint + hillshade', 'observed', true],
  ['seguinot2018-alps-1km', 'Ice thickness (model)', 'modeled', true],
  ['geology-suedtirol', 'Geology, South Tyrol', 'observed', false],
  ['glacimontis-lgm', 'LGM ice extent', 'interpreted', false],
  ['reinthaler-paul-2025-lia', 'Little Ice Age glaciers', 'interpreted', false],
  ['rgi7-region11', 'Glaciers today (RGI 7)', 'observed', false],
  ['diss-3-3-1', 'Seismogenic faults (DISS)', 'interpreted', false],
  ['localities', 'Localities', 'observed', false],
];

export const CAMERA_PRESETS: Record<string, TerrainCamera> = {
  Overview: { lon: 11.55, lat: 46.28, zoom: 8.6, pitch: 50, bearing: -8 },
  'Sella from the south': { lon: 11.79, lat: 46.44, zoom: 11.6, pitch: 70, bearing: 5 },
  Marmolada: { lon: 11.9, lat: 46.4, zoom: 11.9, pitch: 66, bearing: 200 },
  'Bolzano basin': { lon: 11.3, lat: 46.43, zoom: 10.6, pitch: 62, bearing: 30 },
};

function $(id: string): HTMLElement {
  const el = document.getElementById(id);
  if (!el) throw new Error(`#${id} missing`);
  return el;
}

/** Frame-time recorder used by the FPS readout and the scripted tests. */
function frameMeter(onSecond: (fps: number) => void) {
  let last = performance.now();
  let count = 0;
  let windowStart = last;
  let samples: number[] | null = null;
  const tick = (now: number) => {
    const dt = now - last;
    last = now;
    count++;
    if (samples) samples.push(dt);
    if (now - windowStart >= 1000) {
      onSecond((count * 1000) / (now - windowStart));
      count = 0;
      windowStart = now;
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  return {
    start() { samples = []; },
    stop() {
      const s = samples ?? [];
      samples = null;
      if (!s.length) return 'no frames';
      const sorted = [...s].sort((a, b) => a - b);
      const total = s.reduce((a, b) => a + b, 0);
      const p95 = sorted[Math.floor(sorted.length * 0.95)];
      const long = s.filter((d) => d > 33.4).length;
      return `${(s.length * 1000 / total).toFixed(1)} fps avg, p95 ${p95.toFixed(1)} ms, max ${sorted[sorted.length - 1].toFixed(0)} ms, ${long} frames > 33 ms`;
    },
  };
}

export function wireControls(engine: TerrainEngine) {
  const enabled = new Set(LAYERS.filter((l) => l[3]).map((l) => l[0]));
  const refs = (): LayerRef[] => LAYERS.filter((l) => enabled.has(l[0]))
    .map(([id, , label]) => ({ id, label, source_ref: id }));
  const range = engine.getIceRange() ?? [0, 120];
  let ka = 20;
  const state = (camera?: TerrainCamera): SceneState => ({
    view: 'terrain', time: { unit: 'ka', value: ka }, camera: camera ? { terrain: camera } : {}, layers: refs(),
  });

  // layers
  const list = $('layers');
  for (const [id, name, label, on] of LAYERS) {
    const row = document.createElement('label');
    row.className = 'row';
    row.innerHTML = `<input type="checkbox" ${on ? 'checked' : ''}><span>${name}</span><span class="hint">${label}</span>`;
    row.querySelector('input')!.addEventListener('change', (e) => {
      if ((e.target as HTMLInputElement).checked) enabled.add(id); else enabled.delete(id);
      void engine.setState(state());
    });
    list.appendChild(row);
  }

  // time
  const slider = $('time') as HTMLInputElement;
  const timeLabel = $('time-value');
  slider.min = String(range[0]);
  slider.max = String(range[1] + 1);
  slider.step = '0.1';
  const setKa = (v: number) => {
    ka = v;
    slider.value = String(v);
    timeLabel.textContent = `${v.toFixed(1)} ka`;
    engine.setTime('ka', v);
  };
  slider.addEventListener('input', () => setKa(Number(slider.value)));
  setKa(ka);

  const perf = $('perf');
  const fpsEl = $('fps');
  const meter = frameMeter((fps) => { fpsEl.textContent = fps.toFixed(0); });

  let anim = 0;
  const animateKa = (from: number, to: number, ms: number, done?: () => void) => {
    cancelAnimationFrame(anim);
    const t0 = performance.now();
    const step = (now: number) => {
      const k = Math.min(1, (now - t0) / ms);
      setKa(from + (to - from) * k);
      if (k < 1) anim = requestAnimationFrame(step); else done?.();
    };
    anim = requestAnimationFrame(step);
  };
  $('play').addEventListener('click', () => animateKa(Number(slider.value) || range[1] + 1, 0, 30000));
  $('scrub').addEventListener('click', () => {
    perf.textContent = 'scrub running...';
    meter.start();
    animateKa(120, 0, 10000, () => { perf.textContent = `scrub 120-0 ka / 10 s: ${meter.stop()}`; });
  });

  // camera
  const presets = $('presets');
  for (const [name, cam] of Object.entries(CAMERA_PRESETS)) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = name;
    b.addEventListener('click', () => engine.setCamera(cam, 2500));
    presets.appendChild(b);
  }
  $('flight').addEventListener('click', () => {
    const map = engine.getMap();
    if (!map) return;
    perf.textContent = 'flight running...';
    const legs = [CAMERA_PRESETS.Overview, CAMERA_PRESETS['Bolzano basin'], CAMERA_PRESETS['Sella from the south'], CAMERA_PRESETS.Marmolada];
    meter.start();
    let i = 0;
    const next = () => {
      if (i >= legs.length) { perf.textContent = `camera flight 4 legs x 3 s: ${meter.stop()}`; return; }
      map.once('moveend', next);
      engine.setCamera(legs[i++], 3000);
    };
    next();
  });
  ($('lock') as HTMLInputElement).addEventListener('change', (e) => engine.setLock((e.target as HTMLInputElement).checked));

  // exaggeration
  const ex = $('exaggeration') as HTMLInputElement;
  ex.addEventListener('input', () => {
    $('exaggeration-value').textContent = `${Number(ex.value).toFixed(2)}x`;
    engine.setExaggeration(Number(ex.value));
  });

  // status
  const loadingEl = $('loading');
  const attrEl = $('attributions');
  engine.onStatus((s) => {
    loadingEl.textContent = s.loading ? 'loading' : 'idle';
    loadingEl.dataset.state = s.loading ? 'loading' : 'idle';
    attrEl.replaceChildren(...s.attributions.map((a) => {
      const d = document.createElement('div');
      d.textContent = a;
      return d;
    }));
  });
  $('fallback-banner').hidden = !engine.getTerrainInfo()?.fallback;

  void engine.setState(state(CAMERA_PRESETS.Overview));
}
