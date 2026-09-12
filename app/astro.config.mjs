// @ts-check
import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';

/** Engine test benches under src/pages/en/dev/ and the labelled stand-in data they can use
 *  (public/data/_sample/) are for development only: drop both from the static output. */
const stripDevPages = {
  name: 'strip-dev-pages',
  hooks: {
    'astro:build:done': async ({ dir }) => {
      const { rm } = await import('node:fs/promises');
      await rm(new URL('en/dev/', dir), { recursive: true, force: true });
      await rm(new URL('data/_sample/', dir), { recursive: true, force: true });
    },
  },
};

export default defineConfig({
  output: 'static',
  devToolbar: { enabled: false },
  integrations: [svelte(), stripDevPages],
  i18n: {
    defaultLocale: 'en',
    locales: ['de', 'it', 'en'],
    routing: { prefixDefaultLocale: true },
  },
  vite: {
    build: { target: 'es2022' },
    // Data files are served as static assets and never need a reload. Watching them makes Windows
    // hold directory handles, which blocks the pipeline's atomic folder renames (export_tiles.py).
    // Consequence: files added under public/data while the dev server runs are only served after a restart.
    server: { watch: { ignored: ['**/public/data/**'] } },
  },
});
