<!--
  "Data & credits": the attribution strings reported by the active engine
  (EngineStatus.attributions), collapsed by default so they do not cover the stage.
-->
<script lang="ts">
  let { attributions = [], uiStrings }: {
    attributions?: string[];
    uiStrings: Record<string, string>;
  } = $props();

  const t = (k: string, fb?: string) => uiStrings[k] ?? fb ?? k;
</script>

{#if attributions.length}
  <details class="credits">
    <summary>{t('credits_title', 'Data & credits')}</summary>
    <div class="credits-body">
      <ul>
        {#each attributions as a (a)}<li>{a}</li>{/each}
      </ul>
    </div>
  </details>
{/if}
