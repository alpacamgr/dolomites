<!--
  Time rail: the chapter's time, what the map shows, and a broken time axis (the story's
  full span plus a magnified inset for the last ~130 ka) with ICS periods and epochs and
  the chapters placed at their intervals in one row per map type. Names and colours come
  only from ics-chart.json and content/ui `ics_names`.
  Design: docs/ux/2026-09-timeline-and-geology-ux.md.
-->
<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import type { Locale } from '@/lib/i18n/client';
  import { formatAge, formatPaleoLat } from '@/lib/i18n/client';
  import type { IcsChart, IcsInterval } from '@/lib/content/ics';
  import type { ClientChapter } from '@/lib/story/types';
  import { loadPaleoPath, paleoLatAt, type PaleoPath } from '@/lib/story/paleoLat';
  import { axisSpec, chapterInterval, damp, relax, xPct, LENS_KA, LENS_MA } from '@/lib/story/timeAxis';

  let { locale, uiStrings, ics, chapters, activeIndex, progress, unit, value, reduceMotion = false, onJump }: {
    locale: Locale;
    uiStrings: Record<string, string>;
    ics: IcsChart | null;
    chapters: ClientChapter[];
    activeIndex: number;
    /** reading progress 0..1 within the active chapter */
    progress: number;
    unit: 'ma' | 'ka';
    /** displayed (eased) time in `unit` */
    value: number;
    reduceMotion?: boolean;
    onJump: (index: number) => void;
  } = $props();

  const t = (k: string, fb?: string) => uiStrings[k] ?? fb ?? k;
  /** Official localized ICS name from content/ui/<lang>.json `ics_names`, English fallback. */
  const tr = (name: string) => uiStrings[`ics_names.${name}`] ?? name;
  const fill = (s: string, v: Record<string, string>) => s.replace(/\{(\w+)\}/g, (_, k) => v[k] ?? '');
  const nfInt = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const nfDec = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
  const MA = t('time.ma', 'Ma');
  const KA = t('time.ka', 'ka');
  const NOW = t('time.now', 'today');
  const cap = (s: string) => s.charAt(0).toLocaleUpperCase(locale) + s.slice(1);

  // ---- static axis content ------------------------------------------------------------
  const spec = untrack(() => axisSpec(chapters));
  const chapterIv = untrack(() => chapters.map(chapterInterval));
  const intervals = untrack(() => ics?.intervals ?? []);
  const ofType = (type: string) =>
    intervals.filter((i) => i.type === type && i.end_ma < spec.windowMa).sort((a, b) => b.start_ma - a.start_ma);
  const periods = ofType('period');
  const epochs = ofType('epoch');

  interface Seg { name: string; color: string; older: number; younger: number; band: boolean }
  const segs: Seg[] = [];
  const clip = (list: IcsInterval[], lo: number, hi: number, band: boolean) => {
    for (const i of list) {
      const older = Math.min(i.start_ma, hi);
      const younger = Math.max(i.end_ma, lo);
      if (i.color && older - younger > 1e-9) segs.push({ name: i.name, color: i.color, older, younger, band });
    }
  };
  if (spec.insetMa > 0) {
    // main part: periods over epochs; magnified inset: epochs over ages
    clip(periods, spec.insetMa, spec.windowMa, true);
    clip(epochs, spec.insetMa, spec.windowMa, false);
    // a hair below the inset start, so inset segments begin after the break gap (xPct maps insetMa itself to the gap's left edge)
    clip(epochs, 0, spec.insetMa - 1e-9, true);
    clip(ofType('age'), 0, spec.insetMa - 1e-9, false);
  } else {
    clip(periods, 0, spec.windowMa, true);
    clip(epochs, 0, spec.windowMa, false);
  }

  /** Dark or light label on an ICS colour. */
  function ink(hex: string): string {
    const n = parseInt(hex.slice(1, 7), 16);
    const lum = 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
    return lum < 150 ? '#fff' : '#1c1b18';
  }

  // ---- chapter lane: one row per map type, reading order kept within a row ------------------
  /**
   * Chapters are grouped by view (reconstruction vs today's terrain). Within a row only the
   * longest run of chapters whose position on the axis follows reading order is placed, so
   * every row reads 2 3 4 5 / 6 7 8 9. A chapter that would break it (the intro, which shows
   * today before the story starts) stays reachable through the chapter stepper.
   */
  const lane = untrack(() => {
    const byView = new Map<string, number[]>();
    chapters.forEach((c, i) => byView.set(c.view, [...(byView.get(c.view) ?? []), i]));
    const kept = new Set<number>();
    for (const idx of byView.values()) {
      const pos = idx.map((i) => -(chapterIv[i].start_ma + chapterIv[i].end_ma) / 2);
      const len = pos.map(() => 1);
      const prev = pos.map(() => -1);
      for (let a = 0; a < pos.length; a++) {
        for (let b = 0; b < a; b++) if (pos[b] <= pos[a] && len[b] + 1 > len[a]) { len[a] = len[b] + 1; prev[a] = b; }
      }
      let end = 0;
      for (let a = 1; a < pos.length; a++) if (len[a] > len[end]) end = a;
      for (let a = end; a >= 0; a = prev[a]) kept.add(idx[a]);
    }
    const first = (v: string) => Math.min(...byView.get(v)!.filter((i) => kept.has(i)));
    const rows = [...byView.keys()].filter((v) => byView.get(v)!.some((i) => kept.has(i))).sort((a, b) => first(a) - first(b));
    return { kept, rows };
  });
  const ROW_H = 21;
  const laneH = lane.rows.length * ROW_H + 1;

  // ---- text fitting -----------------------------------------------------------------------
  let ctx: CanvasRenderingContext2D | null = null;
  let fontReady = $state(false);
  const widths = new Map<string, number>();
  const textW = (s: string) => {
    let w = widths.get(s);
    if (w === undefined) {
      w = ctx ? ctx.measureText(s).width : s.length * 6;
      if (ctx) widths.set(s, w);
    }
    return w;
  };
  /** Full name if it fits, else a consistent short form (four letters, then three, with a full stop), else nothing. */
  function fitLabel(name: string, px: number): string {
    if (px < 12) return '';
    if (textW(name) <= px) return name;
    for (let k = Math.min(4, name.length - 1); k >= 3; k--) {
      const s = `${name.slice(0, k).trimEnd()}.`;
      if (textW(s) <= px) return s;
    }
    return '';
  }

  let paleoPath = $state<PaleoPath | null>(null);
  let axisW = $state(540);
  onMount(() => {
    ctx = document.createElement('canvas').getContext('2d');
    if (ctx) ctx.font = `500 10px ${getComputedStyle(document.body).fontFamily}`;
    fontReady = true;
    loadPaleoPath('/data').then((p) => {
      paleoPath = p;
    });
  });

  // ---- lens (inset share), eased only when the time unit changes --------------------------
  const lensFor = (u: 'ma' | 'ka') => (spec.insetMa > 0 ? (u === 'ka' ? LENS_KA : LENS_MA) : 0);
  let lens = $state(untrack(() => lensFor(unit)));
  $effect(() => {
    const target = lensFor(unit);
    if (reduceMotion) {
      lens = target;
      return;
    }
    let raf = 0;
    let last = 0;
    const step = (now: number) => {
      const dt = last ? Math.min(64, now - last) : 16.7;
      last = now;
      const cur = untrack(() => lens);
      const next = cur + (target - cur) * damp(dt, 160);
      if (Math.abs(target - next) < 0.001) {
        lens = target;
        return;
      }
      lens = next;
      raf = requestAnimationFrame(step);
    };
    if (untrack(() => lens) !== target) raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  });

  // ---- derived geometry -------------------------------------------------------------------
  let bandSegs = $derived.by(() => {
    void fontReady;
    return segs.map((s) => {
      const left = xPct(s.older, spec, lens);
      const width = Math.max(0, xPct(s.younger, spec, lens) - left);
      // the first band segment after the axis break keeps its label clear of the break slashes
      const afterBreak = s.band && spec.insetMa > 0 && Math.abs(s.older - spec.insetMa) < 1e-6;
      const label = s.band ? fitLabel(tr(s.name), (width / 100) * axisW - (afterBreak ? 12 : 6)) : '';
      return { ...s, left, width, label, afterBreak };
    });
  });
  let breakLeft = $derived((100 - spec.gapPct) * (1 - lens));

  let marks = $derived.by(() => {
    const out: Array<{ row: number; parts: Array<[number, number]>; cx: number } | null> = chapters.map(() => null);
    lane.rows.forEach((view, row) => {
      const idx = chapters.map((_, i) => i).filter((i) => chapters[i].view === view && lane.kept.has(i));
      const px = idx.map((i) => (xPct((chapterIv[i].start_ma + chapterIv[i].end_ma) / 2, spec, lens) / 100) * axisW);
      // leave room for the row glyph at the left edge
      const cx = relax(px, 19, 26, Math.max(26, axisW - 9));
      idx.forEach((i, k) => {
        const iv = chapterIv[i];
        const l = xPct(iv.start_ma, spec, lens);
        const r = xPct(iv.end_ma, spec, lens);
        const crosses = spec.insetMa > 0 && iv.start_ma > spec.insetMa && iv.end_ma < spec.insetMa;
        const parts: Array<[number, number]> = crosses ? [[l, breakLeft], [breakLeft + spec.gapPct, r]] : [[l, r]];
        out[i] = { row, parts, cx: (cx[k] / axisW) * 100 };
      });
    });
    return out;
  });

  /** Scale labels placed by measured width: ends first, then the inset start, then round values. */
  let ticks = $derived.by(() => {
    void fontReady;
    const px = (x: number) => (x / 100) * axisW;
    const cands: Array<{ x: number; text: string; align: 'start' | 'mid' | 'end' }> = [
      { x: 0, text: `${nfInt.format(spec.windowMa)} ${MA}`, align: 'start' },
      { x: 100, text: NOW, align: 'end' },
    ];
    if (spec.insetMa > 0) cands.push({ x: breakLeft + spec.gapPct, text: `${nfInt.format(spec.insetMa * 1000)} ${KA}`, align: 'start' });
    const step = spec.windowMa > 150 ? 50 : 10;
    for (let m = Math.ceil(spec.windowMa / step - 1) * step; m > spec.insetMa; m -= step) {
      cands.push({ x: xPct(m, spec, lens), text: nfInt.format(m), align: 'mid' });
    }
    if (spec.insetMa > 0) {
      // the magnified part always carries its unit, so it cannot be read as Ma
      for (let k = Math.ceil((spec.insetMa * 1000) / 50 - 1) * 50; k > 0; k -= 50) {
        cands.push({ x: xPct(k / 1000, spec, lens), text: `${nfInt.format(k)} ${KA}`, align: 'mid' });
      }
    }
    const brk = spec.insetMa > 0 ? [px(breakLeft) - 6, px(breakLeft + spec.gapPct) + 6] : null;
    const placed: Array<[number, number]> = [];
    const out: typeof cands = [];
    for (const c of cands) {
      const w = textW(c.text) * 1.04 + 2;
      const x = px(c.x);
      const a = c.align === 'start' ? x : c.align === 'end' ? x - w : x - w / 2;
      const b = a + w;
      if (a < -1 || b > axisW + 1) continue;
      if (brk && c.align === 'mid' && a < brk[1] && b > brk[0]) continue;
      if (placed.some(([p, q]) => a < q + 10 && b > p - 10)) continue;
      placed.push([a, b]);
      out.push(c);
    }
    return out;
  });

  // ---- readouts ---------------------------------------------------------------------------
  const ageText = (ma: number) => (ma <= 0 ? NOW : ma < 1 ? `${nfInt.format(ma * 1000)} ${KA}` : `${nfDec.format(ma)} ${MA}`);
  function rangeText(iv: { start_ma: number; end_ma: number }): string {
    if (iv.start_ma === iv.end_ma) return ageText(iv.start_ma);
    if (iv.end_ma >= 1) return `${nfDec.format(iv.start_ma)}–${nfDec.format(iv.end_ma)} ${MA}`;
    return `${ageText(iv.start_ma)} – ${ageText(iv.end_ma)}`;
  }

  let active = $derived(chapters[activeIndex]);
  let view = $derived<'globe' | 'terrain'>(active?.view ?? 'globe');
  /** a past topic shown on a static map (scene time does not move); chapters that animate time show the time */
  let subject = $derived(active?.subject && active.time.start === active.time.end ? active.subject : undefined);
  let ageMa = $derived(unit === 'ka' ? value / 1000 : value);
  let markerX = $derived(xPct(ageMa, spec, lens));
  let subjectBox = $derived(subject ? { left: xPct(subject.start_ma, spec, lens), right: xPct(subject.end_ma, spec, lens) } : null);

  /** Large readout: the subject interval when the map shows today's terrain for a past topic, else the eased time. */
  let readout = $derived.by(() => {
    if (subject) return rangeText(subject);
    const s = formatAge(locale, uiStrings, { unit, ageValue: value });
    return s === NOW ? cap(s) : s;
  });
  let readoutKey = $derived(subject ? `subject-${activeIndex}` : 'time');

  let paleoLatValue = $derived(view === 'globe' ? paleoLatAt(paleoPath, ageMa) : null);

  /** What the map shows: the view, then the layers that have a phrase in the UI strings. */
  let mapLine = $derived.by(() => {
    if (!active) return '';
    if (active.view === 'globe') return t('rail.map_globe');
    const parts = active.layers.map((l) => uiStrings[`rail.map_layer.${l.id}`]).filter((s): s is string => !!s);
    const unique = [...new Set(parts)];
    return unique.length ? `${t('rail.map_terrain')} · ${unique.join(', ')}` : t('rail.map_terrain');
  });

  const contains = (i: IcsInterval, ma: number) => ma <= i.start_ma && ma >= i.end_ma;
  const overlaps = (i: IcsInterval, s: { start_ma: number; end_ma: number }) => i.start_ma > s.end_ma && i.end_ma < s.start_ma;

  /** Interval name and swatch for the current time or the chapter's subject interval. */
  let current = $derived.by(() => {
    if (subject) {
      const eps = epochs.filter((e) => overlaps(e, subject));
      const pers = periods.filter((p) => overlaps(p, subject));
      const use = eps.length > 0 && eps.length <= 2 ? eps : pers;
      const names = use.length > 2 ? [use[0].name, use[use.length - 1].name] : use.map((u) => u.name);
      return { label: names.map(tr).join(' – '), color: use[0]?.color };
    }
    const p = periods.find((x) => contains(x, ageMa));
    const e = epochs.find((x) => contains(x, ageMa));
    // "Middle Triassic" already names its period: show the epoch alone (decided on the English names)
    const label = p && e ? (e.name.includes(p.name) ? tr(e.name) : `${tr(p.name)} · ${tr(e.name)}`) : tr(p?.name ?? e?.name ?? '');
    return { label, color: e?.color ?? p?.color };
  });

  const viewLabel = (v: string) => t(v === 'globe' ? 'rail.view_globe' : 'rail.view_terrain');
  const chapterLabel = (i: number) => `${i + 1}. ${chapters[i].title} (${rangeText(chapterIv[i])})`;

  let tipIndex = $state<number | null>(null);
  let tip = $derived.by(() => {
    if (tipIndex === null) return null;
    const ch = chapters[tipIndex];
    const m = marks[tipIndex];
    if (!ch || !m) return null;
    return {
      title: `${tipIndex + 1} · ${ch.title}`,
      meta: `${rangeText(chapterIv[tipIndex])} · ${viewLabel(ch.view)}`,
      x: m.cx,
      align: m.cx < 22 ? 'start' : m.cx > 78 ? 'end' : 'mid',
    };
  });
</script>

{#snippet glyph(v: string)}
  {#if v === 'globe'}
    <circle cx="7" cy="7" r="5.6" /><ellipse cx="7" cy="7" rx="2.4" ry="5.6" /><path d="M1.6 7h10.8" />
  {:else}
    <path d="M1 12 5.2 4.5l2.6 4 1.6-2.2L13 12Z" />
  {/if}
{/snippet}

<div class="timerail">
  <div class="rail-head">
    {#key readoutKey}<span class="age">{readout}</span>{/key}
    {#if current.label}
      <span class="period-name" title={ics?.version}>
        {#if current.color}<i class="swatch" style:background={current.color}></i>{/if}
        <span class="period-text">{current.label}</span>
      </span>
    {/if}
    <span class="rail-step">
      <button
        type="button"
        class="step-btn"
        disabled={activeIndex <= 0}
        title={activeIndex > 0 ? chapterLabel(activeIndex - 1) : undefined}
        aria-label={activeIndex > 0 ? `${t('rail.prev')}: ${chapterLabel(activeIndex - 1)}` : t('rail.prev')}
        onclick={() => onJump(activeIndex - 1)}
      ><svg viewBox="0 0 10 10" aria-hidden="true"><path d="M6.5 1.5 3 5l3.5 3.5" /></svg></button>
      <span class="step-count" title={fill(t('rail.chapter_n'), { n: String(activeIndex + 1), total: String(chapters.length) })}
        >{activeIndex + 1} / {chapters.length}</span>
      <button
        type="button"
        class="step-btn"
        disabled={activeIndex >= chapters.length - 1}
        title={activeIndex < chapters.length - 1 ? chapterLabel(activeIndex + 1) : undefined}
        aria-label={activeIndex < chapters.length - 1 ? `${t('rail.next')}: ${chapterLabel(activeIndex + 1)}` : t('rail.next')}
        onclick={() => onJump(activeIndex + 1)}
      ><svg viewBox="0 0 10 10" aria-hidden="true"><path d="M3.5 1.5 7 5 3.5 8.5" /></svg></button>
    </span>
  </div>

  <div class="rail-map">
    <svg class="view-glyph" viewBox="0 0 14 14" aria-hidden="true">{@render glyph(view)}</svg>
    <span class="map-text">{mapLine}</span>
    {#if view === 'globe'}
      <span class="paleolat" title={t('paleolat_model_note', '')}>
        {t('time.paleolat')}: {paleoLatValue === null ? '—' : formatPaleoLat(locale, uiStrings, paleoLatValue)}
      </span>
    {/if}
  </div>

  {#if segs.length}
    <div class="rail-axis" bind:clientWidth={axisW}>
      <div class="rail-band" aria-hidden="true">
        {#each bandSegs as s}
          <span
            class={s.band ? (s.afterBreak ? 'seg band after-break' : 'seg band') : 'seg strip'}
            style:left="{s.left}%"
            style:width="{s.width}%"
            style:background={s.color}
            style:color={s.band ? ink(s.color) : undefined}
            title={tr(s.name)}
          >{s.label}</span>
        {/each}
        {#if subjectBox}
          <i class="rail-subject" style:left="{subjectBox.left}%" style:width="{subjectBox.right - subjectBox.left}%"></i>
        {/if}
        <b class="rail-marker" class:off={!!subject} style:left="{markerX}%"></b>
      </div>
      {#if spec.insetMa > 0}
        <i class="rail-break" style:left="{breakLeft}%" style:width="{spec.gapPct}%"
          title={fill(t('rail.inset'), { ka: nfInt.format(spec.insetMa * 1000) })}></i>
      {/if}

      <nav class="rail-lane" aria-label={t('rail.timeline')} style:height="{laneH}px">
        {#each lane.rows as v, row (v)}
          <svg class="lane-glyph" style:top="{row * ROW_H + 5}px" viewBox="0 0 14 14" aria-hidden="true"><title>{viewLabel(v)}</title>{@render glyph(v)}</svg>
        {/each}
        {#each chapters as ch, i (ch.id)}
          {@const m = marks[i]}
          {#if m}
            {#each m.parts as [l, r]}
              <i class="lane-bracket" class:active={i === activeIndex} class:hot={tipIndex === i}
                style:top="{m.row * ROW_H + 1}px" style:left="{l}%" style:width="{Math.max(0, r - l)}%"></i>
            {/each}
          {/if}
        {/each}
        {#each chapters as ch, i (ch.id)}
          {@const m = marks[i]}
          {#if m}
            <button
              type="button"
              class="lane-btn"
              class:active={i === activeIndex}
              class:next={i === activeIndex + 1}
              class:terrain={ch.view === 'terrain'}
              style:left="{m.cx}%"
              style:top="{m.row * ROW_H + 4}px"
              aria-current={i === activeIndex ? 'step' : undefined}
              aria-label={chapterLabel(i)}
              onclick={() => onJump(i)}
              onpointerenter={() => (tipIndex = i)}
              onpointerleave={() => (tipIndex = null)}
              onfocus={() => (tipIndex = i)}
              onblur={() => (tipIndex = null)}
            >{i + 1}</button>
          {/if}
        {/each}
        {#if tip}
          <div class={`lane-tip ${tip.align}`} style:left="{tip.x}%" style:top="{laneH + 18}px" aria-hidden="true">
            <b>{tip.title}</b><small>{tip.meta}</small>
          </div>
        {/if}
      </nav>

      <div class="rail-ticks" aria-hidden="true">
        {#each ticks as tk}
          <span class={`tick ${tk.align}`} style:left="{tk.x}%">{tk.text}</span>
        {/each}
      </div>
    </div>
  {/if}
  <div class="rail-progress" aria-hidden="true"><i style:transform="scaleX({progress})"></i></div>
</div>
