/**
 * Worker: fetch + parse + convert one plates/{age}.json off the main thread.
 * Replies with transferable Float32Arrays (see plates-geometry.ts).
 */
import { buildPlateBuffers, PLATE_KINDS } from './plates-geometry';

export interface PlatesRequest { id: number; url: string; radius: number; reload: boolean }
export type PlatesResponse =
  | { id: number; ok: true; segments: Record<string, Float32Array> }
  | { id: number; ok: false; error: string };

const scope = self as unknown as {
  onmessage: ((e: MessageEvent<PlatesRequest>) => void) | null;
  postMessage(msg: PlatesResponse, transfer: Transferable[]): void;
};

scope.onmessage = async (e) => {
  const { id, url, radius, reload } = e.data;
  try {
    const resp = await fetch(url, reload ? { cache: 'reload' } : undefined);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    // A file that is being rewritten by the pipeline can be truncated; the
    // JSON.parse error is reported and the main thread retries.
    const data = JSON.parse(await resp.text());
    const { segments } = buildPlateBuffers(data, radius);
    scope.postMessage({ id, ok: true, segments }, PLATE_KINDS.map((k) => segments[k].buffer));
  } catch (err) {
    scope.postMessage({ id, ok: false, error: String(err) }, []);
  }
};
