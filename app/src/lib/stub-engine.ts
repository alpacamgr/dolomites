/**
 * Placeholder engine used until the real globe / terrain engines exist,
 * and as a fallback when WebGL is unavailable. Draws the view name and the
 * current time on a 2D canvas. Not a data source; nothing here is shown as fact.
 */
import type { SceneEngine, SceneState, EngineStatus, TimeUnit, GlobeCamera, TerrainCamera } from './scene-api';

export function createStubEngine(kind: 'globe' | 'terrain'): SceneEngine {
  let canvas: HTMLCanvasElement | null = null;
  let ctx: CanvasRenderingContext2D | null = null;
  let container: HTMLElement | null = null;
  let time: { unit: TimeUnit; value: number } = { unit: 'ma', value: 0 };
  let paused = false;
  const listeners = new Set<(s: EngineStatus) => void>();

  function draw() {
    if (!ctx || !canvas || paused) return;
    const { width, height } = canvas;
    const g = ctx.createLinearGradient(0, 0, 0, height);
    if (kind === 'globe') { g.addColorStop(0, '#0b1020'); g.addColorStop(1, '#1b2a4a'); }
    else { g.addColorStop(0, '#dfe6ea'); g.addColorStop(1, '#8a9aa5'); }
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = kind === 'globe' ? '#c9d4e5' : '#1f2a33';
    ctx.font = `${Math.round(height / 22)}px system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText(`${kind} engine placeholder`, width / 2, height / 2 - 20);
    const label = time.unit === 'ma' ? `${time.value.toFixed(1)} Ma` : `${Math.round(time.value)} ka`;
    ctx.fillText(label, width / 2, height / 2 + 30);
  }

  function emit() { listeners.forEach((cb) => cb({ loading: false, attributions: [] })); }

  return {
    kind,
    async mount(el) {
      container = el;
      canvas = document.createElement('canvas');
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      canvas.style.display = 'block';
      el.appendChild(canvas);
      ctx = canvas.getContext('2d');
      this.resize();
      emit();
    },
    async setState(state: SceneState) { time = state.time; draw(); emit(); },
    setTime(unit, value) { time = { unit, value }; draw(); },
    setCamera(_c: GlobeCamera | TerrainCamera) { /* no camera in the stub */ },
    async preload(_s: SceneState) { /* nothing to preload */ },
    pause() { paused = true; },
    resume() { paused = false; draw(); },
    onStatus(cb) { listeners.add(cb); return () => listeners.delete(cb); },
    resize() {
      if (!canvas || !container) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(container.clientWidth * dpr));
      canvas.height = Math.max(1, Math.round(container.clientHeight * dpr));
      draw();
    },
    dispose() { canvas?.remove(); canvas = null; ctx = null; listeners.clear(); },
  };
}
