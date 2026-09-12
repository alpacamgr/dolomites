/**
 * fetch + JSON.parse with retries. Pipeline scripts may rewrite data files
 * while the app reads them, so a truncated file (parse error) or a transient
 * HTTP error is retried; a 404 is not.
 */
export async function fetchJson<T>(url: string, attempts = 4): Promise<T> {
  let lastErr: unknown = null;
  for (let i = 0; i < attempts; i++) {
    try {
      const resp = await fetch(url, i > 0 ? { cache: 'reload' } : undefined);
      if (resp.status === 404) return Promise.reject(new Error(`404 ${url}`));
      if (!resp.ok) throw new Error(`HTTP ${resp.status} ${url}`);
      return JSON.parse(await resp.text()) as T;
    } catch (err) {
      lastErr = err;
      await new Promise((r) => setTimeout(r, 300 * (i + 1)));
    }
  }
  throw lastErr;
}
