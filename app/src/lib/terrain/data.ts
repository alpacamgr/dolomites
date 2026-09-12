/**
 * Runtime detection of pipeline outputs. Every probe is best-effort: a missing
 * file returns null and the caller leaves that layer off.
 *
 * Tilesets are served as individual static tiles described by TileJSON (ADR 0006).
 * Their `tiles` templates are relative to the data base, so they are resolved here
 * rather than handing MapLibre the TileJSON URL.
 */

export type Bounds = [number, number, number, number];

export interface ResolvedTileJson {
  /** absolute tile URL template, e.g. https://host/data/terrain/elevation/{z}/{x}/{y}.webp */
  tiles: string;
  minzoom: number;
  maxzoom: number;
  bounds: Bounds;
  attribution: string;
  encoding?: 'mapbox' | 'terrarium';
  tileSize?: number;
}

export interface DetectedTerrain extends ResolvedTileJson {
  kind: 'tilejson' | 'terrarium';
  encoding: 'mapbox' | 'terrarium';
  tileSize: number;
  label: string;
  /** true when the global stand-in tiles are used instead of the project DEM */
  fallback: boolean;
}

export interface IceIndex {
  ages_ka: number[];
  path_pattern: string;
  bounds: Bounds;
  size?: [number, number];
  render_scale?: number;
  run?: string;
  /** [thickness_m, [r, g, b, a 0..255]] used to colourise the published frames */
  thickness_stops_m?: Array<[number, unknown]>;
}

export interface Meta {
  dataset_id?: string;
  label?: string;
  source_ref?: string | string[];
  attribution?: string;
  license?: string;
}

/** Contract 2.1 bbox, used when a TileJSON lacks bounds. */
export const DOLOMITES_BBOX: Bounds = [10.3, 45.8, 12.7, 47.2];

const TILEZEN_ATTRIBUTION =
  'STAND-IN elevation: AWS Terrain Tiles by Tilezen/Mapzen (SRTM, GMTED, EU-DEM, ETOPO1 and national sources; ' +
  'github.com/tilezen/joerd/blob/master/docs/attribution.md)';

export async function exists(url: string): Promise<boolean> {
  try {
    const r = await fetch(url, { method: 'HEAD' });
    return r.ok;
  } catch {
    return false;
  }
}

export async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

/** Plain text from a TileJSON attribution, which may contain entities and links. */
function plainText(html: string): string {
  const el = document.createElement('div');
  el.innerHTML = html;
  return (el.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/**
 * Read `${dataBase}/${path}` (a TileJSON 3.0 file) and resolve its first tile
 * template against the data base. Returns null when the file is missing or unusable.
 */
export async function readTileJson(dataBase: string, path: string): Promise<ResolvedTileJson | null> {
  const tj = await fetchJson<{
    tiles?: string[]; minzoom?: number; maxzoom?: number; bounds?: number[];
    attribution?: string; encoding?: 'mapbox' | 'terrarium'; tileSize?: number;
  }>(`${dataBase}/${path}`);
  const template = tj?.tiles?.[0];
  if (!tj || !template) return null;
  // String concatenation, not new URL(template, base): URL() would percent-encode {z}/{x}/{y}.
  const base = new URL(`${dataBase.replace(/\/$/, '')}/`, location.href).href;
  const rel = template.replace(/^\{base\}\//, '').replace(/^\.?\//, '');
  const tiles = /^[a-z]+:\/\//i.test(template) ? template : base + rel;
  const b = tj.bounds;
  return {
    tiles,
    minzoom: tj.minzoom ?? 0,
    maxzoom: tj.maxzoom ?? 22,
    bounds: b && b.length === 4 && b[2] > b[0] && b[3] > b[1] ? (b as Bounds) : DOLOMITES_BBOX,
    attribution: tj.attribution ? plainText(tj.attribution) : '',
    encoding: tj.encoding,
    tileSize: tj.tileSize,
  };
}

export async function detectTerrain(dataBase: string): Promise<DetectedTerrain> {
  const [tj, meta] = await Promise.all([
    readTileJson(dataBase, 'terrain/elevation/tiles.json'),
    fetchJson<Meta>(`${dataBase}/terrain/dolomites-terrain.meta.json`),
  ]);
  if (tj) {
    return {
      ...tj,
      kind: 'tilejson',
      encoding: tj.encoding ?? 'mapbox',
      tileSize: tj.tileSize ?? 512,
      attribution: meta?.attribution ?? tj.attribution,
      label: meta?.label ?? 'observed',
      fallback: false,
    };
  }
  console.info('[terrain] terrain/elevation/tiles.json unavailable; using AWS Terrain Tiles as a stand-in');
  return {
    kind: 'terrarium',
    tiles: 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png',
    encoding: 'terrarium',
    tileSize: 256,
    minzoom: 0,
    maxzoom: 12,
    bounds: DOLOMITES_BBOX,
    attribution: TILEZEN_ATTRIBUTION,
    label: 'observed',
    fallback: true,
  };
}
