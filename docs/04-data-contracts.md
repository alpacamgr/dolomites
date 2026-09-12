# 04 - Data contracts between pipeline and app

Status: accepted 2026-09-06. Pipeline scripts write exactly these files; the app reads exactly these files. Change this document first, then both sides.

All paths are relative to `app/public/data/`. All JSON is UTF-8, no BOM. Coordinates are WGS84 lon/lat unless stated. Ages: `ma` = million years before present (float), `ka` = thousand years before present (integer).

Every dataset directory contains a `meta.json` with: `dataset_id` (matches `data/manifests/<id>.yaml`), `label` (observed | modeled | interpreted | illustrative), `source_ref` (bibliography key), `attribution` (display string), `license`, `generated` (ISO date), and `script` (path of the generating script).

## 1. Globe

### 1.1 Paleogeography textures — `globe/textures/`

- `index.json`:
  ```json
  {
    "ages_ma": [0, 5, 10, "...", 300],
    "sizes": { "4k": [4096, 2048], "2k": [2048, 1024] },
    "format": "webp",
    "path_pattern": "globe/textures/{size}/{age}.webp",
    "modern": { "age_ma": 0, "dataset_id": "noaa-etopo2022-60s", "label": "observed" },
    "paleo": { "dataset_id": "scotese-paleodem-2018-v2", "label": "interpreted" },
    "palette": { "sea_level_m": 0, "stops": [[-8000, "#0b1d3a"], ["...", "..."]] }
  }
  ```
- `{size}/{age}.webp`: equirectangular, lon -180..180 left to right, lat 90..-90 top to bottom, hypsometric tint with hillshade multiplied in, no labels, no graticule, sRGB, quality 85. `age` is an integer in Ma with no padding (`0.webp`, `5.webp`, ...). The 0 Ma texture comes from ETOPO 2022; all others from the PaleoDEM, both rendered with the same palette and light direction so the crossfade to today is seamless.
- Optional `{size}/{age}-normal.webp`: tangent-space normal map derived from the same elevation, for lighting on the sphere.

### 1.2 Reconstructed geometry — `globe/plates/`

- `index.json`: `{ "ages_ma": [0, 1, 2, "...", 300], "path_pattern": "globe/plates/{age}.json", "model": "scotese_and_wright2018 (PALEOMAP frame)", "simplify_deg": 0.25 }`
- `{age}.json`: GeoJSON FeatureCollection, WGS84, polygons split at the antimeridian, coordinates rounded to 3 decimals. Feature `properties.kind` is one of:
  - `continent` (polygon; from the model's continental polygons), with `plate_id` (int) and `name` if the model has one;
  - `landmass` (polygon or multipolygon; the union of all `continent` polygons at that age, holes smaller than 0.5 deg^2 removed, simplified at 0.1 deg). Optional detail layer, off by default: the model's continental polygons mark continental crust, not shorelines, so they do not follow the painted coastline of the PaleoDEM texture (checked at 240, 100 and 20 Ma). The texture's sea-level colour step is the coastline the globe shows. Added 2026-09-12;
  - `coastline` (polygon or line; from the model's coastlines; absent in the PALEOMAP model);
  - `boundary` (line; from resolved topologies) with `type` in `subduction | ridge | transform | other` and, for subduction, `polarity` in `left | right | unknown`;
  - `dolomites` (point) with `lat`, `lon`, `paleolat`.
  Target size after simplification: under 200 kB per file.

### 1.3 Dolomites trajectory — `globe/dolomites-path.json`

`{ "reference_point": { "lat": 46.5, "lon": 11.8 }, "plate_id": 0, "model": "...", "samples": [ { "ma": 0, "lat": 46.5, "lon": 11.8 }, { "ma": 1, "lat": "...", "lon": "..." } ] }` for every integer Ma 0..300. `plate_id` is the plate that the reference point was assigned to at 0 Ma.

## 2. Terrain (Dolomites)

### 2.1 Elevation — served as `terrain/elevation/{z}/{x}/{y}.webp` + `terrain/elevation/tiles.json`

Served layout (ADR 0006, 2026-09-12): individual lossless WebP tiles under `terrain/elevation/`, described by a TileJSON 3.0 file `tiles.json` (`tiles: ["{base}/terrain/elevation/{z}/{x}/{y}.webp"]` with a path relative to the data base, plus `minzoom`, `maxzoom`, `bounds`, `attribution`, `encoding: "mapbox"`, `tileSize: 512`). Heights keep the 0.1 m Terrain-RGB precision; no rounding. The PMTiles archive `data/processed/terrain/dolomites-terrain.pmtiles` is the pipeline intermediate the tiles are exported from and is not shipped.

Tile properties: 512 px tiles, EPSG:3857, Mapbox Terrain-RGB encoding (`height = -10000 + (R * 65536 + G * 256 + B) * 0.1`), zoom 6 to 12 (512 px tiles at z12 give 13 m per pixel at 46.5 N, the finest level the 10 m source supports without upsampling), bounding box 10.3 E to 12.7 E, 45.8 N to 47.2 N. Source priority: TINITALY 10 m inside Italy, Copernicus GLO-30 for voids and areas outside Italy; both are recorded in meta.json. Metadata in the archive: `attribution`, `encoding: mapbox`, `minzoom`, `maxzoom`, `bounds`.

### 2.2 Geology — served as `terrain/geology/{z}/{x}/{y}.pbf` + `terrain/geology/tiles.json`

Served layout (ADR 0006): individual MVT tiles exported from `geology-dolomites.pmtiles` (pipeline intermediate in `data/processed/terrain/`), described by TileJSON `terrain/geology/tiles.json` with `vector_layers: [{ id: "units" }]`. Tiles are gzip-free raw MVT so any static host serves them without content-encoding configuration.

Coverage finding 2026-09-12: the CC0 South Tyrol layer contains only the province's published CARG sheets (66,133 features, equal to the server's numberMatched). It covers Schlern/Sciliar, Sella, Rosengarten, Seiser Alm, Geisler/Odle, Drei Zinnen and Prati di Stuores, but not Latemar, Marmolada, Bletterbach, Bolzano, Brixen, or anything in Trentino or Belluno.

Vector PMTiles (MVT), layer `units`, zoom 8 to 13, merged from every open vector geological map whose licence permits redistribution of derived tiles. Each feature carries `source` (dataset id). Priority, where a lower source only fills area that no higher source covers (so no area has double polygons): 1 `bz-geology-carg` South Tyrol CARG (CC0, 1:25,000 from 1:10,000 survey), 2 `pat-geology-carta-geologica` Trentino (CC BY 4.0, 1:10,000), 3 `veneto-litologia-250k` Veneto lithology (IODL 2.0, 1:250,000), 4 `swisstopo-geocover` swisstopo GeoCover (swisstopo OGD terms, 1:25,000; Swiss strip), 5 `ispra-geologia-100k-inspire` ISPRA Carta Geologica d'Italia 1:100,000 (CC BY 4.0; South Tyrol outside the CARG sheets, Lombardy and Friuli edges), 6 `geosphere-geologicunits-500k` GeoSphere Austria (CC BY 4.0, 1:500,000; Austria). The meta lists each source with `scale`, `scale_denominator` and a `scale_note` for maps coarser than 1:25,000, whose polygons must not be read as detailed mapping at z11-13.

Geometry (2026-09-12): all sources form one polygon coverage (boundaries noded together, each face given to the highest-priority polygon containing it), so neighbouring units share edges and no polygon is dropped. z13 is unsimplified; at z8-z12 units smaller than about one tile pixel are merged into the neighbour with the longest shared edge (the area stays covered and shows that neighbour's attributes) and the coverage is simplified topologically (`shapely.coverage_simplify`). Tiles are clipped with a 16/4096-unit buffer. `data/scripts/terrain/check_geology_tiles.py` samples random points on the served tiles and reports per zoom covered, dated, missing versus z13 and tile bytes; the meta embeds its before/after results under `verification.served_tiles_check`.

`terrain/geology-coverage.geojson`: one dissolved polygon per source (simplified 0.005 deg) with `source`, `attribution`, `license`, `scale`, `scale_denominator`, `label: interpreted`. The terrain view draws its outline so unmapped areas read as "no open vector geology" rather than as missing data.

`terrain/geology-gaps.geojson`: the terrain DEM bbox (bounds of `terrain/elevation/tiles.json`) minus the union of all source coverage, one Polygon feature per part (largest first) with `properties: { kind: "no_open_geology", area_km2, mean_width_m }`, where `mean_width_m` = 2 × area / perimeter in EPSG:25832 (rounded to 0.0001 km2 and 1 m). Thin parts are mostly seams along sheet and source borders; they are kept as gaps (neighbouring geology is not extended into them) so a viewer can style or filter them by `mean_width_m`. Slivers narrower than about 15-20 m (morphological opening, 0.0001 deg) and parts under about 800 m2 are omitted; simplified 0.0001 deg. The meta names the file under `coverage.gaps_file` and gives part counts and areas by width class under `coverage.gaps`.

Until the merged archive exists, `geology-suedtirol.pmtiles` stays in place with the same layer and properties. Properties: `unit_name`, `unit_code`, `age_min_ma` (younger bound) and `age_max_ma` (older bound), both in Ma, null unless the unit is dated; `age_label`, the source's own age text, present when `age_basis` is `source` or `withheld` and null otherwise; `age_basis`, one of `source` (dated with the age stated by the polygon's own map), `legend_join` (the map names formations without a usable age, dated by joining the formation names to another cited legend, envelope of their ages), `class_rule` (dated by a deposit-type rule with a cited basis, e.g. Veneto Quaternary deposit classes), `withheld` (the source states an age that this site does not use for colour) or `none` (the source gives no usable age: no age, water, ice, anthropic or unmappable ground); `age_withheld_reason`, only for `withheld` (else null), one of `metamorphic_event` (the stated age is a metamorphic, deformation or subduction event: ISPRA metamorphicProcess/faulting, GeoSphere subduction), `contradiction` (the source's attributes contradict each other: the per-unit ISPRA review by `data/scripts/terrain/review_ispra_100k_units.py`, swisstopo descriptions or legends that contradict the age fields), `young_bedrock` (ISPRA gives a Cenozoic or Quaternary age to volcanic, plutonic, dyke, metamorphic or lithified bedrock, e.g. the Bolzano porphyries as 'Cenozoic'), `unmappable_interval` (no ICS chart interval for the stated younger bound, e.g. 'Terziario (?)', 'frühes Paläozoikum', 'Unknown') or `open_range` (an age open on one side or spanning eons, e.g. 'pre-Permiano', Proterozoikum-Känozoikum); `lithology`; `color` (hex, official ICS colour of the younger interval of a dated unit; null for `withheld` and `none`); `source`. Numbers and colour of withheld units stay null. Ages are derived from the sources' stage names via the ICS chart and the mapping table `data/scripts/terrain/geology_age_mapping.json`, which lists the cited `authorities`, the evidence of every join and rule and the `age_basis_contract`; the maps themselves carry no numeric ages. The geology layer is labelled `interpreted` (docs/03): a geological map is drawn by researchers from field evidence, and its ages are derived by this project. Other provinces stay WMS overlays in v0.1, listed in `terrain/wms.json`.

### 2.3 Ice frames — `terrain/ice/`

- `index.json`: `{ "ages_ka": [120, 119, "...", 0], "path_pattern": "terrain/ice/{ka}.webp", "bounds": [minLon, minLat, maxLon, maxLat], "crs": "EPSG:3857", "size": [w, h], "thickness_size": [w, h], "native_resolution_m": 1000, "render_scale": 2, "encoding": "rgba-colorized", "thickness_stops_m": [[0, "transparent"], [50, "..."], "..."], "run": "alpcyc.1km.epica.pp", "resolution_m": 1000 }`
- `{ka}.webp`: lossless WebP, RGBA at twice the native 1 km model resolution (bilinear), already colorized and alpha-blended by thickness so the app can drop it into a MapLibre `image` source using `bounds` as the four corners (in lon/lat, but the image itself must be rendered in Web Mercator so it drapes correctly). Areas with thickness below 10 m are fully transparent.
- Also `thickness/{ka}.png`: 16-bit grayscale PNG (metres, 0..65535) at native 1 km resolution (`thickness_size`), same bounds, for numeric readouts. The app reads `path_pattern` and sizes from `index.json` and never hardcodes them.

### 2.4 Vector overlays — `terrain/`

- `glaciers-rgi7.geojson`: RGI 7.0 region 11 outlines clipped to the terrain bbox; `properties.name`, `area_km2`.
- `glaciers-lia.geojson`: Little Ice Age outlines (Reinthaler and Paul 2025) clipped; `properties.year_ref`.
- `lgm-extent.geojson`: LGM ice extent polygon(s) clipped to the Alps; source in `meta.json`.
- `faults.geojson`: DISS 3.3.1 sources clipped; `properties.name`, `type`.
- `localities.geojson`: hand-curated points from `content/localities.yaml` (GSSPs, geosites, viewpoints); `properties.id`, `kind`, `name`, `source_ref`. Built by `data/scripts/content/build_localities.py`; entries without `source_url` and `verified` are skipped. Metadata in `localities.meta.json`.

## 3. Curves — `curves/`

Each file: `{ "dataset_id": "...", "label": "modeled", "x": "ma" | "ka", "unit": "degC", "series": [ { "name": "gmst_p50", "values": [[x, y], ...] }, ... ] }` sorted by x descending (oldest first). Every file also carries `source_ref`, `attribution` (meeting the source licence, with "(modified: ...)" where values are derived), `license` and `license_url`.

- `phanda-gmst.json` (Judd et al. 2024; p05, p50, p95), `phanda-co2.json`
- `cenogrid-d18o.json` (Westerhold et al. 2020, benthic d18O, decimated to 10 kyr)
- `spratt-lisiecki-sealevel.json` (800 ka to 0)
- `alps2017-uplift.json`: a single number and grid cell for the Dolomites reference point, with uncertainty

## 4. Time axis — `ics-chart.json`

`{ "version": "ICS 2026/06", "source_ref": "ics-2026", "intervals": [ { "name": "Ladinian", "type": "age", "parent": "Middle Triassic", "start_ma": 241.464, "end_ma": 237.0, "color": "#B3A3C4" }, ... ] }` for eons, eras, periods, epochs, ages from 300 Ma to 0. Colors are the official ICS colors. Boundary ages copied from the chart itself.

## 5. Content — built from `content/` at build time

`content/timeline/*.yaml` (schema in `content/README.md`, plus the `scene` block below) is read by Astro at build time; no runtime YAML parsing. Scene block:

```yaml
scene:
  view: globe | terrain
  time:
    unit: ma | ka
    start: 300        # time at chapter entry
    end: 250          # time at chapter exit; scrolling interpolates linearly
  camera:
    globe:   { lat: 20, lon: 15, distance: 2.6 }                      # distance in Earth radii
    terrain: { lon: 11.8, lat: 46.5, zoom: 10, pitch: 60, bearing: 20 }
  layers:
    - { id: "scotese-paleodem-2018-v2", label: interpreted, source_ref: "scotese-2018" }
    - { id: "earthbyte-muller2019", label: modeled, source_ref: "muller-2019", style: "boundaries" }
```

Optional `emphasis` (added 2026-09-12): `emphasis: { age_start_ma: 247.0, age_end_ma: 237.0 }` (older bound first). The terrain view emphasises geological units whose mapped age range (`age_min_ma`..`age_max_ma`) lies entirely within the interval and dims the rest; the geology key names it "Rocks mapped as <interval>". Containment, not overlap, is deliberate: units with very wide envelopes (for example "Paleozoico (?) - Mesozoico (?)", 66-538.8 Ma) overlap almost any interval and would otherwise be painted as rocks of that age. Engines without age-coloured data ignore it.

`source_ref` on a layer (in `scene.layers` and `map_state.layers`) is a bibliography key or, for a layer merged from several sources, a list of keys (added 2026-09-12; a plain string stays valid). The legend shows the single short cite, or "n sources" linking to the Sources section with every short cite in its tooltip and accessible name; the Sources section lists every key.

## 6. Component API — `app/src/lib/scene-api.ts`

Both engines implement `SceneEngine` from that file. The story controller only talks to that interface.
