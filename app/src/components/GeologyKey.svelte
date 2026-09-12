<!--
  Geology colour key: ICS rows for the unit colours the terrain engine reports in view,
  plus explicit swatches for undated units and for areas without an open geological map.
  Period rows sit in two columns; long rows span both. Pointing at, focusing or tapping a
  row highlights its units on the map (through the terrain engine, never MapLibre
  directly). Grouping: lib/story/geologyKey.ts.
-->
<script lang="ts">
  import type { IcsChart } from '@/lib/content/ics';
  import { groupGeologyKey, intervalName, type GeologyFocus, type GeologyKeyData } from '@/lib/story/geologyKey';

  let { data, ics, uiStrings, locale, emphasis, chapterId, onFocus }: {
    data: GeologyKeyData;
    ics: IcsChart | null;
    uiStrings: Record<string, string>;
    locale: string;
    /** the chapter's emphasis interval (Ma, older first) */
    emphasis?: { start_ma: number; end_ma: number };
    /** the active chapter; a hover or pin never survives a chapter change */
    chapterId?: string;
    onFocus: (focus: GeologyFocus | null) => void;
  } = $props();

  const t = (k: string, fb?: string) => uiStrings[k] ?? fb ?? k;
  const tr = (name: string) => uiStrings[`ics_names.${name}`] ?? name;
  const fill = (s: string, v: Record<string, string>) => s.replace(/\{(\w+)\}/g, (_, k) => v[k] ?? '');
  const nf = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });

  let rows = $derived(groupGeologyKey(ics, data.units, tr, t, locale));
  let periodRows = $derived(rows.filter((r) => r.id.startsWith('period:')));
  let otherRows = $derived(rows.filter((r) => !r.id.startsWith('period:')));
  let emphasisLabel = $derived.by(() => {
    if (!emphasis) return '';
    const range = `${nf.format(emphasis.start_ma)}–${nf.format(emphasis.end_ma)} ${t('time.ma', 'Ma')}`;
    const name = intervalName(ics, emphasis.start_ma, emphasis.end_ma, tr);
    return name ? `${fill(t('geology_key.emphasis'), { name })} (${range})` : fill(t('geology_key.emphasis'), { name: range });
  });
  let coarseNote = $derived.by(() => {
    if (!data.coarse.length) return '';
    const list = data.coarse.map((c) => `${c.name} ${c.scale}`).join('; ');
    return fill(t(data.coarse.length > 1 ? 'geology_key.coarse_many' : 'geology_key.coarse_one'), { list });
  });

  let undatedLabel = $derived(data.withheld
    ? t(data.undated ? 'geology_key.undated_withheld' : 'geology_key.withheld')
    : t('geology_key.undated'));

  let hovered = $state<string | null>(null);
  let pinned = $state<string | null>(null);
  /** row that drives the map: hover, else a tapped row, else the chapter emphasis */
  let focusId = $derived(hovered ?? pinned ?? (emphasis ? 'emphasis' : null));

  function focusFor(id: string): GeologyFocus | null {
    if (id === 'emphasis') return emphasis ? { within: emphasis } : null;
    if (id === 'undated') return { undated: true };
    const row = rows.find((r) => r.id === id);
    return row ? { keys: row.keys } : null;
  }
  function sync() {
    const id = hovered ?? pinned;
    onFocus(id ? focusFor(id) : null);
  }
  const enter = (id: string) => { hovered = id; sync(); };
  const leave = (id: string) => { if (hovered === id) { hovered = null; sync(); } };
  const toggle = (id: string) => { pinned = pinned === id ? null : id; sync(); };

  // a new chapter drops a stale hover or pin (the key data refreshes while hovering, so rows do not reset it)
  $effect(() => {
    void chapterId;
    void emphasis;
    return () => {
      if (hovered || pinned) { hovered = null; pinned = null; onFocus(null); }
    };
  });
</script>

<div class="gkey" role="group" aria-labelledby="gkey-title">
  <p class="gkey-title" id="gkey-title">{t('geology_key.title')}</p>
  {#if emphasis}
    <ul class="gkey-list">{@render row('emphasis', emphasisLabel, 'emph', [])}</ul>
  {/if}
  {#if periodRows.length}
    <ul class="gkey-list grid">
      {#each periodRows as r (r.id)}{@render row(r.id, r.label, 'strip', r.colors)}{/each}
    </ul>
  {/if}
  <ul class="gkey-list">
    {#each otherRows as r (r.id)}{@render row(r.id, r.label, 'strip', r.colors)}{/each}
    {#if data.undated || data.withheld}{@render row('undated', undatedLabel, 'undated', [])}{/if}
    <li>
      <span class="gkey-row static">
        {#if data.gapsLayer}
          <span class="gkey-swatch gap" aria-hidden="true"></span><span class="gkey-label">{t('geology_key.gap')}</span>
        {:else}
          <span class="gkey-swatch edge" aria-hidden="true"></span><span class="gkey-label">{t('geology_key.edge')}</span>
        {/if}
      </span>
    </li>
  </ul>
  {#if rows.length === 0 && !data.undated && !data.withheld}
    <p class="gkey-note">{t('geology_key.none')}</p>
  {/if}
  {#if coarseNote}<p class="gkey-note coarse">{coarseNote}</p>{/if}
  <p class="gkey-note">{t('geology_key.shades')} <span class="gkey-hint">{t('geology_key.hint')}</span></p>
</div>

{#snippet row(id: string, label: string, kind: 'strip' | 'emph' | 'undated', colors: string[])}
  <li>
    <button
      type="button"
      class="gkey-row"
      data-row={id}
      title={label}
      class:dim={focusId !== null && focusId !== id}
      aria-pressed={pinned === id}
      onpointerenter={(e) => { if (e.pointerType === 'mouse') enter(id); }}
      onpointerleave={() => leave(id)}
      onfocus={() => enter(id)}
      onblur={() => leave(id)}
      onclick={() => toggle(id)}
    >
      {#if kind === 'strip'}
        <span class="gkey-swatch" aria-hidden="true">{#each colors as c (c)}<i style:background={c}></i>{/each}</span>
      {:else}
        <span class={`gkey-swatch ${kind}`} aria-hidden="true"><i></i></span>
      {/if}
      <span class="gkey-label">{label}</span>
    </button>
  </li>
{/snippet}
