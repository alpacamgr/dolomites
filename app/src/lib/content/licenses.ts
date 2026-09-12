/**
 * Build-time licence data:
 *  - licence names and URLs from data/manifests/*.yaml (`license.name`, `license.url`), plus the
 *    short Creative Commons form of long names ("CC0 1.0 Universal" -> "CC0 1.0") so credit texts
 *    that use the short form are linked too;
 *  - the curve data files in public/data/curves/, which ship with the site although no page draws
 *    them yet, grouped by dataset with the manifest's licence.
 * Nothing is invented: a licence without a URL in its manifest stays unlinked.
 */
import fs from 'node:fs';
import path from 'node:path';
import YAML from 'yaml';
import { PUBLIC_DATA_DIR, REPO_DIR } from './paths';
import type { LicenseLink } from '@/lib/story/licenseText';

interface ManifestLicense { id: string; name: string; url: string | null }

let manifestCache: ManifestLicense[] | null = null;

function manifestLicenses(): ManifestLicense[] {
  if (manifestCache && !import.meta.env.DEV) return manifestCache;
  const dir = path.join(REPO_DIR, 'data', 'manifests');
  const out: ManifestLicense[] = [];
  if (fs.existsSync(dir)) {
    for (const f of fs.readdirSync(dir).filter((n: string) => n.endsWith('.yaml') && n !== 'TEMPLATE.yaml').sort()) {
      try {
        const doc = YAML.parse(fs.readFileSync(path.join(dir, f), 'utf8')) as { id?: string; license?: { name?: unknown; url?: unknown } };
        const name = typeof doc?.license?.name === 'string' ? doc.license.name.trim() : '';
        const url = typeof doc?.license?.url === 'string' && /^https?:\/\//.test(doc.license.url) ? doc.license.url.trim() : null;
        if (name) out.push({ id: String(doc.id ?? f.replace(/\.yaml$/, '')), name, url });
      } catch {
        /* a malformed manifest is reported by the pipeline tools, not here */
      }
    }
  }
  manifestCache = out;
  return out;
}

/** Licence name -> URL pairs for linking, longest names first. */
export function loadLicenseLinks(): LicenseLink[] {
  const byName = new Map<string, string>();
  for (const m of manifestLicenses()) {
    if (!m.url) continue;
    if (!byName.has(m.name)) byName.set(m.name, m.url);
    const short = m.name.match(/^(CC0 \d\.\d|CC BY(?:-[A-Z]{2})* \d\.\d)/)?.[1];
    if (short && !byName.has(short)) byName.set(short, m.url);
  }
  return [...byName.entries()].map(([name, url]) => ({ name, url })).sort((a, b) => b.name.length - a.name.length);
}

export interface DataFileGroup {
  datasetId: string;
  files: string[];
  attribution: string;
  licenseName: string;
  licenseUrl: string | null;
}

/** Curve files in public/data/curves, grouped by dataset id, with the manifest licence. */
export function loadCurveFiles(): DataFileGroup[] {
  const dir = path.join(PUBLIC_DATA_DIR, 'curves');
  if (!fs.existsSync(dir)) return [];
  const groups = new Map<string, DataFileGroup>();
  const licenses = manifestLicenses();
  for (const f of fs.readdirSync(dir).filter((n: string) => n.endsWith('.json')).sort()) {
    try {
      const doc = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) as { dataset_id?: string; attribution?: string; license?: string };
      const id = doc.dataset_id ?? f.replace(/\.json$/, '');
      const manifest = licenses.find((m) => m.id === id);
      let g = groups.get(id);
      if (!g) {
        g = {
          datasetId: id,
          files: [],
          attribution: doc.attribution ?? id,
          licenseName: manifest?.name ?? doc.license ?? '',
          licenseUrl: manifest?.url ?? null,
        };
        groups.set(id, g);
      }
      g.files.push(`curves/${f}`);
    } catch {
      /* skip unreadable files */
    }
  }
  return [...groups.values()];
}
