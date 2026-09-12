/**
 * Geology colour key. The terrain engine reports the unit colours rendered in the
 * current view; this module groups them into ICS rows for the legend. Pure and
 * browser-safe: names and colours come only from ics-chart.json and the localized
 * ICS names. See docs/ux/2026-09-timeline-and-geology-ux.md, section 4.
 */
import type { IcsChart, IcsInterval } from '@/lib/content/ics';

/** What the terrain engine reports for the current view. */
export interface GeologyKeyData {
  /** distinct dated units in view, by colour and younger age bound */
  units: Array<{ color: string; ageMin: number | null }>;
  /** units whose source gives no usable age (age_basis none, or tiles without age_basis) are rendered in view */
  undated: boolean;
  /** units whose stated age is withheld from colour (age_basis withheld) are rendered in view */
  withheld: boolean;
  /** sources mapped coarser than 1:25,000 with units rendered in view: dataset id, localized name, formatted scale */
  coarse: Array<{ id: string; name: string; scale: string }>;
  /** a gaps layer (areas with no open geological map) is loaded */
  gapsLayer: boolean;
}

/** Units to highlight on the map; everything else is dimmed. */
export interface GeologyFocus {
  /** `unitKey()` strings of dated units */
  keys?: string[];
  undated?: boolean;
  /** units whose mapped age range lies within this interval (Ma, older first) */
  within?: { start_ma: number; end_ma: number };
}

export interface KeyRow {
  id: string;
  label: string;
  /** colours present in this row, older first */
  colors: string[];
  keys: string[];
  /** localized interval name of an era- or eon-only row */
  name?: string;
}

/**
 * Same string as the terrain engine's expression
 * `['concat', ['get','color'], '|', ['to-string', ['get','age_min_ma']]]` (to-string of null is '').
 */
export function unitKey(color: string, ageMin: number | null): string {
  return `${color}|${ageMin == null ? '' : String(ageMin)}`;
}

const EPS = 1e-3;
const fill = (s: string, vars: Record<string, string>) => s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');

/**
 * Group units into rows, youngest first. The colour is the ICS colour of the unit's
 * younger named interval, whose end is `age_min_ma`; that pair identifies the interval
 * even where two intervals share a colour. Rows are periods; units named only at era or
 * eon level get their own row; units older than the chart window form one "pre-" row.
 */
export function groupGeologyKey(
  ics: IcsChart | null,
  units: GeologyKeyData['units'],
  tr: (name: string) => string,
  t: (key: string, fallback?: string) => string,
  locale: string,
): KeyRow[] {
  const periods = ics ? ics.intervals.filter((i) => i.type === 'period') : [];
  const oldest = periods.reduce<IcsInterval | null>((a, p) => (!a || p.start_ma > a.start_ma ? p : a), null);
  const byColor = new Map<string, IcsInterval[]>();
  for (const i of ics?.intervals ?? []) {
    if (!i.color) continue;
    const k = i.color.toLowerCase();
    byColor.set(k, [...(byColor.get(k) ?? []), i]);
  }
  const nf = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const rows = new Map<string, { row: KeyRow; sort: number; order: Map<string, number> }>();
  const add = (id: string, label: string, sort: number, color: string, key: string, age: number, name?: string) => {
    let r = rows.get(id);
    if (!r) rows.set(id, (r = { row: { id, label, colors: [], keys: [], name }, sort, order: new Map() }));
    if (!r.row.keys.includes(key)) r.row.keys.push(key);
    if (!r.order.has(color)) r.order.set(color, age);
    else r.order.set(color, Math.max(r.order.get(color)!, age));
  };

  for (const u of units) {
    const key = unitKey(u.color, u.ageMin);
    const cands = byColor.get(u.color.toLowerCase()) ?? [];
    const iv = cands.find((i) => u.ageMin != null && Math.abs(i.end_ma - u.ageMin) < EPS)
      ?? cands.find((i) => i.type !== 'era' && i.type !== 'eon')
      ?? cands[0];
    if (iv && (iv.type === 'era' || iv.type === 'eon')) {
      add(`broad:${iv.name}`, fill(t('geology_key.period_not_given', '{name}, period not given'), { name: tr(iv.name) }),
        iv.start_ma + EPS, u.color, key, iv.start_ma, tr(iv.name));
      continue;
    }
    const ref = iv ? (iv.start_ma + iv.end_ma) / 2 : u.ageMin;
    const p = ref == null ? undefined : periods.find((x) => ref <= x.start_ma && ref >= x.end_ma);
    if (p) add(`period:${p.name}`, tr(p.name), p.start_ma, u.color, key, ref!);
    else if (ref != null && oldest && ref >= oldest.start_ma) {
      add('pre', fill(t('geology_key.pre', 'Pre-{name} (older than {ma} Ma)'), { name: tr(oldest.name), ma: nf.format(oldest.start_ma) }),
        Number.MAX_VALUE, u.color, key, ref);
    } else add('other', t('geology_key.other', 'Other dated units'), Infinity, u.color, key, ref ?? 0);
  }

  const sorted = [...rows.values()]
    .sort((a, b) => a.sort - b.sort)
    .map(({ row, order }) => ({ ...row, colors: [...order.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c) }));
  // several era- or eon-only rows collapse into one ("Period not given: Cenozoic, Mesozoic, Paleozoic"), youngest first
  const broad = sorted.filter((r) => r.id.startsWith('broad:'));
  if (broad.length < 2) return sorted;
  const merged: KeyRow = {
    id: 'broad',
    label: fill(t('geology_key.period_not_given_many', 'Period not given: {names}'), { names: broad.map((r) => r.name ?? r.label).join(', ') }),
    colors: broad.flatMap((r) => r.colors),
    keys: broad.flatMap((r) => r.keys),
  };
  const out = sorted.filter((r) => !r.id.startsWith('broad:'));
  out.splice(sorted.indexOf(broad[0]), 0, merged);
  return out;
}

/** Localized name of the ICS interval matching [start, end] exactly, else null. */
export function intervalName(ics: IcsChart | null, start_ma: number, end_ma: number, tr: (n: string) => string): string | null {
  const hit = ics?.intervals.find((i) => Math.abs(i.start_ma - start_ma) < 0.01 && Math.abs(i.end_ma - end_ma) < 0.01);
  return hit ? tr(hit.name) : null;
}
