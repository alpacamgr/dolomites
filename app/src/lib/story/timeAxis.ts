/**
 * Geometry of the time rail: a broken axis with a magnified inset for the last
 * ~130 ka. Pure and browser-safe. Positions are percentages of the axis width.
 * See docs/ux/2026-09-timeline-and-geology-ux.md, section 2.
 */
import type { ClientChapter } from './types';

export interface AxisSpec {
  /** oldest time on the axis, Ma */
  windowMa: number;
  /** start of the magnified inset, Ma; 0 = no inset */
  insetMa: number;
  /** width of the break between the two parts, % of the axis */
  gapPct: number;
}

/** Inset share of the axis width while a Ma chapter or a ka chapter is active. */
export const LENS_MA = 0.16;
export const LENS_KA = 0.62;

const toMa = (unit: 'ma' | 'ka', v: number) => (unit === 'ka' ? v / 1000 : v);

/** Interval a chapter is placed at on the axis (Ma, older first). */
export function chapterInterval(ch: ClientChapter): { start_ma: number; end_ma: number } {
  if (ch.subject) return ch.subject;
  const a = toMa(ch.time.unit, ch.time.start);
  const b = toMa(ch.time.unit, ch.time.end);
  return { start_ma: Math.max(a, b), end_ma: Math.min(a, b) };
}

/** Axis extent from the chapters: the oldest chapter time, and an inset covering every ka chapter. */
export function axisSpec(chapters: ClientChapter[]): AxisSpec {
  let windowMa = 0;
  let insetKa = 0;
  for (const ch of chapters) {
    windowMa = Math.max(windowMa, chapterInterval(ch).start_ma);
    if (ch.time.unit === 'ka') insetKa = Math.max(insetKa, ch.time.start, ch.time.end);
  }
  // pad the inset a little and round up to 10 ka so its left edge gets a clean label
  const insetMa = insetKa > 0 ? (Math.ceil((insetKa * 1.08) / 10) * 10) / 1000 : 0;
  return { windowMa: windowMa || 1, insetMa, gapPct: insetMa > 0 ? 2.6 : 0 };
}

/** x position (% of the axis) of an age in Ma, for inset share `f` (0..1). */
export function xPct(ma: number, s: AxisSpec, f: number): number {
  const m = Math.min(Math.max(ma, 0), s.windowMa);
  if (s.insetMa <= 0) return ((s.windowMa - m) / s.windowMa) * 100;
  const usable = 100 - s.gapPct;
  const maW = usable * (1 - f);
  if (m >= s.insetMa) return ((s.windowMa - m) / (s.windowMa - s.insetMa)) * maW;
  return maW + s.gapPct + ((s.insetMa - m) / s.insetMa) * usable * f;
}

/**
 * Spread button centres (px) so neighbours keep at least `min` px apart, inside [lo, hi].
 * Order along the axis is kept; ties keep reading order.
 */
export function relax(xs: number[], min: number, lo: number, hi: number): number[] {
  const idx = xs.map((_, i) => i).sort((a, b) => xs[a] - xs[b] || a - b);
  const out = xs.slice();
  let prev = -Infinity;
  for (const i of idx) {
    out[i] = Math.max(lo, out[i], prev + min);
    prev = out[i];
  }
  let next = Infinity;
  for (let k = idx.length - 1; k >= 0; k--) {
    const i = idx[k];
    out[i] = Math.min(hi, out[i], next - min);
    next = out[i];
  }
  return out;
}

/** Frame-rate independent exponential damping factor for a step of `dt` ms. */
export function damp(dt: number, tauMs: number): number {
  return tauMs <= 0 ? 1 : 1 - Math.exp(-dt / tauMs);
}
