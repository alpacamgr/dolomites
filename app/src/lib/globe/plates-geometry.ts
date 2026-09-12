/**
 * Converts a plates/{age}.json FeatureCollection (docs/04-data-contracts.md 1.2)
 * into flat segment buffers, one per line style. Runs inside the plates worker
 * (and on the main thread only if workers are unavailable), so lon/lat are
 * converted to sphere coordinates exactly once per feature.
 *
 * Output layout: [x0,y0,z0, x1,y1,z1, ...] pairs, ready for
 * LineSegmentsGeometry.setPositions().
 */
import { DEG, lonLatToArray } from './geo';

export type PlateKind = 'landmass' | 'continent' | 'coastline' | 'subduction' | 'ridge' | 'transform' | 'other';
export const PLATE_KINDS: readonly PlateKind[] = ['landmass', 'continent', 'coastline', 'subduction', 'ridge', 'transform', 'other'];

export interface PlateBuffers {
  segments: Record<PlateKind, Float32Array>;
}

/** Longest chord drawn without subdivision; keeps lines on the curved surface. */
const MAX_STEP_RAD = 2 * DEG;

type Coords = number[][];

function lineStrings(geom: { type?: string; coordinates?: unknown } | null | undefined): Coords[] {
  if (!geom || !geom.coordinates) return [];
  const c = geom.coordinates;
  switch (geom.type) {
    case 'LineString': return [c as Coords];
    case 'MultiLineString': return c as Coords[];
    case 'Polygon': return c as Coords[];
    case 'MultiPolygon': return (c as Coords[][]).flat();
    default: return [];
  }
}

function kindOf(props: Record<string, unknown> | null | undefined): PlateKind | null {
  const k = props?.kind;
  if (k === 'landmass' || k === 'continent' || k === 'coastline') return k;
  if (k === 'boundary') {
    const t = props?.type;
    return t === 'subduction' || t === 'ridge' || t === 'transform' ? t : 'other';
  }
  return null; // 'dolomites' points and unknown kinds are not lines
}

const a = new Float64Array(3);
const b = new Float64Array(3);

function pushLine(out: number[], coords: Coords, r: number): void {
  for (let i = 0; i + 1 < coords.length; i++) {
    const p = coords[i];
    const q = coords[i + 1];
    const lon0 = p[0], lat0 = p[1], lon1 = q[0], lat1 = q[1];
    if (!Number.isFinite(lon0 + lat0 + lon1 + lat1)) continue;
    // Polygons are split at the antimeridian: skip the artificial cut edge
    // along +-180 and any edge that would wrap around the globe.
    if (Math.abs(lon1 - lon0) > 180) continue;
    if (Math.abs(lon0) >= 179.99 && Math.abs(lon1) >= 179.99) continue;
    if (Math.abs(lat0) >= 89.9 && Math.abs(lat1) >= 89.9) continue; // edges across the polar cap
    lonLatToArray(lon0, lat0, a, 0);
    lonLatToArray(lon1, lat1, b, 0);
    const dot = Math.min(1, Math.max(-1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]));
    const steps = Math.max(1, Math.ceil(Math.acos(dot) / MAX_STEP_RAD));
    let px = a[0] * r, py = a[1] * r, pz = a[2] * r;
    for (let s = 1; s <= steps; s++) {
      const t = s / steps;
      let x = a[0] + (b[0] - a[0]) * t;
      let y = a[1] + (b[1] - a[1]) * t;
      let z = a[2] + (b[2] - a[2]) * t;
      const k = r / Math.hypot(x, y, z);
      x *= k; y *= k; z *= k;
      out.push(px, py, pz, x, y, z);
      px = x; py = y; pz = z;
    }
  }
}

export function buildPlateBuffers(fc: unknown, radius: number): PlateBuffers {
  const features = (fc as { features?: unknown[] } | null)?.features;
  if (!Array.isArray(features)) throw new Error('not a FeatureCollection');
  const acc: Record<PlateKind, number[]> = {
    landmass: [], continent: [], coastline: [], subduction: [], ridge: [], transform: [], other: [],
  };
  for (const f of features as Array<{ properties?: Record<string, unknown>; geometry?: { type?: string; coordinates?: unknown } }>) {
    const kind = kindOf(f?.properties);
    if (!kind) continue;
    for (const line of lineStrings(f.geometry)) {
      if (Array.isArray(line) && line.length > 1) pushLine(acc[kind], line, radius);
    }
  }
  const segments = {} as Record<PlateKind, Float32Array>;
  for (const k of PLATE_KINDS) segments[k] = Float32Array.from(acc[k]);
  return { segments };
}
