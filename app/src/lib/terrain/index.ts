/**
 * Terrain engine: MapLibre GL JS 6.7 implementation of SceneEngine (../scene-api.ts).
 *
 *  - raster-dem from the project's static tiles via TileJSON (AWS Terrain Tiles stand-in if missing)
 *  - 3D `terrain` (exaggeration 1 by default), `color-relief` alpine hypsometric tint,
 *    soft multidirectional `hillshade`, `sky` with horizon fog
 *  - overlays toggled by dataset id: ice frames (image sources A/B), geology
 *    (vector tiles via TileJSON + coverage outline + optional gaps hatch), glaciers / LIA / LGM /
 *    fault traces (GeoJSON, added on first use), localities (HTML markers)
 *  - geology colour key: reports the unit colours rendered in view (onGeologyKey) and
 *    highlights units on request (setGeologyFocus) or for the scene's `emphasis` interval
 *
 * The style is built once; state changes only toggle visibility and paint values.
 */
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
// MapLibre 6 loads its worker from a separate file that Vite's dependency
// optimizer does not copy; let Vite bundle the worker (with its shared chunk)
// and hand MapLibre the URL. Works in dev and in the static build.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import type {
  SceneEngine, SceneState, EngineStatus, TimeUnit, GlobeCamera, TerrainCamera, LayerRef,
} from '../scene-api';
import {
  elevationExpression, geologyFillColorExpression, geologyIsDatedExpression, isDatedColor, faultColorExpression,
  GEOLOGY_UNDATED_FILL,
} from './palette';
import {
  detectTerrain, exists, fetchJson, readTileJson,
  type DetectedTerrain, type IceIndex, type Meta, type ResolvedTileJson,
} from './data';
import { IceManager } from './ice';
import { unitKey, type GeologyFocus, type GeologyKeyData } from '../story/geologyKey';

export interface TerrainOptions {
  /** base URL of the data directory, default '/data' */
  dataBase?: string;
  /** vertical exaggeration; default 1.0 (true to data) */
  exaggeration?: number;
  /** disable user pan/zoom/rotate (the story controller drives the camera) */
  lock?: boolean;
  /** page background, used where there is no data; default the site --bg */
  background?: string;
  /** flat UI strings (content/ui) for popups; English fallbacks are built in */
  strings?: Record<string, string>;
  /** number formatting locale, default 'en' */
  locale?: string;
  /** prefers-reduced-motion: the camera jumps instead of flying */
  reduceMotion?: boolean;
  /** ICS chart intervals, used to name a mapped age range in the popup when the source gives no age string */
  icsIntervals?: Array<{ name: string; type: string; start_ma: number; end_ma: number }>;
}

/** Non-contract extras used by the dev page and the legend. */
export interface TerrainEngine extends SceneEngine {
  setExaggeration(value: number): void;
  setLock(lock: boolean): void;
  getTerrainInfo(): DetectedTerrain | null;
  getIceRange(): [number, number] | null;
  getMap(): maplibregl.Map | null;
  /** Highlight geology units and dim the rest; null restores the scene's emphasis (if any). */
  setGeologyFocus(focus: GeologyFocus | null): void;
  /** Colour-key data for the geology rendered in view; null while geology is off. */
  onGeologyKey(cb: (key: GeologyKeyData | null) => void): () => void;
}

const ID = {
  DEM: 'dolomites-terrain',
  GEOLOGY: 'geology-dolomites',
  GEOLOGY_BZ: 'geology-suedtirol',
  ICE: 'seguinot2018-alps-1km',
  RGI: 'rgi7-region11',
  LIA: 'reinthaler-paul-2025-lia',
  LGM: 'glacimontis-lgm',
  FAULTS: 'diss-3-3-1',
  LOCALITIES: 'localities',
} as const;
const KNOWN = new Set<string>(Object.values(ID));
/** Both geology ids select the merged geology tiles (the chapters still name the South Tyrol id). */
const canonical = (id: string) => (id === ID.GEOLOGY_BZ ? ID.GEOLOGY : id);

/** English fallbacks for the merged geology sources; localized names come from `geology_popup.source.<id>`. */
const GEOLOGY_SOURCE_NAMES: Record<string, string> = {
  'bz-geology-carg': 'South Tyrol geological map (CARG)',
  'pat-geology-carta-geologica': 'Trentino geological map (PAT)',
  'veneto-litologia-250k': 'Veneto lithology map',
  'swisstopo-geocover': 'GeoCover geological vector data (swisstopo)',
  'ispra-geologia-100k-inspire': 'Geological Map of Italy (ISPRA)',
  'geosphere-geologicunits-500k': 'Geological units of Austria (GeoSphere Austria)',
};
/** Sources whose meta scale denominator exceeds this get a "coarser map in view" note in the key. */
const COARSE_ABOVE = 25_000;

interface GeologyMeta extends Meta {
  sources?: Array<{ dataset_id: string; title?: string; scale?: string; attribution?: string }>;
  coverage?: { file?: string; gaps_file?: string };
}

/** Draw order of every style layer the engine may add (bottom to top). */
const ORDER = [
  // geology sits under the hillshade so relief keeps reading through the unit colours
  'color-relief', 'geology-fill', 'hillshade', 'geology-gaps', 'geology-line', 'geology-coverage',
  'ice-a', 'ice-b', 'lgm-line', 'lia-line', 'rgi-fill', 'rgi-line', 'faults-casing', 'faults-line',
];

type Position = [number, number];
interface GeoFeature {
  type: 'Feature';
  properties: Record<string, unknown> | null;
  geometry: { type: string; coordinates: unknown } | null;
}
interface GeoCollection { type: 'FeatureCollection'; features: GeoFeature[] }

interface GeoJsonOverlay {
  id: string;
  file: string;
  layers: maplibregl.AddLayerObject[];
  /** optional client-side reduction of the file before it is drawn */
  transform?: (fc: GeoCollection) => GeoCollection;
}

const zoomWidth = (z0: number, w0: number, z1: number, w1: number) =>
  ['interpolate', ['linear'], ['zoom'], z0, w0, z1, w1] as never;

/**
 * DISS 3.3.1 fault traces only. Composite sources come as `composite_top` LineStrings
 * (the CSS top trace). Individual sources (ISS) are MultiPolygons holding the source's
 * surface-projection rectangle plus its top trace stored as a zero-area ring (A, B, A, A);
 * the trace is kept, the rectangles are not drawn.
 */
export function faultTraces(fc: GeoCollection): GeoCollection {
  const area = (ring: Position[]) => {
    let a = 0;
    for (let i = 0; i < ring.length - 1; i++) a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
    return Math.abs(a / 2);
  };
  const out: GeoFeature[] = [];
  for (const f of fc.features ?? []) {
    const g = f.geometry;
    if (!g) continue;
    if (g.type === 'LineString' || g.type === 'MultiLineString') { out.push(f); continue; }
    const polys = (g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : []) as Position[][][];
    for (const poly of polys) {
      for (const ring of poly) {
        if (area(ring) > 1e-10) continue;
        const pts: Position[] = [];
        for (const p of ring) if (!pts.some((q) => q[0] === p[0] && q[1] === p[1])) pts.push(p);
        if (pts.length >= 2) out.push({ type: 'Feature', properties: f.properties, geometry: { type: 'LineString', coordinates: pts } });
      }
    }
  }
  return { type: 'FeatureCollection', features: out };
}

const OVERLAYS: GeoJsonOverlay[] = [
  {
    id: ID.LGM, file: 'lgm-extent',
    layers: [
      // One light, thin dashed line: the modelled ice frame carries the visual weight.
      { id: 'lgm-line', type: 'line', source: ID.LGM,
        paint: { 'line-color': '#7c9db3', 'line-width': zoomWidth(8, 0.6, 12, 1.1), 'line-dasharray': [3, 2.5], 'line-opacity': 0.55 } },
    ],
  },
  {
    id: ID.LIA, file: 'glaciers-lia',
    layers: [
      { id: 'lia-line', type: 'line', source: ID.LIA,
        paint: { 'line-color': '#5d7f90', 'line-width': zoomWidth(9, 0.5, 12, 1.2), 'line-dasharray': [2.5, 1.5], 'line-opacity': 0.9 } },
    ],
  },
  {
    id: ID.RGI, file: 'glaciers-rgi7',
    layers: [
      { id: 'rgi-fill', type: 'fill', source: ID.RGI, paint: { 'fill-color': '#e9f6fa', 'fill-opacity': 0.85 } },
      { id: 'rgi-line', type: 'line', source: ID.RGI,
        paint: { 'line-color': '#3f84a0', 'line-width': zoomWidth(9, 0.5, 12, 1.5), 'line-opacity': 1 } },
    ],
  },
  {
    id: ID.FAULTS, file: 'faults',
    transform: faultTraces,
    layers: [
      // light casing keeps the thin traces legible over geology colours
      { id: 'faults-casing', type: 'line', source: ID.FAULTS,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#fbf8f2', 'line-width': zoomWidth(8, 2.2, 12, 3.4), 'line-opacity': 0.55 } },
      { id: 'faults-line', type: 'line', source: ID.FAULTS,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': faultColorExpression() as never, 'line-width': zoomWidth(8, 0.9, 12, 1.6), 'line-opacity': 0.85 } },
    ],
  },
];

/** Paint property that carries LayerRef.opacity for each style layer, with its base value. */
const OPACITY: Record<string, [string, number]> = {
  'color-relief': ['color-relief-opacity', 1],
  hillshade: ['hillshade-exaggeration', 0.5],
  'geology-gaps': ['fill-opacity', 0.9],
  'geology-coverage': ['line-opacity', 0.55],
  'lgm-line': ['line-opacity', 0.55],
  'lia-line': ['line-opacity', 0.9],
  'rgi-fill': ['fill-opacity', 0.85],
  'rgi-line': ['line-opacity', 1],
  'faults-casing': ['line-opacity', 0.55],
  'faults-line': ['line-opacity', 0.85],
};
/**
 * Geology fill opacities. Dated units at 0.55 keep the hillshade reading under the ICS
 * colours (mountains-first, unit colours as a tint, like a printed geological map on
 * shaded relief); undated units get a lighter neutral wash; a focus lifts matching units
 * and dims the rest, but never so hard that context disappears. Coarse-source polygons
 * (>1:25,000 scale) get an extra multiplier so they read as "less detailed" instead of
 * as a different paint job.
 */
const GEOLOGY_OPACITY = { dated: 0.55, undated: 0.34, hoverLift: 0.2, focus: 0.72, dimmed: 0.3, coarse: 0.75 };
/**
 * Gap parts narrower than this mean width (metres) are thin seams along map-sheet borders; hatched,
 * they read as stripes across the mountains, so they stay plain terrain (no hatch, no outline, no popup).
 * A gaps file without `mean_width_m` hatches every part.
 */
const GAP_MIN_WIDTH_M = 200;
const GAP_HATCH_FILTER = ['any', ['!', ['has', 'mean_width_m']], ['>=', ['to-number', ['get', 'mean_width_m'], 0], GAP_MIN_WIDTH_M]];

/** Camera timing (docs/ux/2026-09-timeline-and-geology-ux.md): same view, and right after a view switch. */
const CAMERA_MS = 1100;
const CAMERA_AFTER_SWITCH_MS = 900;
const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const easeOutCubic = (t: number) => 1 - (1 - t) ** 3;

const ENGINE_CSS = `
.tg-marker{display:flex;align-items:center;gap:6px;cursor:default}
.tg-marker-dot{width:9px;height:9px;border-radius:50%;background:#fff7e6;border:2px solid #6b4f2a;box-shadow:0 1px 3px rgba(0,0,0,.35)}
.tg-marker-label{opacity:0;transition:opacity .12s;font:500 12px/1.2 system-ui,sans-serif;color:#2b2419;background:rgba(246,243,238,.92);padding:2px 6px;border-radius:3px;white-space:nowrap;pointer-events:none}
.tg-marker:hover .tg-marker-label{opacity:1}
.tg-popup .maplibregl-popup-content{padding:8px 10px;border-radius:6px;background:#fbf9f5;color:#2b2419;font:12px/1.35 system-ui,sans-serif;box-shadow:0 2px 10px rgba(0,0,0,.18)}
.tg-popup .maplibregl-popup-tip{border-top-color:#fbf9f5;border-bottom-color:#fbf9f5}
.tg-pop-title{display:flex;gap:6px;align-items:center;font-weight:600;font-size:13px}
.tg-pop-swatch{width:11px;height:11px;border-radius:2px;flex:none;border:1px solid rgba(0,0,0,.2)}
.tg-pop-swatch.hatch{background:repeating-linear-gradient(135deg,rgba(70,62,52,.6) 0 1px,rgba(246,243,238,.5) 1px 4px)}
.tg-pop-muted{color:#857a6a;font-style:italic;margin-top:2px}
.tg-pop-row{color:#5b5245;margin-top:2px;font-variant-numeric:tabular-nums}
.tg-pop-note{color:#857a6a;font-size:11px}
.tg-pop-badge{display:inline-block;margin-top:5px;padding:0 5px;border:1px solid #8a7a62;border-radius:8px;font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:#6b5a40}
.tg-pop-src{margin-top:4px;font-size:10px;color:#857a6a;max-width:240px}
`;

let workerConfigured = false;

interface DataProbe {
  iceIndex: IceIndex | null;
  iceMeta: Meta | null;
  geologyTiles: ResolvedTileJson | null;
  geologyMeta: GeologyMeta | null;
  /** coverage GeoJSON file name inside terrain/, as named by the geology meta */
  geologyCoverage: string | null;
  /** gaps GeoJSON file name inside terrain/ (areas with no open geology), as named by the geology meta */
  geologyGaps: string | null;
  localities: boolean;
  localitiesMeta: Meta | null;
  overlays: Array<{ ok: boolean; meta: Meta | null }>;
}

/**
 * Availability of optional datasets, probed once per page session and shared by
 * every engine instance. Geology is gated on its TileJSON: when geology/tiles.json is
 * absent, neither its meta nor the coverage file is requested, and the coverage and gaps
 * files are only loaded when the meta names them.
 */
const probes = new Map<string, Promise<DataProbe>>();
function probeData(dataBase: string): Promise<DataProbe> {
  let p = probes.get(dataBase);
  if (!p) {
    const t = `${dataBase}/terrain`;
    const geology = (async () => {
      const tiles = await readTileJson(dataBase, 'terrain/geology/tiles.json');
      if (!tiles) return { tiles: null, meta: null, coverage: null, gaps: null };
      const meta = await fetchJson<GeologyMeta>(`${t}/geology-dolomites.meta.json`);
      return { tiles, meta, coverage: meta?.coverage?.file ?? null, gaps: meta?.coverage?.gaps_file ?? null };
    })();
    p = Promise.all([
      fetchJson<IceIndex>(`${t}/ice/index.json`),
      fetchJson<Meta>(`${t}/ice/meta.json`),
      geology,
      fetchJson<Meta>(`${t}/localities.meta.json`),
      Promise.all(OVERLAYS.map(async (o) => {
        const meta = await fetchJson<Meta>(`${t}/${o.file}.meta.json`);
        return { ok: !!meta || (await exists(`${t}/${o.file}.geojson`)), meta };
      })),
    ]).then(async ([iceIndex, iceMeta, geo, localitiesMeta, overlays]) => ({
      iceIndex,
      iceMeta,
      geologyTiles: geo.tiles,
      geologyMeta: geo.meta,
      geologyCoverage: geo.coverage,
      geologyGaps: geo.gaps,
      localities: !!localitiesMeta || (await exists(`${t}/localities.geojson`)),
      localitiesMeta,
      overlays,
    }));
    probes.set(dataBase, p);
  }
  return p;
}

function esc(s: unknown): string {
  return String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

/** Scale denominator of a meta scale string such as "1:250,000 (digitised ...)". */
function scaleDenominator(scale: string | undefined): number | null {
  const m = scale?.match(/1:([\d,.\s]+\d)/);
  return m ? Number(m[1].replace(/[,.\s]/g, '')) : null;
}

/** Diagonal hatch for areas without an open geological map; the legend swatch mirrors it in CSS. */
function hatchPattern(): ImageData | null {
  const s = 16;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = s;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.fillStyle = 'rgba(246,243,238,0.32)';
  ctx.fillRect(0, 0, s, s);
  ctx.strokeStyle = 'rgba(70,62,52,0.6)';
  ctx.lineWidth = 1.6;
  for (const o of [-s, 0, s]) {
    ctx.beginPath();
    ctx.moveTo(o, s);
    ctx.lineTo(o + s, 0);
    ctx.stroke();
  }
  return ctx.getImageData(0, 0, s, s);
}

export function createTerrainEngine(options: TerrainOptions = {}): TerrainEngine {
  const dataBase = (options.dataBase ?? '/data').replace(/\/$/, '');
  const background = options.background ?? '#f6f3ee';
  const strings = options.strings ?? {};
  const locale = options.locale ?? 'en';
  const reduceMotion = options.reduceMotion ?? false;
  let exaggeration = options.exaggeration ?? 1;
  let locked = options.lock ?? false;

  const S = (key: string, fallback: string) => strings[key] ?? fallback;
  const fill = (s: string, vars: Record<string, string>) => s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
  /** Localized source name (`geology_popup.source.<id>`), then the English fallback, then the meta title. */
  const sourceName = (id: string, title?: string) => S(`geology_popup.source.${id}`, GEOLOGY_SOURCE_NAMES[id] ?? title ?? id);
  const ics = options.icsIntervals ?? [];
  const RANKS = ['age', 'epoch', 'period', 'era', 'eon'];
  /** Localized ICS name from `ics_names`; null when the page language has no official translation for it. */
  const icsName = (name: string) => strings[`ics_names.${name}`] ?? (locale.startsWith('en') ? name : null);
  const sameMa = (a: number, b: number) => Math.abs(a - b) < 1e-6;
  /**
   * ICS name(s) whose boundaries equal a mapped range exactly: one interval spanning it (finest rank
   * first), else an older and a younger interval of the same rank. Null otherwise, so the popup never
   * names an interval the bounds do not match.
   */
  function rangeName(ageMax: number, ageMin: number): string | null {
    for (const rank of RANKS) {
      const one = ics.find((i) => i.type === rank && sameMa(i.start_ma, ageMax) && sameMa(i.end_ma, ageMin));
      const n = one ? icsName(one.name) : null;
      if (n) return n;
    }
    for (const rank of RANKS) {
      const older = ics.find((i) => i.type === rank && sameMa(i.start_ma, ageMax));
      const younger = ics.find((i) => i.type === rank && sameMa(i.end_ma, ageMin));
      const a = older ? icsName(older.name) : null;
      const b = younger ? icsName(younger.name) : null;
      if (a && b) return `${a} – ${b}`;
    }
    return null;
  }
  const nf1 = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  const ageOne = (ma: number) => (ma <= 0 ? S('time.now', 'today')
    : ma < 1 ? `${nf1.format(ma * 1000)} ${S('time.ka', 'ka')}` : `${nf1.format(ma)} ${S('time.ma', 'Ma')}`);
  /** Rounded range: one decimal, Ma from 1 Ma up, ka below, "today" at 0. */
  function rangeText(ageMax: number, ageMin: number): string {
    if (sameMa(ageMax, ageMin)) return ageOne(ageMax);
    if (ageMin >= 1) return `${nf1.format(ageMax)}–${nf1.format(ageMin)} ${S('time.ma', 'Ma')}`;
    if (ageMax < 1 && ageMin > 0) return `${nf1.format(ageMax * 1000)}–${nf1.format(ageMin * 1000)} ${S('time.ka', 'ka')}`;
    return `${ageOne(ageMax)} – ${ageOne(ageMin)}`;
  }

  let container: HTMLElement | null = null;
  let map: maplibregl.Map | null = null;
  let terrain: DetectedTerrain | null = null;
  let ice: IceManager | null = null;
  let mounted = false;
  let disposed = false;
  let loading = true;
  let paused = false;
  let resumedAt = 0;
  let cameraApplied = false;
  let wanted = new Map<string, LayerRef>();
  let lastTime: { unit: TimeUnit; value: number } | null = null;
  let popup: maplibregl.Popup | null = null;
  let popupFor: string | null = null;
  let hoveredUnit: string | null = null;
  let geologyTiles: ResolvedTileJson | null = null;
  let geologyMeta: GeologyMeta | null = null;
  let geologyCoverage: string | null = null;
  let geologyGaps: string | null = null;
  let geologyOpacity = 1;
  let emphasis: { start_ma: number; end_ma: number } | null = null;
  let focus: GeologyFocus | null = null;

  const listeners = new Set<(s: EngineStatus) => void>();
  const keyListeners = new Set<(k: GeologyKeyData | null) => void>();
  const metas = new Map<string, Meta>();
  const available = new Set<string>();
  const installed = new Map<string, Promise<void>>();
  const markers: maplibregl.Marker[] = [];

  // ---------- status ----------
  function attributions(): string[] {
    const out: string[] = [];
    const add = (id: string) => {
      const m = metas.get(id);
      if (m?.attribution) out.push(m.label ? `${m.attribution} [${m.label}]` : m.attribution);
    };
    add(ID.DEM); // the DEM shapes the 3D surface even when its tint is hidden
    for (const id of wanted.keys()) if (id !== ID.DEM && available.has(id)) add(id);
    return out;
  }
  function emit() {
    const s: EngineStatus = { loading, attributions: attributions() };
    listeners.forEach((cb) => cb(s));
  }
  function setLoading(v: boolean) {
    if (v !== loading) { loading = v; emit(); }
  }

  // ---------- helpers ----------
  function beforeId(layerId: string): string | undefined {
    for (let i = ORDER.indexOf(layerId) + 1; i < ORDER.length; i++) {
      if (map!.getLayer(ORDER[i])) return ORDER[i];
    }
    return undefined;
  }
  function addOrdered(layer: maplibregl.AddLayerObject) {
    const layout = { ...('layout' in layer ? layer.layout : {}), visibility: 'none' };
    map!.addLayer({ ...layer, layout } as maplibregl.AddLayerObject, beforeId(layer.id));
  }
  function show(layerId: string, on: boolean, opacity = 1) {
    if (!map?.getLayer(layerId)) return;
    map.setLayoutProperty(layerId, 'visibility', on ? 'visible' : 'none');
    if (!on) return;
    if (layerId === 'geology-fill') {
      geologyOpacity = opacity;
      map.setPaintProperty(layerId, 'fill-opacity', geologyFillOpacity() as never);
      return;
    }
    const o = OPACITY[layerId];
    if (o) map.setPaintProperty(layerId, o[0] as 'fill-opacity', o[1] * opacity);
  }
  /** Map-side expression for the key's focus (hover row) or the scene's emphasis interval. */
  function focusExpression(): unknown[] | null {
    const f = focus ?? (emphasis ? { within: emphasis } : null);
    if (!f) return null;
    const any: unknown[] = ['any'];
    if (f.keys?.length) {
      any.push(['in', ['concat', ['to-string', ['get', 'color']], '|', ['to-string', ['get', 'age_min_ma']]], ['literal', f.keys]]);
    }
    if (f.undated) any.push(['!', geologyIsDatedExpression]);
    if (f.within) {
      const eps = 1e-6;
      any.push(['all',
        ['>=', ['to-number', ['coalesce', ['get', 'age_min_ma'], -1]], f.within.end_ma - eps],
        ['<=', ['to-number', ['coalesce', ['get', 'age_max_ma'], 1e9]], f.within.start_ma + eps]]);
    }
    return any.length > 1 ? any : ['literal', false];
  }
  /**
   * Dated units at the base opacity, undated units as a light wash; a focus dims everything
   * it does not match. Coarse sources (>1:25,000) get an extra factor so they read as a
   * lighter wash than the detailed maps in the same view; the ICS hue is not touched, so
   * legend swatches stay identical.
   */
  function geologyFillOpacity(): unknown[] {
    const o = geologyOpacity;
    const G = GEOLOGY_OPACITY;
    const coarseIds = [...coarseSources.keys()];
    const coarse = (v: number): number | unknown[] => (coarseIds.length
      ? ['case', ['in', ['get', 'source'], ['literal', coarseIds]], Math.min(1, v * G.coarse), Math.min(1, v)]
      : Math.min(1, v));
    const byDated = (d: number, u: number) => ['case', geologyIsDatedExpression, coarse(d * o), coarse(u * o)];
    const f = focusExpression();
    // dimmed units keep the coarse wash so a dimmed coarse polygon does not read louder than the emphasised bedrock
    const base = f ? ['case', f, Math.min(1, G.focus * o), coarse(G.dimmed * o)] : byDated(G.dated, G.undated);
    return ['case', ['boolean', ['feature-state', 'hover'], false], byDated(G.dated + G.hoverLift, G.undated + G.hoverLift), base];
  }
  /** Emphasis outline: firmer at low zoom (0.9 px) than at high zoom, so the focus reads even before z11. */
  function geologyLineWidth(): unknown[] {
    const f = focusExpression();
    const hairline: unknown[] = ['interpolate', ['linear'], ['zoom'], 10, 0, 11, 0.3, 13, 0.6];
    const focus: unknown[] = ['interpolate', ['linear'], ['zoom'], 8, 0.7, 11, 1.2, 13, 1.6];
    const hover: unknown[] = ['interpolate', ['linear'], ['zoom'], 8, 1.2, 11, 1.6, 13, 2];
    return ['case',
      ['boolean', ['feature-state', 'hover'], false], hover,
      f ?? false, focus,
      hairline];
  }
  function geologyLineOpacity(): unknown[] {
    const f = focusExpression();
    const hairline: unknown[] = ['interpolate', ['linear'], ['zoom'], 10, 0, 11, 0.2, 13, 0.35];
    return ['case',
      ['boolean', ['feature-state', 'hover'], false], 0.75,
      f ?? false, 0.85,
      hairline];
  }
  function refreshGeologyPaint() {
    if (!map?.getLayer('geology-fill')) return;
    map.setPaintProperty('geology-fill', 'fill-opacity', geologyFillOpacity() as never);
    if (map.getLayer('geology-line')) {
      map.setPaintProperty('geology-line', 'line-width', geologyLineWidth() as never);
      map.setPaintProperty('geology-line', 'line-opacity', geologyLineOpacity() as never);
    }
    // paint changes do not invalidate the terrain render-to-texture cache
    map.terrain?.tileManager.releaseAllRTT();
    map.triggerRepaint();
  }
  function applyLock() {
    if (!map) return;
    for (const h of [map.scrollZoom, map.boxZoom, map.dragRotate, map.dragPan, map.keyboard,
      map.doubleClickZoom, map.touchZoomRotate, map.touchPitch]) {
      if (locked) h.disable(); else h.enable();
    }
  }
  function showPopup(forId: string, lngLat: maplibregl.LngLat, html: () => string) {
    if (!map) return;
    if (!popup) {
      popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: 'tg-popup', offset: 12, maxWidth: '280px' });
      popup.setLngLat(lngLat).setHTML(html()).addTo(map);
    } else if (popupFor !== forId) popup.setHTML(html());
    popupFor = forId;
    popup.setLngLat(lngLat);
  }
  function hidePopup() {
    popup?.remove();
    popup = null;
    popupFor = null;
  }
  /** Remove the popup, the hovered unit's highlight and the help cursor. */
  function clearGeologyHover() {
    if (map && hoveredUnit != null && map.getSource('geology')) {
      map.setFeatureState({ source: 'geology', sourceLayer: 'units', id: hoveredUnit }, { hover: false });
    }
    hoveredUnit = null;
    if (map) map.getCanvas().style.cursor = '';
    hidePopup();
  }
  const gapHtml = () => '<div class="tg-pop-title"><span class="tg-pop-swatch hatch"></span>'
    + `${esc(S('geology_popup.gap_title', 'No open geological map'))}</div>`
    + `<div class="tg-pop-row">${esc(S('geology_popup.gap_text', 'No open vector geological map covers this area. This is a gap in the open data, not an absence of rock.'))}</div>`;

  // ---------- geology colour key ----------
  let keyDirty = true;
  let keyPending = false;
  let lastKeySig = '';
  let lastKey: GeologyKeyData | null = null;
  const coarseSources = new Map<string, { name: string; scale: string }>();

  function geologyVisible(): boolean {
    return !!map && wanted.has(ID.GEOLOGY) && available.has(ID.GEOLOGY) && !!map.getLayer('geology-fill')
      && map.getLayoutProperty('geology-fill', 'visibility') === 'visible';
  }
  function publishKey(k: GeologyKeyData | null) {
    const sig = k ? JSON.stringify(k) : '';
    if (sig === lastKeySig) return;
    lastKeySig = sig;
    lastKey = k;
    keyListeners.forEach((cb) => cb(k));
  }
  function scheduleKey() {
    if (keyPending || !keyListeners.size) return;
    keyPending = true;
    const run = () => { keyPending = false; computeKey(); };
    // outside the frame: the query walks every rendered feature
    if ('requestIdleCallback' in window) window.requestIdleCallback(run, { timeout: 500 });
    else setTimeout(run, 60);
  }
  let keyRun = 0;
  const onIdle = (cb: (deadline?: IdleDeadline) => void) => {
    if ('requestIdleCallback' in window) window.requestIdleCallback(cb, { timeout: 600 });
    else setTimeout(() => cb(), 30);
  };
  /**
   * A whole-view queryRenderedFeatures walks tens of thousands of features (measured 70-100 ms
   * at the reefs camera), so the view is queried as a grid of boxes spread over idle callbacks,
   * at most ~10 ms of work per callback. A camera move or a newer run abandons the pass.
   */
  function computeKey() {
    if (!map || disposed || paused) return;
    if (!geologyVisible()) { publishKey(null); return; }
    if (!map.loaded() || !map.areTilesLoaded()) return; // the next idle retries
    keyDirty = false;
    const run = ++keyRun;
    const m = map;
    const w = m.getCanvas().clientWidth;
    const h = m.getCanvas().clientHeight;
    const COLS = 6, ROWS = 4;
    const boxes: Array<[[number, number], [number, number]]> = [];
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < COLS; c++) boxes.push([[(c * w) / COLS, (r * h) / ROWS], [((c + 1) * w) / COLS, ((r + 1) * h) / ROWS]]);
    }
    const units = new Map<string, { color: string; ageMin: number | null }>();
    const coarse = new Map<string, { id: string; name: string; scale: string }>();
    let undated = false;
    let withheld = false;
    const step = () => {
      if (run !== keyRun || disposed || paused || map !== m) return;
      if (m.isMoving()) { keyDirty = true; return; }
      const t0 = performance.now();
      do {
        const box = boxes.pop()!;
        for (const f of m.queryRenderedFeatures(box, { layers: ['geology-fill'] })) {
          const p = f.properties ?? {};
          const src = typeof p.source === 'string' ? p.source : '';
          const cs = coarseSources.get(src);
          if (cs && !coarse.has(src)) coarse.set(src, { id: src, ...cs });
          if (isDatedColor(p.color)) {
            const ageMin = typeof p.age_min_ma === 'number' ? p.age_min_ma : null;
            const k = unitKey(p.color, ageMin);
            if (!units.has(k)) units.set(k, { color: p.color, ageMin });
          } else if (p.age_basis === 'withheld') withheld = true;
          else undated = true;
        }
      } while (boxes.length && performance.now() - t0 < 10);
      if (boxes.length) { onIdle(step); return; }
      publishKey({
        units: [...units.values()].sort((a, b) => (a.ageMin ?? 1e9) - (b.ageMin ?? 1e9) || a.color.localeCompare(b.color)),
        undated,
        withheld,
        coarse: [...coarse.values()],
        gapsLayer: !!m.getLayer('geology-gaps'),
      });
    };
    step();
  }

  // ---------- style ----------
  function buildStyle(t: DetectedTerrain): maplibregl.StyleSpecification {
    const dem: maplibregl.RasterDEMSourceSpecification = {
      type: 'raster-dem', tiles: [t.tiles], tileSize: t.tileSize, encoding: t.encoding,
      minzoom: t.minzoom, maxzoom: t.maxzoom, bounds: t.bounds,
    };
    return {
      version: 8,
      // Separate sources for the 3D mesh and for tint/hillshade, as MapLibre
      // recommends: the terrain source is sampled at lower zoom than the layers.
      sources: { dem, 'dem-terrain': { ...dem } },
      terrain: { source: 'dem-terrain', exaggeration },
      sky: {
        // Softer, longer atmospheric fade so the DEM bbox edge dissolves into the horizon
        // instead of cutting hard against the page background at pitched cameras.
        'sky-color': '#c6d6e3',
        'horizon-color': '#e7e2d8',
        'fog-color': background,
        'sky-horizon-blend': 0.8,
        'horizon-fog-blend': 0.75,
        'fog-ground-blend': 0.45,
        'atmosphere-blend': 0,
      },
      layers: [
        { id: 'background', type: 'background', paint: { 'background-color': background } },
        {
          id: 'color-relief', type: 'color-relief', source: 'dem',
          paint: { 'color-relief-color': elevationExpression() as never, 'color-relief-opacity': 1 },
        },
        {
          // Soft relief: one main light from 335 deg plus two weak fill lights; shadows are a
          // translucent warm grey-blue rather than black, highlights barely lift the tint.
          id: 'hillshade', type: 'hillshade', source: 'dem',
          paint: {
            'hillshade-method': 'multidirectional',
            'hillshade-illumination-direction': [335, 285, 25],
            'hillshade-illumination-altitude': [42, 50, 50],
            'hillshade-highlight-color': ['rgba(255,252,244,0.38)', 'rgba(255,252,244,0.10)', 'rgba(255,252,244,0.10)'],
            'hillshade-shadow-color': ['rgba(78,84,104,0.62)', 'rgba(92,98,116,0.20)', 'rgba(92,98,116,0.20)'],
            'hillshade-exaggeration': 0.5,
          },
        },
      ],
    };
  }

  // ---------- overlays ----------
  function applyProbe(d: DataProbe) {
    const note = (id: string, ok: boolean, meta: Meta | null) => {
      if (ok) { available.add(id); if (meta) metas.set(id, meta); }
      else console.info(`[terrain] ${id}: data not found, layer stays off`);
    };
    geologyTiles = d.geologyTiles;
    geologyMeta = d.geologyMeta;
    geologyCoverage = d.geologyCoverage;
    geologyGaps = d.geologyGaps;
    for (const s of d.geologyMeta?.sources ?? []) {
      const den = scaleDenominator(s.scale);
      if (den && den > COARSE_ABOVE) coarseSources.set(s.dataset_id, { name: sourceName(s.dataset_id, s.title), scale: `1:${new Intl.NumberFormat(locale).format(den)}` });
    }
    note(ID.GEOLOGY, !!d.geologyTiles, d.geologyMeta);
    note(ID.LOCALITIES, d.localities, d.localitiesMeta);
    OVERLAYS.forEach((o, i) => note(o.id, d.overlays[i].ok, d.overlays[i].meta));
    note(ID.ICE, !!d.iceIndex?.ages_ka?.length && !!d.iceIndex.path_pattern, d.iceMeta);
  }

  function installGeology() {
    const m = map!;
    const tj = geologyTiles!;
    m.addSource('geology', {
      type: 'vector',
      tiles: [tj.tiles],
      minzoom: tj.minzoom,
      maxzoom: tj.maxzoom,
      bounds: tj.bounds,
      promoteId: { units: 'unit_name' },
    });
    addOrdered({
      id: 'geology-fill', type: 'fill', source: 'geology', 'source-layer': 'units',
      paint: {
        'fill-color': geologyFillColorExpression() as never,
        'fill-opacity': geologyFillOpacity() as never,
        'fill-antialias': true,
      },
    });
    // Unit boundaries at low zoom show only around focused/emphasised units (a crisp edge so
    // an emphasis reads without a flat saturated block); at high zoom every unit gets a
    // hairline, a hovered unit a firmer edge.
    addOrdered({
      id: 'geology-line', type: 'line', source: 'geology', 'source-layer': 'units',
      paint: {
        'line-color': '#3d352c',
        'line-width': geologyLineWidth() as never,
        'line-opacity': geologyLineOpacity() as never,
      },
    });
    if (geologyGaps) {
      const img = m.hasImage('tg-hatch') ? null : hatchPattern();
      if (img) m.addImage('tg-hatch', img, { pixelRatio: 2 });
      m.addSource('geology-gaps', { type: 'geojson', data: `${dataBase}/terrain/${geologyGaps}` });
      addOrdered({
        id: 'geology-gaps', type: 'fill', source: 'geology-gaps',
        filter: GAP_HATCH_FILTER as never,
        paint: { 'fill-pattern': 'tg-hatch', 'fill-opacity': OPACITY['geology-gaps'][1] },
      });
      m.on('mousemove', 'geology-gaps', (e) => {
        if (hoveredUnit != null) return;
        m.getCanvas().style.cursor = 'help';
        showPopup('gap', e.lngLat, gapHtml);
      });
      m.on('mouseleave', 'geology-gaps', () => {
        if (popupFor !== 'gap') return;
        m.getCanvas().style.cursor = '';
        hidePopup();
      });
    }
    if (geologyCoverage) {
      m.addSource('geology-coverage', { type: 'geojson', data: `${dataBase}/terrain/${geologyCoverage}` });
      addOrdered({
        id: 'geology-coverage', type: 'line', source: 'geology-coverage',
        paint: { 'line-color': '#4a4238', 'line-width': zoomWidth(8, 0.8, 12, 1.4), 'line-opacity': OPACITY['geology-coverage'][1] },
      });
    }
    const meta = geologyMeta;
    const sourceInfo = (id: unknown) => {
      const s = meta?.sources?.find((x) => x.dataset_id === id);
      const den = scaleDenominator(s?.scale);
      const key = id == null ? '' : String(id);
      const name = key ? sourceName(key, s?.title) : null;
      return {
        label: name ? (den ? `${name} 1:${new Intl.NumberFormat(locale).format(den)}` : name) : null,
        attribution: s?.attribution ?? meta?.attribution ?? null,
      };
    };
    const setHover = (name: string | null) => {
      if (name === hoveredUnit) return;
      if (hoveredUnit != null) m.setFeatureState({ source: 'geology', sourceLayer: 'units', id: hoveredUnit }, { hover: false });
      hoveredUnit = name;
      if (name != null) m.setFeatureState({ source: 'geology', sourceLayer: 'units', id: name }, { hover: true });
    };
    const unitHtml = (p: Record<string, unknown>, name: string | null) => {
      const ageMin = typeof p.age_min_ma === 'number' ? p.age_min_ma : null;
      const ageMax = typeof p.age_max_ma === 'number' ? p.age_max_ma : null;
      const basisKind = typeof p.age_basis === 'string' ? p.age_basis : null;
      // withheld: the source states an age that this site does not use for colour; the source text stays in age_label
      const withheld = basisKind === 'withheld';
      const range = withheld ? null : ageMin != null && ageMax != null ? rangeText(ageMax, ageMin)
        : (ageMin ?? ageMax) != null ? ageOne((ageMin ?? ageMax)!) : null;
      // no age string in the source record: name the interval only where the chart boundaries match exactly
      const derived = !withheld && !p.age_label && ageMin != null && ageMax != null ? rangeName(ageMax, ageMin) : null;
      const reason = withheld && typeof p.age_withheld_reason === 'string' ? S(`geology_popup.withheld_reason.${p.age_withheld_reason}`, '') : '';
      const withheldLine = !withheld ? '' : reason
        ? fill(S('geology_popup.withheld', 'Not used for colour: {reason}.'), { reason })
        : S('geology_popup.withheld_plain', 'Not used for colour.');
      const basis = basisKind && basisKind !== 'none' && !withheld ? S(`geology_popup.basis.${basisKind}`, '') : '';
      // "not given" only when the source gives no usable age ('none'), or on older tiles without age_basis
      const noAge = basisKind === 'none' || (basisKind == null && !p.age_label && !range);
      const dated = isDatedColor(p.color);
      const src = sourceInfo(p.source);
      const rows = [
        p.unit_code ? `<div class="tg-pop-row">${esc(p.unit_code)}</div>` : '',
        p.lithology ? `<div class="tg-pop-row">${esc(p.lithology)}</div>` : '',
        p.age_label ? `<div class="tg-pop-row">${esc(p.age_label)}</div>` : '',
        derived ? `<div class="tg-pop-row">${esc(derived)}</div>` : '',
        range ? `<div class="tg-pop-row">${esc(range)} <span class="tg-pop-note">${esc(S('geology_popup.ics_bounds', 'ICS chart bounds'))}</span></div>` : '',
        basis ? `<div class="tg-pop-note">${esc(basis)}</div>` : '',
        withheldLine ? `<div class="tg-pop-muted">${esc(withheldLine)}</div>` : '',
        noAge ? `<div class="tg-pop-muted">${esc(S('geology_popup.age_not_given', 'Age not given in the source map'))}</div>` : '',
        src.label ? `<div class="tg-pop-row">${esc(src.label)}</div>` : '',
      ].join('');
      const swatch = `<span class="tg-pop-swatch" style="background:${esc(dated ? p.color : GEOLOGY_UNDATED_FILL)}"></span>`;
      // the honesty label the chapter declares for this layer; the dataset meta label only as a fallback
      const label = wanted.get(ID.GEOLOGY)?.label ?? meta?.label ?? 'interpreted';
      return `<div class="tg-pop-title">${swatch}${esc(name ?? S('geology_popup.unnamed', 'Unnamed unit'))}</div>${rows}`
        + `<span class="tg-pop-badge">${esc(S(`label.${label}`, label))}</span>`
        + (src.attribution ? `<div class="tg-pop-src">${esc(src.attribution)}</div>` : '');
    };
    m.on('mousemove', 'geology-fill', (e) => {
      const f = e.features?.[0];
      if (!f) return;
      const p = f.properties ?? {};
      const name = p.unit_name == null ? null : String(p.unit_name);
      m.getCanvas().style.cursor = 'help';
      setHover(name);
      showPopup(`unit:${name}`, e.lngLat, () => unitHtml(p, name));
    });
    m.on('mouseleave', 'geology-fill', () => {
      m.getCanvas().style.cursor = '';
      setHover(null);
      hidePopup();
    });
    // Touch has no hover: a tap (or click) opens the same popup, a tap elsewhere closes it.
    m.on('click', (e) => {
      const layers = ['geology-fill', 'geology-gaps'].filter((l) => m.getLayer(l) && m.getLayoutProperty(l, 'visibility') === 'visible');
      const hits = layers.length ? m.queryRenderedFeatures(e.point, { layers }) : [];
      const unit = hits.find((h) => h.layer.id === 'geology-fill');
      const gap = hits.find((h) => h.layer.id === 'geology-gaps');
      if (unit) {
        const p = unit.properties ?? {};
        const name = p.unit_name == null ? null : String(p.unit_name);
        setHover(name);
        showPopup(`unit:${name}`, e.lngLat, () => unitHtml(p, name));
      } else if (gap) {
        setHover(null);
        showPopup('gap', e.lngLat, gapHtml);
      } else clearGeologyHover();
    });
  }

  async function installOverlay(o: GeoJsonOverlay) {
    const url = `${dataBase}/terrain/${o.file}.geojson`;
    let data: string | GeoCollection = url;
    if (o.transform) {
      const fc = await fetchJson<GeoCollection>(url);
      if (!fc || !map) return;
      data = o.transform(fc);
    }
    map!.addSource(o.id, { type: 'geojson', data: data as never, tolerance: 0.5 });
    for (const l of o.layers) addOrdered(l);
  }

  async function installLocalities() {
    const fc = await fetchJson<GeoCollection>(`${dataBase}/terrain/localities.geojson`);
    for (const f of fc?.features ?? []) {
      if (f.geometry?.type !== 'Point') continue;
      const el = document.createElement('div');
      el.className = 'tg-marker';
      const name = String(f.properties?.name ?? f.properties?.id ?? '');
      el.innerHTML = `<span class="tg-marker-dot"></span><span class="tg-marker-label">${esc(name)}</span>`;
      el.dataset.kind = String(f.properties?.kind ?? '');
      el.setAttribute('aria-label', name);
      markers.push(new maplibregl.Marker({ element: el, anchor: 'left', offset: [-5, 0] })
        .setLngLat(f.geometry.coordinates as Position));
    }
  }

  /** Add sources/layers for a dataset the first time it is requested. */
  function ensureInstalled(id: string): Promise<void> {
    if (!available.has(id) || !map) return Promise.resolve();
    let p = installed.get(id);
    if (!p) {
      if (id === ID.GEOLOGY) p = Promise.resolve(installGeology());
      else if (id === ID.LOCALITIES) p = installLocalities();
      else {
        const o = OVERLAYS.find((x) => x.id === id);
        p = o ? installOverlay(o) : Promise.resolve();
      }
      installed.set(id, p);
    }
    return p;
  }

  // ---------- state ----------
  async function applyLayers(refs: LayerRef[]) {
    const next = new Map<string, LayerRef>();
    for (const r of refs) {
      if (KNOWN.has(r.id)) next.set(canonical(r.id), r);
      else console.info(`[terrain] unknown layer id "${r.id}" ignored`);
    }
    wanted = next;
    if (!map) return;
    await Promise.all([...next.keys()].map(ensureInstalled));
    if (!map || wanted !== next) return;
    const op = (id: string) => next.get(id)?.opacity ?? 1;
    const on = (id: string) => next.has(id) && available.has(id);

    const demOn = next.has(ID.DEM);
    show('color-relief', demOn, op(ID.DEM));
    show('hillshade', demOn, op(ID.DEM));
    show('geology-fill', on(ID.GEOLOGY), op(ID.GEOLOGY));
    show('geology-line', on(ID.GEOLOGY), op(ID.GEOLOGY));
    show('geology-gaps', on(ID.GEOLOGY), op(ID.GEOLOGY));
    // with a gaps layer the hatch explains unmapped areas (and the key shows its swatch, not the edge);
    // the source outline would add unexplained lines along the thin seams
    show('geology-coverage', on(ID.GEOLOGY) && !map.getLayer('geology-gaps'), op(ID.GEOLOGY));
    for (const o of OVERLAYS) for (const l of o.layers) show(l.id, on(o.id), op(o.id));
    if (!on(ID.GEOLOGY)) { hidePopup(); publishKey(null); } else keyDirty = true;
    if (ice) {
      ice.setVisible(on(ID.ICE) && iceInRange());
      ice.setOpacity(op(ID.ICE));
    }
    for (const mk of markers) {
      if (on(ID.LOCALITIES)) mk.addTo(map); else mk.remove();
    }
    // Visibility/paint changes do not invalidate the terrain render-to-texture cache.
    map.terrain?.tileManager.releaseAllRTT();
    map.triggerRepaint();
    emit();
  }

  function toKa(unit: TimeUnit, value: number) { return unit === 'ka' ? value : value * 1000; }
  function iceInRange(): boolean {
    if (!ice || !lastTime) return false;
    const [lo, hi] = ice.range;
    const ka = toKa(lastTime.unit, lastTime.value);
    return ka >= lo - 0.5 && ka <= hi + 1;
  }
  function applyTime(unit: TimeUnit, value: number): Promise<void> {
    lastTime = { unit, value };
    if (!ice) return Promise.resolve();
    const visible = wanted.has(ID.ICE) && available.has(ID.ICE) && iceInRange();
    ice.setVisible(visible);
    return visible ? ice.setTime(toKa(unit, value)) : Promise.resolve();
  }

  function whenIdle(): Promise<void> {
    return new Promise((resolve) => {
      if (!map || (map.loaded() && map.areTilesLoaded())) return resolve();
      map.once('idle', () => resolve());
    });
  }

  function moveCamera(camera: TerrainCamera, durationMs: number, easing: (t: number) => number) {
    if (!map) return;
    const opts = {
      center: [camera.lon, camera.lat] as Position,
      zoom: camera.zoom,
      pitch: Math.min(75, Math.max(0, camera.pitch)),
      bearing: camera.bearing,
    };
    // a user's zoom or its inertia must not cancel or bend the story's flight
    map.stop();
    if (durationMs <= 0 || reduceMotion) map.jumpTo(opts);
    else map.easeTo({ ...opts, duration: durationMs, easing, essential: true });
  }

  // ---------- engine ----------
  const engine: TerrainEngine = {
    kind: 'terrain',

    async mount(el) {
      container = el;
      if (!document.getElementById('tg-engine-css')) {
        const style = document.createElement('style');
        style.id = 'tg-engine-css';
        style.textContent = ENGINE_CSS;
        document.head.appendChild(style);
      }
      if (!workerConfigured) {
        maplibregl.setWorkerUrl(workerUrl);
        workerConfigured = true;
      }
      const [t, probe] = await Promise.all([detectTerrain(dataBase), probeData(dataBase)]);
      terrain = t;
      metas.set(ID.DEM, { attribution: t.attribution, label: t.fallback ? 'observed, stand-in' : t.label });
      available.add(ID.DEM);
      applyProbe(probe);
      if (disposed) return;
      const [w, s, e, n] = t.bounds;
      // Wider max bounds so a whole-region zoom-out no longer hits background; the DEM
      // still stops at [w,s,e,n], but the atmospheric fade in the sky settings keeps its
      // edge from cutting hard against the page. minZoom drops to 6.5 for the same reason.
      const mx = (e - w) * 0.5, my = (n - s) * 0.5;
      map = new maplibregl.Map({
        container: el,
        style: buildStyle(t),
        center: [(w + e) / 2, (s + n) / 2],
        zoom: 8.3,
        pitch: 45,
        minZoom: 6.5,
        maxZoom: t.maxzoom,
        maxPitch: 75,
        maxBounds: [[w - mx, s - my], [e + mx, n + my]],
        renderWorldCopies: false,
        pixelRatio: Math.min(window.devicePixelRatio || 1, 2),
        canvasContextAttributes: { antialias: false },
        fadeDuration: 0,
        attributionControl: false,
        refreshExpiredTiles: false,
        maxTileCacheSize: 300,
        // The wheel scrolls the story and Ctrl/⌘ + wheel zooms; on touch one finger scrolls the page, two move the map.
        cooperativeGestures: true,
        locale: {
          'CooperativeGesturesHandler.WindowsHelpText': S('map_hint.wheel_windows', 'Use Ctrl + scroll to zoom the map'),
          'CooperativeGesturesHandler.MacHelpText': S('map_hint.wheel_mac', 'Use ⌘ + scroll to zoom the map'),
          'CooperativeGesturesHandler.MobileHelpText': S('map_hint.touch', 'Use two fingers to move the map'),
        },
      });
      map.on('dataloading', () => setLoading(true));
      map.on('idle', () => {
        setLoading(false);
        if (keyDirty) scheduleKey();
      });
      map.on('moveend', () => { keyDirty = true; });
      // a story camera flight (no originalEvent) moves the terrain away under the popup and the highlight
      map.on('movestart', (ev) => { if (!(ev as { originalEvent?: unknown }).originalEvent) clearGeologyHover(); });
      map.on('sourcedata', (ev) => { if (ev.sourceId === 'geology' && ev.tile) keyDirty = true; });
      map.on('error', (ev) => console.warn('[terrain] map error:', ev.error?.message ?? ev));
      applyLock();
      await new Promise<void>((resolve) => map!.once('load', () => resolve()));
      if (disposed || !map) return;
      if (probe.iceIndex && available.has(ID.ICE)) ice = new IceManager(map, dataBase, probe.iceIndex, beforeId('ice-b'));
      mounted = true;
      await applyLayers([...wanted.values()]);
      if (lastTime) void applyTime(lastTime.unit, lastTime.value);
      emit();
    },

    async setState(state: SceneState) {
      lastTime = state.time;
      clearGeologyHover();
      const nextEmphasis = state.emphasis ?? null;
      if (nextEmphasis?.start_ma !== emphasis?.start_ma || nextEmphasis?.end_ma !== emphasis?.end_ma) {
        emphasis = nextEmphasis;
        refreshGeologyPaint();
      }
      const layersDone = applyLayers(state.layers);
      if (!mounted || !map) return;
      if (state.camera.terrain) {
        // First show: jump. Right after a view switch: a shorter ease-out that settles as the
        // crossfade completes. Same view: a longer ease-in-out flight.
        const switched = performance.now() - resumedAt < 400;
        const d = !cameraApplied ? 0 : switched ? CAMERA_AFTER_SWITCH_MS : CAMERA_MS;
        cameraApplied = true;
        moveCamera(state.camera.terrain, d, switched ? easeOutCubic : easeInOutCubic);
      }
      await layersDone;
      await Promise.all([applyTime(state.time.unit, state.time.value), whenIdle()]);
    },

    setTime(unit, value) {
      if (!mounted) { lastTime = { unit, value }; return; }
      if (lastTime && lastTime.unit === unit && lastTime.value === value) return;
      void applyTime(unit, value);
    },

    setCamera(camera: GlobeCamera | TerrainCamera, durationMs = 800) {
      if (!('zoom' in camera)) return;
      moveCamera(camera, durationMs, easeInOutCubic);
    },

    async preload(state: SceneState) {
      const jobs: Promise<unknown>[] = [];
      for (const r of state.layers) {
        if (KNOWN.has(r.id) && r.id !== ID.LOCALITIES) jobs.push(ensureInstalled(canonical(r.id)));
      }
      if (ice) jobs.push(ice.preload(toKa(state.time.unit, state.time.value)));
      await Promise.all(jobs);
    },

    pause() {
      paused = true;
      // leaving the terrain view (e.g. for the globe) must not leave a popup or highlight behind
      clearGeologyHover();
      map?.stop();
      if (container) container.style.visibility = 'hidden';
    },

    resume() {
      if (paused) resumedAt = performance.now();
      paused = false;
      if (container) container.style.visibility = '';
      map?.resize();
    },

    onStatus(cb) {
      listeners.add(cb);
      cb({ loading, attributions: attributions() });
      return () => { listeners.delete(cb); };
    },

    resize() { map?.resize(); },

    dispose() {
      disposed = true;
      hidePopup();
      markers.forEach((mk) => mk.remove());
      ice?.dispose();
      map?.remove();
      map = null;
      ice = null;
      listeners.clear();
      keyListeners.clear();
    },

    setExaggeration(value) {
      exaggeration = Math.max(0, value);
      map?.setTerrain({ source: 'dem-terrain', exaggeration });
    },
    setLock(lock) { locked = lock; applyLock(); },
    getTerrainInfo: () => terrain,
    getIceRange: () => ice?.range ?? null,
    getMap: () => map,

    setGeologyFocus(next) {
      const sig = (f: GeologyFocus | null) => JSON.stringify(f);
      if (sig(next) === sig(focus)) return;
      focus = next;
      refreshGeologyPaint();
    },

    onGeologyKey(cb) {
      keyListeners.add(cb);
      cb(lastKey);
      keyDirty = true;
      if (map?.loaded()) scheduleKey();
      return () => { keyListeners.delete(cb); };
    },
  };
  return engine;
}
