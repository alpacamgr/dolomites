/**
 * Manages the two stacked engine containers on the stage.
 *
 *  - Loads each engine lazily via dynamic import so nothing three.js- or
 *    MapLibre-shaped ends up in the initial bundle. If a real engine fails to
 *    load or mount, the slot falls back to the placeholder stub engine.
 *  - On a chapter change to a different `view`, crossfades the two containers
 *    (CROSSFADE_MS, applied inline so CSS and JS cannot drift) and pauses the
 *    outgoing engine when the fade completes. The terrain engine times its camera
 *    flight to the same fade (docs/ux/2026-09-timeline-and-geology-ux.md).
 *  - Preloads (mounts + preload) the other engine on demand so the first
 *    switch is not blank.
 */
import type { SceneEngine, SceneState, EngineStatus } from '../scene-api';
import { importWithReload } from './chunkReload';

export type EngineKind = 'globe' | 'terrain';

type Slot = {
  el: HTMLElement;
  engine: SceneEngine | null;
  mountPromise: Promise<SceneEngine> | null;
};

export interface EngineManager {
  ensureMounted(kind: EngineKind): Promise<SceneEngine>;
  /** Call `cb` once the engine of `kind` is mounted (immediately if it already is); does not trigger a mount. */
  onMounted(kind: EngineKind, cb: (engine: SceneEngine) => void): () => void;
  applyState(state: SceneState): Promise<void>;
  applyTime(unit: 'ma' | 'ka', value: number): void;
  preload(state: SceneState): Promise<void>;
  activeKind(): EngineKind | null;
  /** status of the active engine (loading flag and attribution strings) */
  onStatus(cb: (status: EngineStatus) => void): () => void;
  resize(): void;
  destroy(): void;
}

export interface EngineManagerOptions {
  reduceMotion?: boolean;
  /** extra options for the engine factories */
  engineOptions?: Record<string, unknown>;
}

/**
 * Sequenced fade: the outgoing engine fades to the stage background first, then the incoming
 * engine fades in. Both engines are never visible at once, so the two scenes cannot overlay
 * (docs/ux/2026-09-13-motion-and-framing.md). The old CROSSFADE_MS is kept as the total budget
 * for the CSS mirror in global.css (transitions only fire on inline changes anyway).
 */
export const FADE_OUT_MS = 260;
export const FADE_IN_MS = 380;
export const CROSSFADE_MS = FADE_OUT_MS + FADE_IN_MS;
const FADE_EASING = 'cubic-bezier(0.4, 0, 0.2, 1)';

async function loadFactory(kind: EngineKind): Promise<(opts?: Record<string, unknown>) => SceneEngine> {
  // a chunk missing after a deploy reloads the page once (chunkReload.ts); other failures use the stub
  if (kind === 'globe') {
    const m = await importWithReload(() => import('@/lib/globe'));
    return m.createGlobeEngine;
  }
  const m = await importWithReload(() => import('@/lib/terrain'));
  return m.createTerrainEngine;
}

export function createEngineManager(
  globeEl: HTMLElement,
  terrainEl: HTMLElement,
  options: EngineManagerOptions = {},
): EngineManager {
  const { reduceMotion = false, engineOptions = {} } = options;
  const slots: Record<EngineKind, Slot> = {
    globe: { el: globeEl, engine: null, mountPromise: null },
    terrain: { el: terrainEl, engine: null, mountPromise: null },
  };
  let active: EngineKind | null = null;
  const statusListeners = new Set<(s: EngineStatus) => void>();
  const mountListeners: Record<EngineKind, Set<(e: SceneEngine) => void>> = { globe: new Set(), terrain: new Set() };
  const lastStatus: Partial<Record<EngineKind, EngineStatus>> = {};
  const statusOff: Partial<Record<EngineKind, () => void>> = {};
  const pauseTimers: Partial<Record<EngineKind, number>> = {};

  function setSlotVisible(kind: EngineKind, visible: boolean, durationMs: number) {
    const el = slots[kind].el;
    el.style.transition = reduceMotion ? 'none' : `opacity ${durationMs}ms ${FADE_EASING}`;
    el.style.opacity = visible ? '1' : '0';
    el.style.pointerEvents = visible ? 'auto' : 'none';
  }

  async function ensureMounted(kind: EngineKind): Promise<SceneEngine> {
    const slot = slots[kind];
    if (slot.engine) return slot.engine;
    if (slot.mountPromise) return slot.mountPromise;
    slot.mountPromise = (async () => {
      let engine: SceneEngine;
      try {
        const factory = await loadFactory(kind);
        engine = factory({ dataBase: '/data', reduceMotion, ...engineOptions });
        await engine.mount(slot.el);
      } catch (err) {
        // The real engine could not load (module error, no WebGL). Fall back to the
        // placeholder so the stage still shows the view and the scrolled time;
        // stub-engine.ts documents this role and draws nothing that reads as data.
        console.error(`[stage] ${kind} engine failed to load; using placeholder`, err);
        slot.el.replaceChildren();
        const { createStubEngine } = await import('@/lib/stub-engine');
        engine = createStubEngine(kind);
        await engine.mount(slot.el);
      }
      slot.engine = engine;
      // finished mounting after the reader already moved to the other view
      if (active !== kind) engine.pause();
      statusOff[kind] = engine.onStatus((s) => {
        lastStatus[kind] = s;
        if (active !== kind) return;
        statusListeners.forEach((cb) => cb(s));
      });
      mountListeners[kind].forEach((cb) => cb(engine));
      return engine;
    })();
    return slot.mountPromise;
  }

  function fadeSwap(next: EngineKind, prev: EngineKind | null) {
    window.clearTimeout(pauseTimers[next]);
    // First-view case: no fade-out sequence; just show the incoming layer at full opacity.
    if (!prev || prev === next || reduceMotion) {
      setSlotVisible(next, true, 0);
      slots[next].engine?.resume();
      return;
    }
    // Two-phase sequence: fade the outgoing layer to the stage background, then fade the
    // incoming layer in. The incoming layer stays at opacity 0 until the fade-in begins so
    // the two scenes never overlay (docs/ux/2026-09-13-motion-and-framing.md).
    setSlotVisible(next, false, 0);
    slots[next].engine?.resume();
    setSlotVisible(prev, false, FADE_OUT_MS);
    pauseTimers[next] = window.setTimeout(() => {
      if (active !== next) return;
      setSlotVisible(next, true, FADE_IN_MS);
      // pause the outgoing engine once the fade-in has started, unless the reader came back meanwhile
      pauseTimers[prev] = window.setTimeout(() => {
        if (active !== prev) slots[prev].engine?.pause();
      }, FADE_IN_MS + 40);
    }, FADE_OUT_MS);
  }

  let applyToken = 0;
  async function applyState(state: SceneState): Promise<void> {
    const token = ++applyToken;
    // Swap the containers right away. The crossfade must not wait for the incoming
    // engine: a slow mount (tiles, textures, a backgrounded tab) would otherwise keep
    // the previous view on screen for a chapter it does not belong to.
    const prev = active;
    active = state.view;
    if (prev !== state.view) {
      fadeSwap(state.view, prev);
      // re-announce the incoming engine's last status so the legend swaps attributions
      const s = lastStatus[state.view];
      if (s) statusListeners.forEach((cb) => cb(s));
    }
    const engine = await ensureMounted(state.view);
    // A later chapter change superseded this one while the engine was loading.
    if (token !== applyToken) return;
    engine.resume();
    await engine.setState(state);
  }

  function applyTime(unit: 'ma' | 'ka', value: number): void {
    if (!active) return;
    slots[active].engine?.setTime(unit, value);
  }

  async function preload(state: SceneState): Promise<void> {
    const engine = await ensureMounted(state.view);
    await engine.preload(state);
  }

  function resize() {
    slots.globe.engine?.resize();
    slots.terrain.engine?.resize();
  }

  function destroy() {
    (Object.keys(slots) as EngineKind[]).forEach((k) => {
      window.clearTimeout(pauseTimers[k]);
      statusOff[k]?.();
      mountListeners[k].clear();
      slots[k].engine?.dispose();
      slots[k].engine = null;
      slots[k].mountPromise = null;
    });
  }

  return {
    ensureMounted,
    onMounted(kind, cb) {
      const e = slots[kind].engine;
      if (e) cb(e);
      else mountListeners[kind].add(cb);
      return () => { mountListeners[kind].delete(cb); };
    },
    applyState,
    applyTime,
    preload,
    activeKind: () => active,
    onStatus(cb) {
      statusListeners.add(cb);
      return () => statusListeners.delete(cb);
    },
    resize,
    destroy,
  };
}
