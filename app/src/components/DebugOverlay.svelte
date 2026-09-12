<script lang="ts">
  let { activeIndex, progress, time, timeUnit, engineLoading, view, chapterId }: {
    activeIndex: number;
    progress: number;
    time: number;
    timeUnit: 'ma' | 'ka';
    engineLoading: boolean;
    view: 'globe' | 'terrain';
    chapterId: string;
  } = $props();
</script>

<div class="debug-overlay" aria-hidden="true">
  <dl>
    <dt>chapter</dt><dd>#{activeIndex} {chapterId}</dd>
    <dt>view</dt><dd>{view}</dd>
    <dt>progress</dt><dd>{progress.toFixed(3)}</dd>
    <dt>time</dt><dd>{time.toFixed(2)} {timeUnit}</dd>
    <dt>engine</dt><dd>{engineLoading ? 'loading' : 'idle'}</dd>
  </dl>
</div>
