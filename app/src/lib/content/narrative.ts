/**
 * Load chapter narrative markdown per locale. The content agent will fill
 * content/narrative/{en,de,it}/<chapter-id>.md; until then this reads
 * whatever exists and returns null for missing ones (the page falls back
 * to the chapter summary).
 *
 * We render markdown ourselves with a tiny, deterministic parser that
 * covers exactly what the editorial style guide allows: headings, paragraphs,
 * bold, italic, links, and citations of the form [@key]. This keeps the
 * shell bundle free of a markdown dependency and keeps citation lookup
 * inside our own control flow.
 */
import fs from 'node:fs';
import path from 'node:path';
import YAML from 'yaml';
import { CONTENT_DIR } from './paths';
import type { Locale } from './schema';

export interface NarrativeDoc {
  chapterId: string;
  locale: Locale;
  frontmatter: Record<string, unknown>;
  /** rendered HTML with [@key] citations turned into superscript anchor tags */
  html: string;
  /** citation keys, in order of first appearance */
  citations: string[];
}

const cache = new Map<string, NarrativeDoc | null>();

function extractFrontmatter(raw: string): { data: Record<string, unknown>; body: string } {
  if (!raw.startsWith('---')) return { data: {}, body: raw };
  const end = raw.indexOf('\n---', 3);
  if (end < 0) return { data: {}, body: raw };
  const fmRaw = raw.slice(3, end).trim();
  const body = raw.slice(end + 4).replace(/^\r?\n/, '');
  let data: Record<string, unknown> = {};
  try {
    const parsed = YAML.parse(fmRaw);
    if (parsed && typeof parsed === 'object') data = parsed as Record<string, unknown>;
  } catch {
    /* leave data empty */
  }
  return { data, body };
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => {
    switch (c) {
      case '&':
        return '&amp;';
      case '<':
        return '&lt;';
      case '>':
        return '&gt;';
      case '"':
        return '&quot;';
      default:
        return '&#39;';
    }
  });
}

function renderInline(line: string, cites: string[]): string {
  // 1. escape HTML first
  let out = escapeHtml(line);
  // 2. citations [@key] -> superscript link (anchor is resolved by the drawer)
  //    also grouped citations [@a; @b] -> one superscript with comma-separated links
  out = out.replace(/\[((?:@[a-z0-9][a-z0-9._-]*\s*;?\s*)+)\]/gi, (_m, group: string) => {
    const links = group.split(';').map((part) => part.trim().replace(/^@/, '')).filter(Boolean).map((key) => {
      if (!cites.includes(key)) cites.push(key);
      const n = cites.indexOf(key) + 1;
      return `<a href="#src-${key}" data-cite="${key}">${n}</a>`;
    });
    return `<sup class="cite">${links.join(',')}</sup>`;
  });
  // 3. links [text](url)
  out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, text, url) => {
    const safeUrl = /^https?:|^\//.test(url) ? url : '#';
    return `<a href="${safeUrl}" rel="noopener">${text}</a>`;
  });
  // 4. bold **x**
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // 5. italic *x* or _x_
  out = out.replace(/(?<!\*)\*([^*\s][^*]*[^*\s]|[^*\s])\*(?!\*)/g, '<em>$1</em>');
  out = out.replace(/(?<!_)_([^_\s][^_]*[^_\s]|[^_\s])_(?!_)/g, '<em>$1</em>');
  return out;
}

function renderMarkdown(body: string): { html: string; citations: string[] } {
  const cites: string[] = [];
  const lines = body.split(/\r?\n/);
  const out: string[] = [];
  let para: string[] = [];
  const flush = () => {
    if (para.length === 0) return;
    out.push(`<p>${renderInline(para.join(' '), cites)}</p>`);
    para = [];
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (line.length === 0) {
      flush();
      continue;
    }
    const h = /^(#{1,4})\s+(.+)$/.exec(line);
    if (h) {
      flush();
      const level = h[1].length + 1; // start at h2 (h1 is the page title)
      out.push(`<h${level}>${renderInline(h[2], cites)}</h${level}>`);
      continue;
    }
    para.push(line);
  }
  flush();
  return { html: out.join('\n'), citations: cites };
}

/** chapter id -> file path per locale, from front matter `chapter` (fallback: file name without NN- prefix) */
const indexCache = new Map<Locale, Map<string, string>>();

function narrativeIndex(locale: Locale): Map<string, string> {
  const cached = indexCache.get(locale);
  if (cached && !import.meta.env.DEV) return cached;
  const map = new Map<string, string>();
  const dir = path.join(CONTENT_DIR, 'narrative', locale);
  if (fs.existsSync(dir)) {
    for (const f of fs.readdirSync(dir).filter((n: string) => n.endsWith('.md')).sort()) {
      const file = path.join(dir, f);
      const { data } = extractFrontmatter(fs.readFileSync(file, 'utf8'));
      const id = typeof data.chapter === 'string' ? data.chapter : f.replace(/\.md$/, '').replace(/^\d+-/, '');
      map.set(id, file);
    }
  }
  indexCache.set(locale, map);
  return map;
}

export function loadNarrative(chapterId: string, locale: Locale): NarrativeDoc | null {
  const key = `${locale}/${chapterId}`;
  if (cache.has(key) && !import.meta.env.DEV) return cache.get(key) ?? null;
  const file = narrativeIndex(locale).get(chapterId);
  if (!file) {
    cache.set(key, null);
    return null;
  }
  const raw = fs.readFileSync(file, 'utf8');
  const { data, body } = extractFrontmatter(raw);
  const { html, citations } = renderMarkdown(body);
  const doc: NarrativeDoc = { chapterId, locale, frontmatter: data, html, citations };
  cache.set(key, doc);
  return doc;
}
