# 02 - Architecture proposal

Status: accepted for v0.1 (2026-09-06). The rendering and site stack is fixed in [decisions/0004-rendering-and-site-stack.md](decisions/0004-rendering-and-site-stack.md) with registry-verified versions; the file formats between pipeline and app are fixed in [04-data-contracts.md](04-data-contracts.md). Scope note: the globe chapters cover the whole Earth (the plate models and PaleoDEM are global); the terrain chapters cover the Dolomites.

## Principles

1. **Static site, no backend.** All data is precomputed into files a browser can fetch directly. This keeps hosting cheap and the site archivable.
2. **Scenes are data, not code.** Each chapter in `content/timeline/*.yaml` declares which layers are visible, at what time, with which camera. The app is a player for that description.
3. **Every layer carries its honesty label and source id** in the scene description, and the legend renders both. A layer without a label cannot be declared.
4. **Coarse data stays coarse.** The plate chapters run on a globe or regional view; the Dolomites chapters run on high-resolution terrain. The app never zooms a 10 km-cell paleogeography raster to street level.
5. **Multilingual from the first commit.** German, Italian, English routes; content keyed by chapter id.

## Two views, one scroll

```
+-------------------------------------------------------------+
|  Narrative column (scrolls)   |  Stage (sticky)              |
|                               |                              |
|  Chapter text, facts with     |  A) Globe / regional view    |
|  citations, honesty badges    |     plate chapters, coarse   |
|                               |  B) Terrain view             |
|  Time axis + paleolatitude +  |     Dolomites chapters, fine |
|  climate curve (sticky rail)  |                              |
+-------------------------------------------------------------+
```

**Globe / regional view (A)** shows reconstructed continent outlines, plate boundaries, and, as a labeled interpretive background, Scotese PaleoDEM paleogeography at 5 Myr steps. A marker tracks the future Dolomites. Chapters: Permian to Paleogene.

**Terrain view (B)** shows present-day terrain (TINITALY 10 m or the Bolzano 2.5 m DTM where licensed) with switchable overlays: geological units, faults, glacier outlines, the Seguinot ice-thickness frames, GSSP and geosite markers, restored sketch maps. Chapters: Triassic detail, Alpine uplift, glaciation, today.

The scroll position drives a single `time` value. Chapters can pause time to explain, then resume.

## Data pipeline (Python, in `data/scripts/`)

| Input (manifest id) | Tool | Output in `data/processed/` | Label |
|---|---|---|---|
| Scotese and Wright 2018 PALEOMAP plate model (rotations, polygons, topologies; see ADR 0005) | gplately / pygplates | GeoJSON per time step (1 Myr, 300-0 Ma): continent polygons, plate boundaries, position of a Dolomites reference point, paleolatitude | modeled |
| Scotese PaleoDEM 0.1 deg NetCDF (5 Myr steps) | xarray, rasterio | One PNG or COG per time slice, regional extent, no upsampling | interpreted |
| TINITALY 10 m, Copernicus GLO-30 | rasterio, Pillow, pmtiles, export_tiles.py | Terrain-RGB tiles: PMTiles intermediate, shipped as lossless WebP `{z}/{x}/{y}` + TileJSON | observed |
| South Tyrol CARG geology (CC0), Trentino PAT geology (CC BY 4.0), Veneto lithology 1:250,000 (IODL 2.0) | shapely, mapbox-vector-tile, pmtiles, export_tiles.py | Merged vector tiles of geological units with ICS ages and colours, shipped as raw MVT `{z}/{x}/{y}` + TileJSON, plus a coverage outline | observed |
| Seguinot 2018 continuous NetCDF (1 km, 1 kyr snapshots) | xarray | Ice-thickness PNG frames clipped to the Alps bbox, 120-0 ka; a JSON index | modeled |
| RGI 7.0, Reinthaler & Paul 2025 LIA outlines, GLACIMONTIS LGM extent | ogr2ogr | GeoJSON | observed / interpreted |
| PhanDA, CENOGRID, Spratt & Lisiecki, Sanchez 2018 velocities | pandas | Small JSON curves for the side rail | modeled / observed |
| ICS chart | manual | `content/ics-chart.json` with stage boundaries and colors | reference |

Every output file name embeds the manifest id, and every script writes the checksum back into the manifest.

## Rendering stack (decided, see ADR 0004)

- **Map engines:** three.js for the whole-Earth globe (ADR 0004) and MapLibre GL JS for the Dolomites terrain, with raster-dem terrain, hillshade and colour relief.
- **Time-varying rasters** (paleogeography slices, ice frames): two textures or image sources crossfaded per time step. The crossfade is presentation only and is documented as such in the legend.
- **Scroll control:** IntersectionObserver-based steps (Scrollama or equivalent) mapping chapter progress to `time`.
- **Site framework:** Astro static output with built-in i18n routing; the map is one island component.
- **Hosting:** everything static as Cloudflare Workers static assets, deployed by Workers Builds from github.com/alpacamgr/dolomites (ADR 0006, amended). Map tiles are exported from PMTiles build intermediates into individual `{z}/{x}/{y}` files with TileJSON descriptors: terrain as lossless WebP at the source's 0.1 m precision, geology as raw MVT compressed at the edge. No object storage, no Worker script.

Alternatives considered: CesiumJS gives true 3D and time-dynamic layers out of the box but is heavier and pushes toward Cesium Ion terms; three.js gives full control at the cost of building terrain streaming ourselves. Either can replace the map engine without changing the data pipeline or content schema, which is the point of principle 2.

## Content schema

See `content/README.md`. The scene description adds to each chapter:

```yaml
scene:
  view: globe | terrain
  time_ma: 237.0            # or time_ka for Quaternary chapters
  camera: { lon: 11.8, lat: 46.5, zoom: 9, pitch: 60, bearing: 20 }
  layers:
    - id: earthbyte-muller2019-continents
      label: modeled
      source_ref: muller-2019
      style: outline
```

A validation script in `tools/` rejects any layer whose `id` has no manifest or whose `label` is missing.

## Decisions made since the proposal

1. Globe engine: three.js (ADR 0004); globe geometry and textures in the PALEOMAP frame (ADR 0005).
2. CARG vector data: no downloadable vector databases exist for the Dolomites sheets outside South Tyrol; Trentino and Veneto open maps are used instead (docs/04 section 2.2).
3. Terrain and data hosting: static tiles as Cloudflare Workers static assets (ADR 0006).
4. Still open: whether to include Ladin in the first release.
