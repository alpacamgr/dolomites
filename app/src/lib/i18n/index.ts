/**
 * Server-side entry point for i18n. This module reads from disk to merge
 * UI JSON overrides on top of built-in defaults, and MUST NOT be imported
 * from Svelte island code — use `./client.ts` for browser-safe helpers.
 * Astro pages call this, then pass the resolved strings dict to islands.
 */
export {
  LOCALES,
  isLocale,
  pickLocaleFromNavigator,
  localePath,
  formatAge,
  formatPaleoLat,
  type Locale,
  type FormatOptions,
} from './client';

export { loadUi, makeT } from '../content/ui-strings';
