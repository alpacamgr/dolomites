<!--
  "Data & credits": the attribution strings reported by the active engine
  (EngineStatus.attributions), collapsed by default so they do not cover the stage.
  Licence names inside the texts link to their licence URLs (from the data manifests).
-->
<script lang="ts">
  import { splitLicenses, type LicenseLink } from '@/lib/story/licenseText';

  let { attributions = [], uiStrings, licenses = [] }: {
    attributions?: string[];
    uiStrings: Record<string, string>;
    licenses?: LicenseLink[];
  } = $props();

  const t = (k: string, fb?: string) => uiStrings[k] ?? fb ?? k;
</script>

{#if attributions.length}
  <details class="credits">
    <summary>{t('credits_title', 'Data & credits')}</summary>
    <div class="credits-body">
      <ul>
        {#each attributions as a (a)}
          <li>{#each splitLicenses(a, licenses) as part}{#if part.url}<a href={part.url} rel="license noopener" target="_blank">{part.text}</a>{:else}{part.text}{/if}{/each}</li>
        {/each}
      </ul>
    </div>
  </details>
{/if}
