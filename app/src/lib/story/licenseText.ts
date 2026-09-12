/**
 * Split a credit or reference text into plain parts and licence names linked to their licence
 * URLs. Browser-safe; the name -> URL list is built at build time from data/manifests
 * (lib/content/licenses.ts). Longer names win over shorter ones that they contain.
 */
export interface LicenseLink { name: string; url: string }
export interface TextPart { text: string; url?: string }

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

export function splitLicenses(text: string, links: LicenseLink[]): TextPart[] {
  if (!text || !links.length) return [{ text }];
  const sorted = [...links].sort((a, b) => b.name.length - a.name.length);
  const re = new RegExp(`(${sorted.map((l) => escapeRe(l.name)).join('|')})`, 'g');
  const url = new Map(sorted.map((l) => [l.name, l.url]));
  const out: TextPart[] = [];
  let last = 0;
  for (const m of text.matchAll(re)) {
    const i = m.index ?? 0;
    if (i > last) out.push({ text: text.slice(last, i) });
    out.push({ text: m[0], url: url.get(m[0]) });
    last = i + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}
