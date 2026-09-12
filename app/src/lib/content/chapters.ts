/**
 * Load chapter YAML at build time, validate against the schema, and sort
 * by file name. If `content/timeline/` is empty we fall back to fixtures
 * under `src/lib/content/fixtures/timeline/` and log which source is in
 * use so it is obvious in the terminal.
 */
import fs from 'node:fs';
import path from 'node:path';
import YAML from 'yaml';
import { chapterSchema, type Chapter } from './schema';
import { CONTENT_DIR, FIXTURES_DIR } from './paths';

export interface LoadedChapter extends Chapter {
  /** file basename, used to keep insertion order stable */
  file: string;
  /** true when this came from the fixture folder, not the editorial content */
  fixture: boolean;
}

let cache: LoadedChapter[] | null = null;

function readDir(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f: string) => f.endsWith('.yaml') || f.endsWith('.yml'))
    .sort();
}

function parseFile(dir: string, file: string, fixture: boolean): LoadedChapter {
  const raw = fs.readFileSync(path.join(dir, file), 'utf8');
  const parsed = YAML.parse(raw);
  const validated = chapterSchema.parse(parsed);
  return { ...validated, file, fixture };
}

export function loadChapters(): LoadedChapter[] {
  if (cache && !import.meta.env.DEV) return cache;
  const timelineDir = path.join(CONTENT_DIR, 'timeline');
  const files = readDir(timelineDir);
  if (files.length > 0) {
    // eslint-disable-next-line no-console
    console.log(`[content] loading ${files.length} chapter(s) from content/timeline/`);
    cache = files.map((f) => parseFile(timelineDir, f, false));
    return cache;
  }
  const fxDir = path.join(FIXTURES_DIR, 'timeline');
  const fxFiles = readDir(fxDir);
  // eslint-disable-next-line no-console
  console.warn(
    `[content] content/timeline/ is empty; using ${fxFiles.length} fixture chapter(s) from src/lib/content/fixtures/timeline/`,
  );
  cache = fxFiles.map((f) => parseFile(fxDir, f, true));
  return cache;
}

export function anyFixtureInUse(): boolean {
  return loadChapters().some((c) => c.fixture);
}
