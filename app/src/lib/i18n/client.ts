/**
 * Browser-safe i18n helpers. Contains ONLY code that can ship to the
 * client bundle. Anything that has to read from disk (bibliography, UI
 * JSON overrides) lives in `./index.ts` and is called from Astro pages
 * only.
 */
export const LOCALES = ['en', 'de', 'it'] as const;
export type Locale = (typeof LOCALES)[number];

export function isLocale(v: string | undefined): v is Locale {
  return !!v && (LOCALES as readonly string[]).includes(v);
}

export function pickLocaleFromNavigator(): Locale {
  if (typeof navigator === 'undefined') return 'en';
  const langs = [navigator.language, ...(navigator.languages ?? [])];
  for (const l of langs) {
    const short = (l || '').toLowerCase().slice(0, 2);
    if (isLocale(short)) return short;
  }
  return 'en';
}

export function localePath(locale: Locale, path: string = '/'): string {
  const clean = path.startsWith('/') ? path : `/${path}`;
  return `/${locale}${clean === '/' ? '/' : clean}`;
}

export interface FormatOptions {
  ageValue: number;
  unit: 'ma' | 'ka';
}

/**
 * Human-readable age readout. The caller supplies the UI strings dict
 * (`time.ma`, `time.ka`, `time.now`) so this file stays disk-free.
 */
export function formatAge(
  locale: Locale,
  strings: Record<string, string>,
  opts: FormatOptions,
): string {
  const { ageValue, unit } = opts;
  const nf = new Intl.NumberFormat(locale, {
    minimumFractionDigits: unit === 'ma' ? 1 : 0,
    maximumFractionDigits: unit === 'ma' ? 1 : 0,
  });
  // 0 Ma and anything that would round to "0 ka" read as "today"
  if (unit === 'ma' ? ageValue < 0.0005 : ageValue < 0.5) {
    return strings['time.now'] ?? 'now';
  }
  const label = unit === 'ma' ? strings['time.ma'] ?? 'Ma' : strings['time.ka'] ?? 'ka';
  return `${nf.format(ageValue)} ${label}`;
}

export function formatPaleoLat(
  locale: Locale,
  strings: Record<string, string>,
  lat: number | null,
): string {
  if (lat === null || !Number.isFinite(lat)) {
    return strings['time.paleolat.unavailable'] ?? '—';
  }
  const nf = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  const hemi = lat >= 0 ? 'N' : 'S';
  return `${nf.format(Math.abs(lat))}° ${hemi}`;
}
