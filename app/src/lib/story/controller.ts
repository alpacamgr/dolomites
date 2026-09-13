/**
 * Scroll-driven story controller.
 *
 *  - One narrative section per chapter carries `data-chapter="<id>"`.
 *  - Reading band: the part of the viewport where the reader reads, below the sticky header
 *    (desktop) or below the sticky stage when it sits above the text (mobile, 55svh). The active
 *    chapter is the last section whose top has passed the band's reading line; progress 0..1
 *    runs from the section's top meeting the band top to its end. goToChapter lands a section's
 *    top at the band top (the CSS scroll-margin-top matches), so jumps and detection agree in
 *    both layouts.
 *  - One rAF loop eases the displayed time toward the scroll target with frame-rate
 *    independent exponential damping (docs/ux/2026-09-timeline-and-geology-ux.md, motion spec)
 *    and stops as soon as it settles. It is the only caller of engine.setTime: at most one call
 *    per frame, none while settled.
 *  - A chapter change issues engine.setState with the new chapter's target time; the displayed
 *    time for the rail keeps easing from its previous value instead of snapping.
 *  - Relative jumps (stepper, PageUp/PageDown) count from a jump still in progress, so two quick
 *    "next" presses move two chapters.
 *  - Keyboard: arrow keys, Home and End stay native. PageUp/PageDown jump chapters only while the
 *    reading line is inside the story, without modifiers, when no other handler consumed the key
 *    and focus is not in a form control or key-handling widget. At the last chapter PageDown
 *    scrolls natively on to the sources.
 *  - prefers-reduced-motion: no damping, time follows scroll directly; jumps are instant.
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
  /** Jump relative to the chapter being read, or to the target of a jump still in progress. */
  step(delta: number): void;
  destroy(): void;
  getEngineManager(): EngineManager;
}

interface StartOptions {
  chapters: ClientChapter[];
  narrativeRoot: HTMLElement;
  globeEl: HTMLElement;
  terrainEl: HTMLElement;
  reduceMotion?: boolean;
  /** passed to the engine factories (localized strings, locale, ICS intervals) */
  engineOptions?: Record<string, unknown>;
}

/** Damping time constants (ms): inside a chapter, and while the rail catches up after a chapter change.
 *  TAU_CHAPTER raised from 200 to 350 in 2026-09-13 so the readout does not race through 300 Myr
 *  in a blink on intro → Permian; see docs/ux/2026-09-13-motion-and-framing.md. */
const TAU_SCROLL = 90;
const TAU_CHAPTER = 350;
/** Reading line position inside the reading band (0 = band top, 1 = viewport bottom). */
const READING_LINE = 0.4;
/** A programmatic jump counts as finished after this long without scroll events. */
const JUMP_SETTLE_MS = 250;

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
const toMa = (unit: 'ma' | 'ka', v: number) => (unit === 'ka' ? v / 1000 : v);
const fromMa = (unit: 'ma' | 'ka', ma: number) => (unit === 'ka' ? ma * 1000 : ma);
/** settle threshold in Ma: 0.01 of the chapter's unit */
const epsMa = (unit: 'ma' | 'ka') => (unit === 'ka' ? 1e-5 : 1e-2);

/** Elements that handle PageUp/PageDown themselves. */
const KEY_WIDGETS = 'input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="slider"], [role="spinbutton"], '
  + '[role="listbox"], [role="combobox"], [role="menu"], [role="menubar"], [role="textbox"], [role="grid"], [role="tree"], [role="tablist"]';

export function startStory(opts: StartOptions): StoryController {
  const { chapters, narrativeRoot, globeEl, terrainEl, reduceMotion = false } = opts;
  const em = createEngineManager(globeEl, terrainEl, { reduceMotion, engineOptions: opts.engineOptions });

  const sections = Array.from(narrativeRoot.querySelectorAll<HTMLElement>('[data-chapter]'));
  const header = document.querySelector<HTMLElement>('.masthead');
  const stageWrap = globeEl.closest<HTMLElement>('.stage-wrap') ?? globeEl.parentElement;

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
  /** target of a programmatic jump that is still scrolling */
  let pendingTarget: number | null = null;
  let pendingTimer = 0;

  /** One-frame scheduler: rAF when visible; a 16 ms timeout when hidden (no frames there). */
  function schedule() {
    if (scheduled || destroyed) return;
    scheduled = true;
    const run = (now: number) => { scheduled = false; tick(now); };
    if (document.hidden) window.setTimeout(() => run(performance.now()), 16);
    else requestAnimationFrame(run);
  }

  /**
   * The reading band in viewport coordinates: its top is the lowest bottom edge of whatever
   * covers the top of the text column (the sticky header, or the stage when it is stacked
   * above the narrative rather than beside it).
   */
  function readingBand(): { top: number; line: number } {
    const vh = window.innerHeight;
    let top = 0;
    const hr = header?.getBoundingClientRect();
    if (hr && hr.top <= 1 && hr.bottom > 0) top = Math.max(top, hr.bottom);
    const sr = stageWrap?.getBoundingClientRect();
    const nr = narrativeRoot.getBoundingClientRect();
    if (sr && sr.bottom > 0 && sr.top < vh && sr.left < nr.right - 1 && sr.right > nr.left + 1) top = Math.max(top, sr.bottom);
    top = Math.min(top, vh - 80);
    return { top, line: top + (vh - top) * READING_LINE };
  }

  /** The last section whose top has reached the reading line (sections are in document order). */
  function activeIndexAt(line: number): number {
    let idx = 0;
    for (let i = 0; i < sections.length; i++) {
      if (sections[i].getBoundingClientRect().top <= line + 1) idx = i;
      else break;
    }
    return idx;
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

  /** Read scroll: active chapter, progress and target time. Returns true if state changed. */
  function measure(): boolean {
    let changed = false;
    const band = readingBand();
    const nextIndex = activeIndexAt(band.line);
    if (nextIndex !== state.activeIndex) {
      state.activeIndex = nextIndex;
      changed = true;
      if (initialized) chapterTween = true;
    }
    const ch = chapters[state.activeIndex];
    const section = sections[state.activeIndex];
    if (ch && section) {
      const rect = section.getBoundingClientRect();
      const traversable = Math.max(1, rect.height - (window.innerHeight - band.top));
      const progress = clamp01((band.top - rect.top) / traversable);
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

  /** A jump is over once scrolling has been quiet for JUMP_SETTLE_MS (or on scrollend). */
  function armJumpSettle() {
    window.clearTimeout(pendingTimer);
    if (pendingTarget !== null) pendingTimer = window.setTimeout(() => { pendingTarget = null; }, JUMP_SETTLE_MS);
  }
  function onScroll() {
    if (pendingTarget !== null) armJumpSettle();
    requestMeasure();
  }
  function onScrollEnd() {
    pendingTarget = null;
    window.clearTimeout(pendingTimer);
  }

  // The scroll listener does the real work; IntersectionObserver is a nudge for touch and
  // momentum scrolling where scroll events can be sparse.
  const io = new IntersectionObserver(requestMeasure, { rootMargin: '-30% 0px -30% 0px', threshold: [0, 0.5, 1] });
  sections.forEach((s) => io.observe(s));
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('scrollend', onScrollEnd);
  const ro = new ResizeObserver(() => {
    em.resize();
    requestMeasure();
  });
  ro.observe(document.body);

  function onKey(e: KeyboardEvent) {
    if (e.key !== 'PageDown' && e.key !== 'PageUp') return;
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.target instanceof Element && e.target.closest(KEY_WIDGETS)) return;
    const band = readingBand();
    const last = sections[sections.length - 1]?.getBoundingClientRect();
    // at or past the end of the story (sources, footer): native scrolling
    if (!last || band.line >= last.bottom) return;
    const current = pendingTarget ?? activeIndexAt(band.line);
    if (e.key === 'PageDown' && current >= sections.length - 1) return;
    if (e.key === 'PageUp' && current <= 0) return;
    e.preventDefault();
    step(e.key === 'PageDown' ? 1 : -1);
  }
  window.addEventListener('keydown', onKey);

  function goToChapter(index: number, options: { smooth?: boolean } = {}) {
    const idx = Math.max(0, Math.min(chapters.length - 1, index));
    const section = sections[idx];
    if (!section) return;
    const smooth = !(reduceMotion || options.smooth === false);
    pendingTarget = smooth ? idx : null;
    armJumpSettle();
    section.scrollIntoView({ block: 'start', behavior: smooth ? 'smooth' : 'auto' });
  }

  function step(delta: number) {
    const base = pendingTarget ?? activeIndexAt(readingBand().line);
    goToChapter(base + delta);
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
    step,
    getEngineManager: () => em,
    destroy() {
      destroyed = true;
      window.clearTimeout(pendingTimer);
      io.disconnect();
      ro.disconnect();
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('scrollend', onScrollEnd);
      window.removeEventListener('keydown', onKey);
      em.destroy();
      subs.clear();
    },
  };
}
