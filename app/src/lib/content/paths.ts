/**
 * Resolve project directories from this module's location.
 * We do not rely on process.cwd() because Astro may run from anywhere.
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const APP_DIR = path.resolve(HERE, '..', '..', '..');
export const REPO_DIR = path.resolve(APP_DIR, '..');
export const CONTENT_DIR = path.resolve(REPO_DIR, 'content');
export const RESEARCH_DIR = path.resolve(REPO_DIR, 'research');
export const PUBLIC_DATA_DIR = path.resolve(APP_DIR, 'public', 'data');
export const FIXTURES_DIR = path.resolve(HERE, 'fixtures');
