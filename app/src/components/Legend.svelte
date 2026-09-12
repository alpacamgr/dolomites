<script lang="ts">
  import { onMount } from 'svelte';
  import type { ClientChapter } from '@/lib/story/types';
  import type { IcsChart } from '@/lib/content/ics';
  import type { GeologyFocus, GeologyKeyData } from '@/lib/story/geologyKey';
  import { importWithReload } from '@/lib/story/chunkReload';

  // The key only appears once the terrain engine reports geology, so it stays out of the initial bundle.
  let keyModule: Promise<typeof import('./GeologyKey.svelte').default> | null = null;
  const loadGeologyKey = () => (keyModule ??= importWithReload(() => import('./GeologyKey.svelte')).then((m) => m.default));

  let { chapter, uiStrings, loading, ics, locale, geologyKey, onGeologyFocus }: {
    chapter: ClientChapter | undefined;
    uiStrings: Record<string, string>;
    loading: boolean;
    ics: IcsChart | null;
    locale: string;
    /** reported by the terrain engine while a geology layer is visible */
    geologyKey: GeologyKeyData | null;
    onGeologyFocus: (focus: GeologyFocus | null) => void;
  } = $props();

  const t = (k: string, fb?: string) => uiStrings[k] ?? fb ?? k;
  const fill = (s: string, v: Record<string, string>) => s.replace(/\{(\w+)\}/g, (_, k) => v[k] ?? '');

  let open = $state(true);
  onMount(() => {
    // on small screens the stage is only 55vh tall: start collapsed
    if (window.matchMedia('(max-width: 900px)').matches) open = false;
  });

  let layers = $derived(chapter?.layers ?? []);
  let showKey = $derived(chapter?.view === 'terrain' && !!geologyKey);

  const layerName = (id: string) => t(`layers.${id}`, id);
  /** "Elevation (TINITALY 10 m, ...)" -> "Elevation": the one-line summary keeps the badge and the short name */
  const shortName = (id: string) => layerName(id).split(' (')[0];
  type Layer = ClientChapter['layers'][number];
  /** every source of a layer, as short cites */
  const citeList = (l: Layer) => (l.cites ?? [l.cite ?? String(l.source_ref)]).join('; ');
  /** compact cite for merged layers: "6 sources", linking to the Sources section */
  const manyLabel = (l: Layer) => fill(t('layer_cite_many', '{n} sources'), { n: String(l.cites?.length ?? 0) });
  const badgeTip = (l: Layer) => `${layerName(l.id)} (${citeList(l)}). ${t(`label.${l.label}.desc`)}`;
</script>

<section class="legend" class:collapsed={!open} class:with-key={showKey} aria-label={t('nav.legend')}>
  <button type="button" class="legend-toggle" aria-expanded={open} onclick={() => (open = !open)}>
    <span>{t('nav.legend')}</span>
    {#if loading}<span class="loading-dot" title={t('engine.loading')}></span>{/if}
    <span class="chev" aria-hidden="true"></span>
  </button>
  {#if open}
    <div class="legend-body">
      {#if layers.length === 0}
        <p class="legend-empty">{t('legend.empty')}</p>
      {:else if showKey}
        <!-- compact while the rock-age key is open: honesty badge and short name per layer; full name and citation on the badge -->
        <ul class="legend-summary">
          {#each layers as layer (layer.id)}
            <li>
              <button
                type="button"
                class={`badge ${layer.label}`}
                data-tip={badgeTip(layer)}
                aria-label={`${t(`label.${layer.label}`)}: ${badgeTip(layer)}`}
              >{t(`label.${layer.label}`)}</button>
              <span class="summary-name">{shortName(layer.id)}</span>
            </li>
          {/each}
        </ul>
      {:else}
        <ul class="legend-layers">
          {#each layers as layer (layer.id)}
            <li>
              <button
                type="button"
                class={`badge ${layer.label}`}
                data-tip={t(`label.${layer.label}.desc`)}
                aria-label={`${t(`label.${layer.label}`)}: ${t(`label.${layer.label}.desc`)}`}
              >{t(`label.${layer.label}`)}</button>
              <span class="layer-text">
                <span class="layer-name">{layerName(layer.id)}</span>
                {#if layer.cites}
                  <a class="layer-cite" href="#sources" title={citeList(layer)} aria-label={`${manyLabel(layer)}: ${citeList(layer)}`}>{manyLabel(layer)}</a>
                {:else}
                  <a class="layer-cite" href={`#src-${layer.source_ref}`}>{layer.cite ?? layer.source_ref}</a>
                {/if}
              </span>
            </li>
          {/each}
        </ul>
      {/if}
      {#if showKey && geologyKey}
        {#await loadGeologyKey() then GeologyKey}
          <GeologyKey data={geologyKey} {ics} {uiStrings} {locale} emphasis={chapter?.emphasis} chapterId={chapter?.id} onFocus={onGeologyFocus} />
        {/await}
      {/if}
    </div>
  {/if}
</section>
