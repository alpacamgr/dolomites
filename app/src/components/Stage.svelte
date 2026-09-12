<!--
  Stage island: mounts two stacked engine containers and starts the story
  controller. Overlay layout: time rail (with the chapter timeline) top-left,
  legend and geology key bottom-left, data credits bottom-right; the centre stays clear.
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { ClientChapter } from '@/lib/story/types';
  import { startStory, type StoryController } from '@/lib/story/controller';
  import type { GeologyFocus, GeologyKeyData } from '@/lib/story/geologyKey';
  import type { TerrainEngine } from '@/lib/terrain';
  import TimeRail from './TimeRail.svelte';
  import Legend from './Legend.svelte';
  import Credits from './Credits.svelte';
  import DebugOverlay from './DebugOverlay.svelte';
  import type { Locale } from '@/lib/i18n/client';
  import type { IcsChart } from '@/lib/content/ics';
  import type { LicenseLink } from '@/lib/story/licenseText';

  let { chapters, locale, uiStrings, ics, licenses = [], debug: initialDebug = false }: {
    chapters: ClientChapter[];
    locale: Locale;
    uiStrings: Record<string, string>;
    ics: IcsChart | null;
    /** licence names -> URLs from the data manifests, for the credits panel */
    licenses?: LicenseLink[];
    debug?: boolean;
  } = $props();

  // In the static build the query string is not visible at build time, so we
  // also read `?debug=1` from the browser on hydration.
  let debug = $state(initialDebug);

  const t = (k: string, fb?: string) => uiStrings[k] ?? fb ?? k;

  let globeEl: HTMLDivElement;
  let terrainEl: HTMLDivElement;
  let controller: StoryController | null = null;

  let activeIndex = $state(0);
  let progress = $state(0);
  let timeUnit = $state<'ma' | 'ka'>(chapters[0]?.time.unit ?? 'ma');
  let time = $state(chapters[0]?.time.start ?? 0);
  let engineLoading = $state(false);
  let attributions = $state<string[]>([]);
  let reduceMotion = $state(false);
  let geologyKey = $state<GeologyKeyData | null>(null);
  let setGeologyFocus: (focus: GeologyFocus | null) => void = () => {};

  let activeChapter = $derived(chapters[activeIndex]);
  let activeView = $derived<'globe' | 'terrain'>(activeChapter?.view ?? 'globe');

  onMount(() => {
    if (new URLSearchParams(window.location.search).get('debug') === '1') debug = true;
    const narrativeRoot = document.querySelector<HTMLElement>('[data-narrative-root]');
    if (!narrativeRoot) {
      console.error('[stage] narrative root not found');
      return;
    }
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    controller = startStory({
      chapters, narrativeRoot, globeEl, terrainEl, reduceMotion,
      engineOptions: { strings: uiStrings, locale, icsIntervals: ics?.intervals ?? [] },
    });
    const off = controller.subscribe((s) => {
      activeIndex = s.activeIndex;
      progress = s.progress;
      timeUnit = s.timeUnit;
      time = s.time;
      engineLoading = s.engineLoading;
      attributions = s.attributions;
    });
    // The geology key lives in the terrain engine; the stub fallback has none.
    let offKey = () => {};
    const offMounted = controller.getEngineManager().onMounted('terrain', (engine) => {
      const te = engine as Partial<TerrainEngine>;
      if (typeof te.onGeologyKey !== 'function' || typeof te.setGeologyFocus !== 'function') return;
      offKey = te.onGeologyKey((k) => (geologyKey = k));
      setGeologyFocus = (f) => te.setGeologyFocus!(f);
    });
    // debug hook: lets tests drive the controller without real scroll events
    if (debug) (window as unknown as { __story?: StoryController }).__story = controller;
    return () => {
      off();
      offMounted();
      offKey();
    };
  });

  onDestroy(() => {
    controller?.destroy();
    controller = null;
  });

  function jump(index: number) {
    controller?.goToChapter(index);
  }
</script>

<div class="stage">
  <div
    bind:this={globeEl}
    class="engine-slot globe"
    class:active={activeView === 'globe'}
    role="img"
    aria-label={t('alt_globe', 'Globe')}
    aria-hidden={activeView !== 'globe'}
  ></div>
  <div
    bind:this={terrainEl}
    class="engine-slot terrain"
    class:active={activeView === 'terrain'}
    role="img"
    aria-label={t('alt_terrain', 'Terrain')}
    aria-hidden={activeView !== 'terrain'}
  ></div>

  <div class="stage-overlay">
    <div class="overlay-top">
      <TimeRail
        {locale}
        {uiStrings}
        {ics}
        {chapters}
        {activeIndex}
        {progress}
        {reduceMotion}
        unit={timeUnit}
        value={time}
        onJump={jump}
        onStep={(delta) => controller?.step(delta)}
      />
    </div>
    <div class="overlay-bottom">
      <Legend
        chapter={activeChapter}
        {uiStrings}
        {ics}
        {locale}
        {geologyKey}
        loading={engineLoading}
        onGeologyFocus={(f) => setGeologyFocus(f)}
      />
      <Credits {attributions} {uiStrings} {licenses} />
    </div>
  </div>
</div>

{#if debug}
  <DebugOverlay
    {activeIndex}
    {progress}
    {time}
    {timeUnit}
    {engineLoading}
    view={activeView}
    chapterId={activeChapter?.id ?? '?'}
  />
{/if}
