/**
 * Load `content/ui/{locale}.json` at build time and merge over a set of
 * built-in defaults so the shell always has strings to render even before
 * the content agent finishes the UI JSON.
 *
 * Keys are dot paths, deliberately flat to keep the JSON reviewable.
 */
import fs from 'node:fs';
import path from 'node:path';
import { CONTENT_DIR } from './paths';
import { LOCALES, type Locale } from './schema';

type Strings = Record<string, string>;

const DEFAULTS: Record<Locale, Strings> = {
  en: {
    'site.title': 'The Dolomites through deep time',
    'site.tagline': 'A scroll-driven journey from Pangea to today',
    'lang.en': 'English',
    'lang.de': 'Deutsch',
    'lang.it': 'Italiano',
    'nav.chapters': 'Chapters',
    'nav.jumpTo': 'Jump to chapter',
    'nav.sources': 'Sources',
    'nav.legend': 'Legend',
    'time.now': 'Present',
    'time.ma': 'Ma',
    'time.ka': 'ka',
    'time.paleolat': 'Paleolatitude',
    'time.paleolat.unavailable': 'not yet available in globe view',
    'label.observed': 'Observed',
    'label.modeled': 'Modelled',
    'label.interpreted': 'Interpreted',
    'label.illustrative': 'Illustrative',
    'label.observed.desc': 'Measured today from real data.',
    'label.modeled.desc': 'Output of a published numerical model.',
    'label.interpreted.desc': 'Drawn from field evidence in the cited work.',
    'label.illustrative.desc': 'Schematic; makes no claim to spatial accuracy.',
    'facts.verificationPending': 'verification pending',
    'legend.attributions': 'Data attributions',
    'legend.empty': 'No layers declared for this chapter yet.',
    'sources.title': 'Sources for this chapter',
    'sources.empty': 'No sources cited in this chapter yet.',
    'sources.unresolved': 'not yet in the bibliography',
    'engine.loading': 'loading',
    'chapter.fixtureWarning': 'Placeholder content — this chapter has not been written yet.',
    'reduced-motion.note': 'Motion is reduced because your system requests it.',
  },
  de: {
    'site.title': 'Die Dolomiten in tiefer Zeit',
    'site.tagline': 'Eine scrollgesteuerte Reise von Pangaea bis heute',
    'lang.en': 'English',
    'lang.de': 'Deutsch',
    'lang.it': 'Italiano',
    'nav.chapters': 'Kapitel',
    'nav.jumpTo': 'Zum Kapitel springen',
    'nav.sources': 'Quellen',
    'nav.legend': 'Legende',
    'time.now': 'Heute',
    'time.ma': 'Ma',
    'time.ka': 'ka',
    'time.paleolat': 'Paläobreite',
    'time.paleolat.unavailable': 'im Globus noch nicht verfügbar',
    'label.observed': 'Gemessen',
    'label.modeled': 'Modelliert',
    'label.interpreted': 'Interpretiert',
    'label.illustrative': 'Illustrativ',
    'label.observed.desc': 'Heute an realen Daten gemessen.',
    'label.modeled.desc': 'Ergebnis eines veröffentlichten Modells.',
    'label.interpreted.desc': 'Aus Feldbefunden in der zitierten Arbeit abgeleitet.',
    'label.illustrative.desc': 'Schematisch; keine räumliche Genauigkeit.',
    'facts.verificationPending': 'Prüfung ausstehend',
    'legend.attributions': 'Datenquellen',
    'legend.empty': 'Für dieses Kapitel sind noch keine Ebenen deklariert.',
    'sources.title': 'Quellen zu diesem Kapitel',
    'sources.empty': 'In diesem Kapitel sind noch keine Quellen zitiert.',
    'sources.unresolved': 'noch nicht in der Bibliografie',
    'engine.loading': 'lädt',
    'chapter.fixtureWarning': 'Platzhalterinhalt – dieses Kapitel ist noch nicht geschrieben.',
    'reduced-motion.note': 'Bewegung reduziert (Systemeinstellung).',
  },
  it: {
    'site.title': "Le Dolomiti attraverso il tempo profondo",
    'site.tagline': 'Un viaggio guidato dallo scroll, dalla Pangea a oggi',
    'lang.en': 'English',
    'lang.de': 'Deutsch',
    'lang.it': 'Italiano',
    'nav.chapters': 'Capitoli',
    'nav.jumpTo': 'Vai al capitolo',
    'nav.sources': 'Fonti',
    'nav.legend': 'Legenda',
    'time.now': 'Oggi',
    'time.ma': 'Ma',
    'time.ka': 'ka',
    'time.paleolat': 'Paleolatitudine',
    'time.paleolat.unavailable': 'non ancora disponibile nella vista globo',
    'label.observed': 'Osservato',
    'label.modeled': 'Modellato',
    'label.interpreted': 'Interpretato',
    'label.illustrative': 'Illustrativo',
    'label.observed.desc': "Misurato oggi da dati reali.",
    'label.modeled.desc': "Prodotto di un modello numerico pubblicato.",
    'label.interpreted.desc': "Ricavato dalle prove di campagna nel lavoro citato.",
    'label.illustrative.desc': "Schematico; nessuna pretesa di accuratezza spaziale.",
    'facts.verificationPending': 'verifica pendente',
    'legend.attributions': 'Fonti dei dati',
    'legend.empty': 'Nessun livello dichiarato per questo capitolo.',
    'sources.title': 'Fonti di questo capitolo',
    'sources.empty': 'Nessuna fonte citata in questo capitolo.',
    'sources.unresolved': 'non ancora nella bibliografia',
    'engine.loading': 'caricamento',
    'chapter.fixtureWarning': 'Contenuto segnaposto – questo capitolo non è ancora scritto.',
    'reduced-motion.note': "Movimento ridotto (impostazione del sistema).",
  },
};

const cache = new Map<Locale, Strings>();

/**
 * content/ui/*.json is nested (e.g. `labels.observed.explanation`). Flatten it
 * to dot paths, then map the editorial key names onto the shell's key names.
 * Editorial strings win over the built-in defaults. `language.*` is not mapped:
 * the switcher shows endonyms (Deutsch, Italiano), not names in the page language.
 */
const KEY_MAP: Record<string, string> = {
  site_title: 'site.title',
  site_tagline: 'site.tagline',
  legend: 'nav.legend',
  sources: 'nav.sources',
  skip_to_chapter: 'nav.jumpTo',
  paleolatitude: 'time.paleolat',
  unit_today: 'time.now',
  loading: 'engine.loading',
  attribution: 'legend.attributions',
};

function flatten(obj: unknown, prefix = '', out: Strings = {}): Strings {
  if (obj && typeof obj === 'object') {
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      const p = prefix ? `${prefix}.${k}` : k;
      if (typeof v === 'string') out[p] = v;
      else flatten(v, p, out);
    }
  }
  return out;
}

function loadFileOverrides(locale: Locale): Strings {
  const file = path.join(CONTENT_DIR, 'ui', `${locale}.json`);
  if (!fs.existsSync(file)) return {};
  try {
    const flat = flatten(JSON.parse(fs.readFileSync(file, 'utf8')));
    const out: Strings = {};
    for (const [k, v] of Object.entries(flat)) {
      const label = /^labels\.(\w+)\.(title|explanation)$/.exec(k);
      if (label) out[label[2] === 'title' ? `label.${label[1]}` : `label.${label[1]}.desc`] = v;
      else if (KEY_MAP[k]) out[KEY_MAP[k]] = v;
      else if (!k.startsWith('language.')) out[k] = v;
    }
    return out;
  } catch {
    return {};
  }
}

export function loadUi(locale: Locale): Strings {
  const cached = cache.get(locale);
  // dev: re-read so edits to content/ui/*.json show without a server restart
  if (cached && !import.meta.env.DEV) return cached;
  const merged: Strings = { ...DEFAULTS[locale], ...loadFileOverrides(locale) };
  cache.set(locale, merged);
  return merged;
}

export function makeT(locale: Locale) {
  const strings = loadUi(locale);
  return (key: string, fallback?: string): string => strings[key] ?? fallback ?? key;
}

export { LOCALES };
export type { Locale };
