/**
 * Orbit controls for a unit globe: drag to rotate (with inertia), wheel and
 * pinch to zoom, eased programmatic moves, and a lock for the story controller.
 * Time-based damping, so behaviour does not depend on the frame rate.
 *
 * Zoom limits. Default 1.6..4.0 Earth radii (brief). Resolution check for a
 * 4k texture (4096 px / 360 deg = 11.4 px/deg, one texel = 0.088 deg at the
 * equator) on a 1440 px tall viewport with the 45 deg vertical fov used here:
 * one screen pixel spans 45/1440 = 0.031 deg of view angle, which at the
 * sub-camera point covers (distance - 1) * 0.031 deg of great-circle arc.
 *   distance 4.0 -> 0.094 deg/px -> 0.94 screen px per texel
 *   distance 2.4 -> 0.044 deg/px -> 2.0 screen px per texel (ADR 0004 limit)
 *   distance 1.6 -> 0.019 deg/px -> 4.7 screen px per texel (soft, not blocky)
 * So the brief's 1.6 minimum magnifies the 4k texture ~4.7x at the centre of a
 * 1440 px viewport; ADR 0004's "no more than two screen pixels per texel"
 * holds from about 2.4 R. The engine raises minDistance per viewport height and
 * texture size (applyDistanceLimits in index.ts) so that rule always holds.
 */
import type { PerspectiveCamera } from 'three';
import { lonLatToVec3 } from './geo';

export interface GlobeView { lat: number; lon: number; distance: number }

export interface ControlsOptions {
  minDistance: number;
  maxDistance: number;
  fovDeg: number;
}

const INERTIA_MS = 240;  // velocity e-folding time after release
const ZOOM_MS = 90;      // distance smoothing time constant
const MAX_LAT = 85;

const wrapLon = (v: number) => ((((v + 180) % 360) + 360) % 360) - 180;
const clamp = (v: number, lo: number, hi: number) => (v < lo ? lo : v > hi ? hi : v);
const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

export class GlobeControls {
  readonly view: GlobeView = { lat: 20, lon: 10, distance: 2.6 };
  private targetDistance = 2.6;
  private vLat = 0; // deg per ms
  private vLon = 0;
  private locked = false;
  private inputChanged = true;
  private easing = false;
  private easeStart = 0;
  private easeDuration = 0;
  private readonly from: GlobeView = { lat: 0, lon: 0, distance: 2.6 };
  private readonly to: GlobeView = { lat: 0, lon: 0, distance: 2.6 };
  private readonly pointers = new Map<number, { x: number; y: number }>();
  private pinchDist = 0;
  private lastMoveTime = 0;
  private readonly off: Array<() => void> = [];

  constructor(
    private readonly el: HTMLElement,
    private readonly onInput: () => void,
    private readonly opts: ControlsOptions,
  ) {
    const on = <K extends keyof HTMLElementEventMap>(type: K, fn: (e: HTMLElementEventMap[K]) => void, o?: AddEventListenerOptions) => {
      el.addEventListener(type, fn, o);
      this.off.push(() => el.removeEventListener(type, fn, o));
    };
    on('pointerdown', (e) => this.down(e));
    on('pointermove', (e) => this.move(e));
    on('pointerup', (e) => this.up(e));
    on('pointercancel', (e) => this.up(e));
    on('wheel', (e) => this.wheel(e), { passive: false });
    this.setLocked(false);
  }

  setLocked(v: boolean) {
    this.locked = v;
    // When locked the page must keep scrolling on touch and wheel.
    this.el.style.touchAction = v ? 'auto' : 'none';
    this.el.style.cursor = v ? '' : 'grab';
    if (v) { this.vLat = this.vLon = 0; this.pointers.clear(); }
  }

  jumpTo(v: GlobeView) {
    this.easing = false;
    this.view.lat = clamp(v.lat, -MAX_LAT, MAX_LAT);
    this.view.lon = wrapLon(v.lon);
    this.view.distance = this.targetDistance = this.clampDist(v.distance);
    this.vLat = this.vLon = 0;
    this.inputChanged = true;
  }

  easeTo(v: GlobeView, durationMs: number, now: number) {
    if (durationMs <= 0) { this.jumpTo(v); return; }
    Object.assign(this.from, this.view);
    this.to.lat = clamp(v.lat, -MAX_LAT, MAX_LAT);
    // shortest way round in longitude
    this.to.lon = this.view.lon + wrapLon(v.lon - this.view.lon);
    this.to.distance = this.clampDist(v.distance);
    this.easeStart = now;
    this.easeDuration = durationMs;
    this.easing = true;
    this.vLat = this.vLon = 0;
  }

  /** Advance by dt. Returns true when the view changed (render needed). */
  step(dtMs: number, now: number): boolean {
    let changed = this.inputChanged;
    this.inputChanged = false;
    const v = this.view;
    if (this.easing) {
      const t = clamp((now - this.easeStart) / this.easeDuration, 0, 1);
      const s = easeInOutCubic(t);
      v.lat = this.from.lat + (this.to.lat - this.from.lat) * s;
      v.lon = wrapLon(this.from.lon + (this.to.lon - this.from.lon) * s);
      // interpolate distance in log space so zooming feels uniform
      v.distance = Math.exp(Math.log(this.from.distance) + (Math.log(this.to.distance) - Math.log(this.from.distance)) * s);
      this.targetDistance = v.distance;
      if (t >= 1) this.easing = false;
      return true;
    }
    if (this.pointers.size === 0 && (this.vLat !== 0 || this.vLon !== 0)) {
      v.lon = wrapLon(v.lon + this.vLon * dtMs);
      v.lat = clamp(v.lat + this.vLat * dtMs, -MAX_LAT, MAX_LAT);
      const k = Math.exp(-dtMs / INERTIA_MS);
      this.vLat *= k;
      this.vLon *= k;
      if (Math.abs(this.vLat) + Math.abs(this.vLon) < 2e-4) this.vLat = this.vLon = 0;
      changed = true;
    }
    const dd = this.targetDistance - v.distance;
    if (dd !== 0) {
      v.distance = Math.abs(dd) < 1e-4 ? this.targetDistance : v.distance + dd * (1 - Math.exp(-dtMs / ZOOM_MS));
      changed = true;
    }
    return changed;
  }

  /** True while an animation (easing, inertia, zoom smoothing) still runs. */
  isAnimating(): boolean {
    return this.easing || this.vLat !== 0 || this.vLon !== 0 || this.targetDistance !== this.view.distance;
  }

  writeCamera(camera: PerspectiveCamera) {
    lonLatToVec3(this.view.lon, this.view.lat, this.view.distance, camera.position);
    camera.up.set(0, 1, 0);
    camera.lookAt(0, 0, 0);
  }

  dispose() {
    for (const f of this.off) f();
    this.off.length = 0;
    this.pointers.clear();
  }

  private clampDist(d: number) { return clamp(d, this.opts.minDistance, this.opts.maxDistance); }

  /** Update zoom limits (after a resize or texture size change); the view eases to the clamped distance. */
  setDistanceLimits(min: number, max: number) {
    this.opts.minDistance = min;
    this.opts.maxDistance = max;
    this.targetDistance = this.clampDist(this.targetDistance);
    this.to.distance = this.clampDist(this.to.distance);
    this.inputChanged = true;
  }

  /** Degrees of arc per CSS pixel at the sub-camera point: the surface follows the pointer. */
  private degPerPx(): number {
    const h = Math.max(1, this.el.clientHeight);
    return (this.opts.fovDeg / h) * Math.max(0.2, this.view.distance - 1);
  }

  private down(e: PointerEvent) {
    if (this.locked || (e.pointerType === 'mouse' && e.button !== 0)) return;
    this.easing = false;
    this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    this.el.setPointerCapture?.(e.pointerId);
    this.vLat = this.vLon = 0;
    this.pinchDist = 0;
    this.lastMoveTime = e.timeStamp;
    this.el.style.cursor = 'grabbing';
  }

  private move(e: PointerEvent) {
    const p = this.pointers.get(e.pointerId);
    if (this.locked || !p) return;
    const dx = e.clientX - p.x;
    const dy = e.clientY - p.y;
    p.x = e.clientX;
    p.y = e.clientY;
    if (this.pointers.size >= 2) {
      const [a, b] = Array.from(this.pointers.values());
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      if (this.pinchDist > 0 && dist > 0) {
        this.targetDistance = this.clampDist(1 + (this.targetDistance - 1) * (this.pinchDist / dist));
      }
      this.pinchDist = dist;
    } else {
      const k = this.degPerPx();
      const dLon = (-dx * k) / Math.max(0.5, Math.cos((this.view.lat * Math.PI) / 180));
      const dLat = dy * k;
      this.view.lon = wrapLon(this.view.lon + dLon);
      this.view.lat = clamp(this.view.lat + dLat, -MAX_LAT, MAX_LAT);
      const dt = Math.max(1, e.timeStamp - this.lastMoveTime);
      this.vLon = this.vLon * 0.5 + (dLon / dt) * 0.5;
      this.vLat = this.vLat * 0.5 + (dLat / dt) * 0.5;
      this.lastMoveTime = e.timeStamp;
    }
    this.inputChanged = true;
    this.onInput();
  }

  private up(e: PointerEvent) {
    if (!this.pointers.delete(e.pointerId)) return;
    this.pinchDist = 0;
    if (this.pointers.size === 0) {
      this.el.style.cursor = this.locked ? '' : 'grab';
      // a pause before release means the user stopped: no fling
      if (e.timeStamp - this.lastMoveTime > 60) this.vLat = this.vLon = 0;
      this.onInput();
    }
  }

  private wheel(e: WheelEvent) {
    if (this.locked) return; // let the page scroll
    e.preventDefault();
    this.easing = false;
    const delta = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * 400 : e.deltaY;
    // scale altitude above the surface, so zoom speed is even near the limit
    const alt = (this.targetDistance - 1) * Math.exp(delta * 0.0012);
    this.targetDistance = this.clampDist(1 + alt);
    this.onInput();
  }
}
