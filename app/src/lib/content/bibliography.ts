/**
 * Parse research/sources/bibliography.md into a keyed lookup at build time.
 * The file is a markdown table:
 *   | Key | Reference | URL / DOI | Accessed | Open access | Verification |
 * Rows with an empty or `(to be filled ...)` key are skipped.
 */
import fs from 'node:fs';
import path from 'node:path';
import { RESEARCH_DIR } from './paths';

export interface BibEntry {
  key: string;
  reference: string;
  url: string;
  accessed: string;
  openAccess: string;
  verification: string;
  /** explicit short citation for institutional references (bibliography 'Short cite' column) */
  short: string;
}

let cache: Map<string, BibEntry> | null = null;

function stripCell(s: string): string {
  return s.trim().replace(/^\|/, '').replace(/\|$/, '').trim();
}

export function loadBibliography(): Map<string, BibEntry> {
  if (cache && !import.meta.env.DEV) return cache;
  cache = new Map();
  const file = path.join(RESEARCH_DIR, 'sources', 'bibliography.md');
  if (!fs.existsSync(file)) return cache;
  const text = fs.readFileSync(file, 'utf8');
  const lines = text.split(/\r?\n/);
  for (const raw of lines) {
    const line = raw.trim();
    if (!line.startsWith('|') || line.startsWith('|---')) continue;
    const cells = line.split('|').slice(1, -1).map((c: string) => c.trim());
    if (cells.length < 2) continue;
    const key = stripCell(cells[0]);
    if (!key || key.toLowerCase() === 'key' || key.startsWith('(')) continue;
    cache.set(key, {
      key,
      reference: cells[1] ?? '',
      url: cells[2] ?? '',
      accessed: cells[3] ?? '',
      openAccess: cells[4] ?? '',
      verification: cells[5] ?? '',
      short: stripCell(cells[6] ?? ''),
    });
  }
  return cache;
}

export function bibEntry(key: string): BibEntry | null {
  return loadBibliography().get(key) ?? null;
}

/**
 * Short author-year citation ("Tarquini et al. 2023", "Scotese & Wright 2018",
 * "RGI Consortium 2023") parsed from the reference cell, which starts with
 * "Surname I., Surname I. YYYY. Title". Authors are never invented: when the
 * cell does not match that shape (institutional pages, portals, undated
 * charts) the bibliography key itself is returned and logged once at build.
 */
const shortCache = new Map<string, string>();
const fallbacks = new Set<string>();

function surnames(block: string): string[] | null {
  if (/\d/.test(block)) return null;
  const pieces = block.includes('.')
    ? block.replace(/\.$/, '').split(/\.,\s+/)
    : block.split(/,\s+/);
  const names: string[] = [];
  for (const piece of pieces) {
    const name = piece.trim().replace(/(\s+(?:\p{Lu}\.?-?)+)+\.?$/u, '').trim();
    if (!/^\p{Lu}[\p{L}'’ -]*$/u.test(name) || name.length > 40) return null;
    names.push(name);
  }
  return names.length ? names : null;
}

export function shortCite(key: string): string {
  const cached = shortCache.get(key);
  if (cached && !import.meta.env.DEV) return cached;
  const explicit = bibEntry(key)?.short;
  if (explicit) { shortCache.set(key, explicit); return explicit; }
  const ref = bibEntry(key)?.reference ?? '';
  const m = /^(.+?)\s(\d{4})\.\s/u.exec(ref);
  const names = m ? surnames(m[1]) : null;
  let out: string;
  if (m && names) {
    const year = m[2];
    out = names.length === 1 ? `${names[0]} ${year}`
      : names.length === 2 ? `${names[0]} & ${names[1]} ${year}`
      : `${names[0]} et al. ${year}`;
  } else {
    out = key;
    if (!fallbacks.has(key)) {
      fallbacks.add(key);
      // eslint-disable-next-line no-console
      console.warn(`[bibliography] no author-year in reference for "${key}"; showing the key`);
    }
  }
  shortCache.set(key, out);
  return out;
}

/** Reference text without markdown emphasis, for link tooltips. */
export function plainReference(key: string): string | null {
  const ref = bibEntry(key)?.reference;
  return ref ? ref.replace(/\*/g, '') : null;
}
