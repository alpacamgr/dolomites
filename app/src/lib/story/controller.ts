/**
 * Scroll-driven story controller.
 *
 *  - One narrative section per chapter carries `data-chapter="<id>"`.
 *  - The active chapter is the section whose midpoint is closest to the viewport
 *    midpoint; progress 0..1 within it maps linearly to a *target* time between
 *    scene.time.start and scene.time.end.
 *  - One rAF loop eases the displayed time toward the target with frame-rate
 *    independent exponential damping (docs/ux/2026-09-timeline-and-geology-ux.md,
 *    motion spec) and stops as soon as it settles. The loop is the only caller of
 *    engine.setTime: at most one call per frame, none while settled.
 *  - A chapter change issues engine.setState with the new chapter's target time
 *    (a view switch triggers the crossfade in the engine manager); the displayed time
 *    for the rail keeps easing from its previous value instead of snapping.
 *  - prefers-reduced-motion: no damping, time follows scroll directly.
 *  - Preloads the next chapter's state when its section is within one viewport of the fold.
 *
 * The controller exposes a small Svelte-shaped store (subscribe) so the TimeRail,
 * Legend and DebugOverlay can react without knowing about scroll internals.
 */
import type { ClientChapter } from './types';
import { toSceneState } from './types';
import { createEngineManager, type EngineManager } from './engineManager';
import { damp } from './timeAxis';

export interface StoryState {
  activeIndex: number;
  /** reading progress 0..1 within the active chapter */
  progress: number;
  timeUnit: 'ma' | 'ka';
  /** displayed (eased) time in `timeUnit` */
  time: number;
  engineLoading: boolean;
  attributions: string[];
}

type Subscriber = (s: StoryState) => void;

export interface StoryController {
  subscribe(cb: Subscriber): () => void;
  goToChapter(index: number, opts?: { smooth?: boolean }): void;
  destroy(): void;
  getEngineManager(): EngineManager;
}

interface StartOptions {
  chapters: ClientChapter[];
  narrativeRoot: HTMLElement;
  globeEl: HTMLElement;
  terrainEl: HTMLElement;
  reduceMotion?: boolean;
  /** passed to the engine factories (localized popup strings, locale) */
  engineOptions?: Record<string, unknown>;
}

/** Damping time constants (ms): inside a chapter, and while the rail catches up after a chapter change. */
const TAU_SCROLL = 90;
const TAU_CHAPTER = 200;

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
const toMa = (unit: 'ma' | 'ka', v: number) => (unit === 'ka' ? v / 1000 : v);
const fromMa = (unit: 'ma' | 'ka', ma: number) => (unit === 'ka' ? ma * 1000 : ma);
/** settle threshold in Ma: 0.01 of the chapter's unit */
const epsMa = (unit: 'ma' | 'ka') => (unit === 'ka' ? 1e-5 : 1e-2);

export function startStory(opts: StartOptions): StoryController {
  const { chapters, narrativeRoot, globeEl, terrainEl, reduceMotion = false } = opts;
  const em = createEngineManager(globeEl, terrainEl, { reduceMotion, engineOptions: opts.engineOptions });

  const sections = Array.from(narrativeRoot.querySelectorAll<HTMLElement>('[data-chapter]'));

  const first = chapters[0];
  const state: StoryState = {
    activeIndex: 0,
    progress: 0,
    timeUnit: first?.time.unit ?? 'ma',
    time: first?.time.start ?? 0,
    engineLoading: false,
    attributions: [],
  };

  const subs = new Set<Subscriber>();
  const emit = () => subs.forEach((cb) => cb({ ...state }));

  // Active engine status -> merged into state (legend shows the attributions)
  em.onStatus((s) => {
    state.engineLoading = s.loading;
    state.attributions = s.attributions;
    emit();
  });

  let displayMa = first ? toMa(first.time.unit, first.time.start) : 0;
  let targetMa = displayMa;
  /** true while the rail eases across a chapter change (engines already have the target) */
  let chapterTween = false;
  let engineMa = Number.NaN;
  let initialized = false;
  let needsMeasure = true;
  let scheduled = false;
  let lastT = 0;
  let currentAppliedIndex = -1;
  let destroyed = false;

  /** One-frame scheduler: rAF when visible; a 16 ms timeout when hidden (no frames there). */
  function schedule() {
    if (scheduled || destroyed) return;
    scheduled = true;
    const run = (now: number) => { scheduled = false; tick(now); };
    if (document.hidden) window.setTimeout(() => run(performance.now()), 16);
    else requestAnimationFrame(run);
  }

  function applyChapter(index: number) {
    const ch = chapters[index];
    if (!ch) return;
    currentAppliedIndex = index;
    engineMa = targetMa;
    em.applyState(toSceneState(ch, fromMa(ch.time.unit, targetMa))).catch((err) => {
      console.error(`[story] setState failed for chapter ${ch.id}`, err);
    });
    const next = chapters[index + 1];
    if (next) em.preload(toSceneState(next, next.time.start)).catch(() => { /* not fatal */ });
  }

  /** The section whose midpoint is closest to the viewport midpoint. */
  function activeIndexFromScroll(): number {
    const target = window.innerHeight * 0.5;
    let best = state.activeIndex;
    let bestDist = Infinity;
    for (let i = 0; i < sections.length; i++) {
      const r = sections[i].getBoundingClientRect();
      const d = Math.abs(r.top + r.height * 0.5 - target);
      if (d < bestDist) { bestDist = d; best = i; }
    }
    return best;
  }

  /** Read scroll: active chapter, progress and target time. Returns true if state changed. */
  function measure(): boolean {
    let changed = false;
    const nextIndex = activeIndexFromScroll();
    if (nextIndex !== state.activeIndex) {
      state.activeIndex = nextIndex;
      changed = true;
      if (initialized) chapterTween = true;
    }
    const ch = chapters[state.activeIndex];
    const section = sections[state.activeIndex];
    if (ch && section) {
      const rect = section.getBoundingClientRect();
      const traversable = Math.max(1, rect.height - window.innerHeight);
      const progress = clamp01(-rect.top / traversable);
      if (changed || Math.abs(progress - state.progress) >= 0.0005) {
        state.progress = progress;
        changed = true;
      }
      targetMa = toMa(ch.time.unit, lerp(ch.time.start, ch.time.end, state.progress));
      state.timeUnit = ch.time.unit;
    }
    if (state.activeIndex !== currentAppliedIndex) applyChapter(state.activeIndex);

    const upcoming = sections[state.activeIndex + 1];
    if (upcoming && upcoming.getBoundingClientRect().top < window.innerHeight * 2) {
      const uc = chapters[state.activeIndex + 1];
      if (uc) em.preload(toSceneState(uc, uc.time.start)).catch(() => {});
    }
    return changed;
  }

  function tick(now: number) {
    const dt = lastT ? Math.min(64, now - lastT) : 16.7;
    let changed = false;
    if (needsMeasure) {
      needsMeasure = false;
      changed = measure();
    }
    if (!initialized) {
      initialized = true;
      displayMa = targetMa;
    }
    const ch = chapters[state.activeIndex];
    if (!ch) return;
    const eps = epsMa(ch.time.unit);

    const prev = displayMa;
    displayMa += (targetMa - displayMa) * (reduceMotion ? 1 : damp(dt, chapterTween ? TAU_CHAPTER : TAU_SCROLL));
    const settled = Math.abs(targetMa - displayMa) < eps;
    if (settled) {
      displayMa = targetMa;
      chapterTween = false;
    }
    if (displayMa !== prev) changed = true;
    state.time = fromMa(ch.time.unit, displayMa);

    // Engines follow the eased time inside a chapter; after a chapter change they already
    // have the target from setState, so they only hear about further scrolling.
    const wantEngine = chapterTween ? targetMa : displayMa;
    if (wantEngine !== engineMa && (settled || chapterTween || Math.abs(wantEngine - engineMa) >= eps * 0.5 || Number.isNaN(engineMa))) {
      engineMa = wantEngine;
      em.applyTime(ch.time.unit, fromMa(ch.time.unit, wantEngine));
    }

    if (changed) emit();
    if (settled && !needsMeasure) lastT = 0;
    else { lastT = now; schedule(); }
  }

  function requestMeasure() {
    needsMeasure = true;
    schedule();
  }

  // The scroll listener does the real work; IntersectionObserver is a nudge for touch and
  // momentum scrolling where scroll events can be sparse.
  const io = new IntersectionObserver(requestMeasure, { rootMargin: '-30% 0px -30% 0px', threshold: [0, 0.5, 1] });
  sections.forEach((s) => io.observe(s));
  window.addEventListener('scroll', requestMeasure, { passive: true });
  const ro = new ResizeObserver(() => {
    em.resize();
    requestMeasure();
  });
  ro.observe(document.body);

  function onKey(e: KeyboardEvent) {
    if (e.target instanceof HTMLElement) {
      const tag = e.target.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) return;
    }
    if (e.key === 'ArrowDown' || e.key === 'PageDown') {
      e.preventDefault();
      goToChapter(state.activeIndex + 1);
    } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
      e.preventDefault();
      goToChapter(state.activeIndex - 1);
    } else if (e.key === 'Home') {
      e.preventDefault();
      goToChapter(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      goToChapter(chapters.length - 1);
    }
  }
  window.addEventListener('keydown', onKey);

  function goToChapter(index: number, options: { smooth?: boolean } = {}) {
    const idx = Math.max(0, Math.min(chapters.length - 1, index));
    const section = sections[idx];
    if (!section) return;
    const behavior: ScrollBehavior = reduceMotion || options.smooth === false ? 'auto' : 'smooth';
    section.scrollIntoView({ block: 'start', behavior });
  }

  // First paint: apply the section that matches the current scroll, without easing.
  requestMeasure();

  return {
    subscribe(cb) {
      subs.add(cb);
      cb({ ...state });
      return () => subs.delete(cb);
    },
    goToChapter,
    getEngineManager: () => em,
    destroy() {
      destroyed = true;
      io.disconnect();
      ro.disconnect();
      window.removeEventListener('scroll', requestMeasure);
      window.removeEventListener('keydown', onKey);
      em.destroy();
      subs.clear();
    },
  };
}
