/**
 * Paleogeography texture store: prioritised loading, GPU upload pacing and an
 * LRU of GPU textures.
 *
 *  - Load: fetch + createImageBitmap (decode off the main thread, flipped
 *    there because WebGL ignores flipY for ImageBitmap), at most 2 at a time,
 *    in the priority order given by setWanted(). Requests that fall out of the
 *    wanted list are aborted while still downloading.
 *  - Upload: decoded textures wait in a queue; the engine uploads one per
 *    animation frame (renderer.initTexture) so uploads never pile into the
 *    frame that swaps the crossfade pair.
 *  - LRU: at most `colorCapacity` colour textures (6 at 4k, 10 at 2k) and 4
 *    normal maps. Textures the engine currently displays are protected.
 *  - Normal maps are decoded at 2048x1024 whatever the colour size: they only
 *    shade the surface (the colour texture already carries hillshade) and this
 *    keeps them to ~15 MB of GPU memory each instead of ~45 MB.
 */
import * as THREE from 'three';

export interface TexturesIndex {
  ages_ma: number[];
  sizes: Record<string, [number, number]>;
  path_pattern: string;
  normal_path_pattern?: string;
}

export type TexKind = 'color' | 'normal';
export interface TexRequest { kind: TexKind; age: number }

type State = 'loading' | 'decoded' | 'ready' | 'error';
interface Entry {
  key: number;
  kind: TexKind;
  age: number;
  size: string;
  state: State;
  tex: THREE.Texture | null;
  lastUsed: number;
  abort: AbortController | null;
  attempts: number;
  retryAt: number;
}

const MAX_ACTIVE = 2;
const MAX_ATTEMPTS = 3;
const NORMAL_CAPACITY = 4;

export interface TextureStoreOptions {
  globeBase: string;
  index: TexturesIndex;
  size: string;
  colorCapacity: number;
  anisotropy: number;
  /** a decoded texture waits for upload: the engine should schedule a frame */
  onDecoded: () => void;
  /** a texture became usable, or failed for good */
  onSettled: () => void;
}

export class TextureStore {
  private readonly entries = new Map<number, Entry>();
  private wanted: TexRequest[] = [];
  private readonly uploadQueue: Entry[] = [];
  private protectedTex = new Set<THREE.Texture>();
  private active = 0;
  private clock = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private disposed = false;
  lastUploadMs = 0;
  maxUploadMs = 0;
  uploads = 0;

  constructor(private readonly o: TextureStoreOptions) {}

  hasNormals(): boolean { return !!this.o.index.normal_path_pattern; }

  setSize(size: string, colorCapacity: number) {
    this.o.size = size;
    this.o.colorCapacity = colorCapacity;
  }

  /** Ready texture or null. Marks it recently used. */
  get(kind: TexKind, age: number): THREE.Texture | null {
    const e = this.entries.get(this.key(kind, age));
    if (!e || e.state !== 'ready') return null;
    e.lastUsed = ++this.clock;
    return e.tex;
  }

  /** True when this texture failed permanently (so nobody should wait for it). */
  failed(kind: TexKind, age: number): boolean {
    if (kind === 'normal' && !this.hasNormals()) return true;
    const e = this.entries.get(this.key(kind, age));
    return !!e && e.state === 'error' && e.attempts >= MAX_ATTEMPTS;
  }

  pendingUploads(): number { return this.uploadQueue.length; }

  /** Priority-ordered list of what the engine wants now. */
  setWanted(list: TexRequest[]) {
    this.wanted = list;
    const keys = new Set(list.map((r) => this.key(r.kind, r.age)));
    for (const e of this.entries.values()) {
      if (e.state === 'loading' && e.abort && !keys.has(e.key)) e.abort.abort();
      else if (keys.has(e.key)) e.lastUsed = ++this.clock;
    }
    this.pump();
    this.evict();
  }

  /** Textures bound to the globe material; never evicted. */
  protect(textures: THREE.Texture[]) {
    this.protectedTex = new Set(textures);
  }

  /** Upload one decoded texture. Returns true if one was uploaded. */
  uploadOne(renderer: THREE.WebGLRenderer): boolean {
    const e = this.uploadQueue.shift();
    if (!e || !e.tex) return false;
    const t0 = performance.now();
    renderer.initTexture(e.tex);
    this.lastUploadMs = performance.now() - t0;
    this.maxUploadMs = Math.max(this.maxUploadMs, this.lastUploadMs);
    this.uploads++;
    // The GPU has the pixels now; free the decoded bitmap (tens of MB at 4k).
    const img = e.tex.image as ImageBitmap | undefined;
    if (img && typeof img.close === 'function') img.close();
    e.state = 'ready';
    e.lastUsed = ++this.clock;
    this.evict();
    this.o.onSettled();
    return true;
  }

  /** Free every texture that is not currently displayed (pause()). */
  releaseUnprotected() {
    for (const e of Array.from(this.entries.values())) {
      if (e.tex && this.protectedTex.has(e.tex)) continue;
      this.drop(e);
    }
  }

  dispose() {
    this.disposed = true;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    for (const e of Array.from(this.entries.values())) this.drop(e);
    this.protectedTex.clear();
  }

  /** Numeric keys: lookups during scrubbing allocate no strings. */
  private key(kind: TexKind, age: number): number {
    return kind === 'normal' ? 2_000_000 + age : (this.o.size === '4k' ? 0 : 1_000_000) + age;
  }

  private pump() {
    if (this.disposed) return;
    const now = performance.now();
    for (const r of this.wanted) {
      if (this.active >= MAX_ACTIVE) break;
      if (r.kind === 'normal' && !this.hasNormals()) continue;
      const e = this.entries.get(this.key(r.kind, r.age));
      if (e && (e.state !== 'error' || e.attempts >= MAX_ATTEMPTS || now < e.retryAt)) continue;
      this.start(r, e);
    }
  }

  private start(r: TexRequest, prev: Entry | undefined) {
    const e: Entry = prev ?? {
      key: this.key(r.kind, r.age), kind: r.kind, age: r.age, size: this.o.size,
      state: 'loading', tex: null, lastUsed: ++this.clock, abort: null, attempts: 0, retryAt: 0,
    };
    e.state = 'loading';
    e.abort = new AbortController();
    this.entries.set(e.key, e);
    this.active++;
    this.load(e)
      .then((tex) => {
        if (this.disposed || this.entries.get(e.key) !== e) { disposeTexture(tex); return; }
        e.tex = tex;
        e.state = 'decoded';
        e.abort = null;
        this.uploadQueue.push(e);
        this.o.onDecoded();
      })
      .catch((err: unknown) => {
        if (this.entries.get(e.key) !== e) return;
        e.abort = null;
        if (err instanceof DOMException && err.name === 'AbortError') { this.entries.delete(e.key); return; }
        e.state = 'error';
        e.attempts++;
        e.retryAt = performance.now() + 700 * e.attempts;
        if (e.attempts >= MAX_ATTEMPTS) {
          if (e.kind === 'color') console.warn(`[globe] texture ${e.key} failed:`, err);
          this.o.onSettled();
        } else if (!this.retryTimer) {
          this.retryTimer = setTimeout(() => { this.retryTimer = null; this.pump(); }, 750 * e.attempts);
        }
      })
      .finally(() => {
        this.active--;
        this.pump();
      });
  }

  private async load(e: Entry): Promise<THREE.Texture> {
    const pattern = e.kind === 'normal' ? this.o.index.normal_path_pattern ?? '' : this.o.index.path_pattern;
    // Contract paths are relative to /data ("globe/textures/..."); the sample set may omit "globe/".
    const rel = pattern.replace('{size}', e.size).replace('{age}', String(e.age)).replace(/^globe\//, '');
    const url = `${this.o.globeBase}/${rel}`;
    const resp = await fetch(url, { signal: e.abort?.signal, cache: e.attempts > 0 ? 'reload' : 'default' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status} ${url}`);
    const blob = await resp.blob();
    const opts: ImageBitmapOptions = { imageOrientation: 'flipY', premultiplyAlpha: 'none', colorSpaceConversion: 'none' };
    if (e.kind === 'normal') {
      opts.resizeWidth = 2048;
      opts.resizeHeight = 1024;
      opts.resizeQuality = 'high';
    }
    const bitmap = await createImageBitmap(blob, opts);
    const tex = new THREE.Texture(bitmap);
    tex.colorSpace = e.kind === 'color' ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    tex.flipY = false; // already flipped by createImageBitmap
    tex.wrapS = THREE.RepeatWrapping; // continuous across the antimeridian
    tex.wrapT = THREE.ClampToEdgeWrapping;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.magFilter = THREE.LinearFilter;
    tex.generateMipmaps = true;
    tex.anisotropy = this.o.anisotropy;
    tex.needsUpdate = true;
    return tex;
  }

  private evict() {
    this.evictKind('color', this.o.colorCapacity);
    this.evictKind('normal', NORMAL_CAPACITY);
  }

  private evictKind(kind: TexKind, capacity: number) {
    const held: Entry[] = [];
    for (const e of this.entries.values()) {
      if (e.kind === kind && (e.state === 'ready' || e.state === 'decoded')) held.push(e);
    }
    let excess = held.length - capacity;
    if (excess <= 0) return;
    const wantedKeys = new Set(this.wanted.map((r) => this.key(r.kind, r.age)));
    held.sort((a, b) => a.lastUsed - b.lastUsed);
    // First pass: anything neither displayed nor wanted; second pass: wanted but not displayed.
    for (const pass of [0, 1]) {
      for (const e of held) {
        if (excess <= 0) return;
        if (!this.entries.has(e.key) || (e.tex && this.protectedTex.has(e.tex))) continue;
        if (pass === 0 && wantedKeys.has(e.key)) continue;
        this.drop(e);
        excess--;
      }
    }
  }

  private drop(e: Entry) {
    e.abort?.abort();
    if (e.tex) disposeTexture(e.tex);
    e.tex = null;
    const qi = this.uploadQueue.indexOf(e);
    if (qi >= 0) this.uploadQueue.splice(qi, 1);
    this.entries.delete(e.key);
  }
}

function disposeTexture(tex: THREE.Texture) {
  const img = tex.image as ImageBitmap | undefined;
  tex.dispose();
  if (img && typeof img.close === 'function') img.close();
}
