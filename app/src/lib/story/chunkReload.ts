/**
 * After a deploy an open tab still references the previous build's hashed chunks, which then 404.
 * A dynamic import that fails for that reason reloads the page once, so the reader gets the new
 * build instead of a placeholder stage. A sessionStorage timestamp prevents reload loops: at most
 * one reload per two minutes, and none at all when sessionStorage is unavailable. Any other error
 * is rethrown for the caller's own fallback.
 */
const KEY = 'dolomites:chunk-reload';
const WINDOW_MS = 120_000;
const CHUNK_ERROR = /dynamically imported module|Importing a module script failed|error loading dynamically imported module|Failed to fetch|Unable to preload/i;

export async function importWithReload<T>(load: () => Promise<T>): Promise<T> {
  try {
    return await load();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (CHUNK_ERROR.test(message) && typeof window !== 'undefined') {
      let allowed = false;
      try {
        const last = Number(window.sessionStorage.getItem(KEY) ?? 0);
        if (Date.now() - last > WINDOW_MS) {
          window.sessionStorage.setItem(KEY, String(Date.now()));
          allowed = true;
        }
      } catch {
        allowed = false;
      }
      if (allowed) {
        console.warn('[stage] a code chunk from an older build is missing; reloading once');
        window.location.reload();
        return new Promise<T>(() => { /* the page is reloading */ });
      }
    }
    throw err;
  }
}
