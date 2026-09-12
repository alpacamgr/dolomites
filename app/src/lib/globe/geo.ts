/**
 * Shared lon/lat -> sphere mapping for the globe.
 *
 * It must match three.js SphereGeometry, which places texture column u at
 * phi = 2*pi*u with x = -cos(phi) * sin(theta), z = sin(phi) * sin(theta),
 * y = cos(theta), and uv.y = 1 at the north pole. With an equirectangular
 * texture (u = (lon + 180) / 360) that gives
 *
 *   x =  cos(lat) * cos(lon)
 *   y =  sin(lat)
 *   z = -cos(lat) * sin(lon)
 *
 * Seen from +X (lon 0, Greenwich facing the camera) with +Y up, east (-Z) is
 * on the right of the screen, so continents are not mirrored. Every overlay,
 * the marker and the camera use this one function.
 */
import type { Vector3 } from 'three';

export const DEG = Math.PI / 180;

export function lonLatToVec3(lon: number, lat: number, r: number, out: Vector3): Vector3 {
  const la = lat * DEG;
  const lo = lon * DEG;
  const c = Math.cos(la);
  return out.set(r * c * Math.cos(lo), r * Math.sin(la), -r * c * Math.sin(lo));
}

/** Writes the unit vector for lon/lat into arr[o..o+2]. */
export function lonLatToArray(lon: number, lat: number, arr: Float32Array | Float64Array | number[], o: number): void {
  const la = lat * DEG;
  const lo = lon * DEG;
  const c = Math.cos(la);
  arr[o] = c * Math.cos(lo);
  arr[o + 1] = Math.sin(la);
  arr[o + 2] = -c * Math.sin(lo);
}
