# Globe textures pipeline

Builds equirectangular sphere textures for the whole-Earth globe, one per time
slice at 5 Myr intervals from 300 Ma to 0 Ma. All slices are rendered with the
same hypsometric-bathymetric palette and hillshade so the crossfade between
ages on the globe is seamless.

## Data sources

| Age | Source | Native res | Native format | Label |
|---:|---|---:|---|---|
| 0 Ma | NOAA ETOPO 2022, 60 arc-sec, ice-surface | 21600 x 10800 | netCDF-4 (`z` metres) | observed |
| 0 Ma | NOAA ETOPO 2022, 60 arc-sec, bedrock (ice-mask companion) | 21600 x 10800 | netCDF-4 (`z` metres) | observed |
| 5..300 Ma | Scotese & Wright 2018 PaleoDEM, 0.1 deg | 3601 x 1801 | netCDF-4 (`z` metres) | interpreted |

Manifests: `data/manifests/scotese-paleodem-2018-v2.yaml`,
`data/manifests/noaa-etopo2022-60s.yaml`. Real SHA-256 checksums are stored in
`data/raw/checksums.json` after `download.py` finishes.

## netCDF conventions we rely on

Verified via `inspect_nc.py`.

### PaleoDEM (Scotese & Wright 2018, 0.1 deg)

- Dimensions: `latitude` (1801), `longitude` (3601). Cell-centered including
  poles and antimeridian; last column duplicates first, last row is the south
  pole - both are dropped during render.
- `latitude` is **north-first**: 90.0 -> -90.0 in 0.1 deg steps.
- `longitude` runs -180.0 -> 180.0 in 0.1 deg steps.
- `z` is float32, metres, **negative below sea level**. No NaN in any file we
  checked; deep ocean is set to about -9000 m as a floor.
- The provider variable is called `z`; the descriptive attribute lives on the
  dataset (`description: PALEOMAP: <epoch>, <age> Ma`).

### ETOPO 2022 (NOAA NCEI, 60 arc-sec, ice-surface)

- Dimensions: `lat` (10800), `lon` (21600). Cell-centered, `node_offset=1`,
  so the outermost cell centre sits 30" inside the +/- 90 lat and +/- 180 lon
  bounds.
- `lat` is **south-first**: -89.99 -> 89.99. We flip to north-first during
  render to match the equirectangular convention.
- `lon` runs -180.0 -> 180.0.
- `z` is float32, metres relative to the EGM2008 geoid. This is the
  **ice-surface** variant, i.e. Greenland and Antarctica report the top of the
  ice, not bedrock.
- The **bedrock** companion (`..._bed.nc`) has the same grid and conventions;
  its `z` is the elevation of the underlying rock. Subtracting the two gives
  ice thickness in metres; cells with `thickness > 50 m` are treated as the
  0 Ma ice mask (ice sheets, including grounded ice and ice shelves).

## Palette

Design goals: print-atlas quality; muted; no cartoon greens; deep abyssal navy
that darkens uniformly; a sharp step at sea level between shelf blue and warm
sandy coastal; sage-olive lowlands through pale ochre and warm brown to grey
at 3500-4000 m and near-white above about 4800 m (snow-capped high plateaus).
Ice sheets at 0 Ma get their own tint (see below).

Stops (see `palette.py`):

- Ocean (`e <= 0`): -8000 -> `#071527`, -6000 -> `#0b213f`, -4000 -> `#123055`,
  -2000 -> `#1e3e63`, -1000 -> `#2b5079`, -500 -> `#456e94`, -200 -> `#6d94b8`,
  -50 -> `#95b4cf`, 0 -> `#b8d0e4`.
- Land (`e > 0`): 0 -> `#d6c8a3`, 100 -> `#a7b57e`, 500 -> `#8ba368`,
  1000 -> `#b6b378`, 1500 -> `#c9b483`, 2000 -> `#b48d5f`, 3000 -> `#8f6a48`,
  3500 -> `#a09a92`, 4000 -> `#c2bdb5`, 4800 -> `#eeece6`, 5000 -> `#ffffff`,
  6500 -> `#ffffff`. The tint reaches grey around 3500-4000 m and near-white
  by ~4800 m, so Tibet and the high Andes read as snow-capped.

At sea level the last ocean stop (pale coastal blue) and first land stop
(warm sand) sit at the same x, producing a single-cell hard step - this is
what makes the coastline read on the globe without an outline overlay.

Written to `index.json` under `palette.stops`.

## Ice tint (0 Ma only)

Antarctica and Greenland are shown as ice sheets, not as rock. At 0 Ma the
pipeline loads both the ETOPO 2022 ice-surface and bedrock grids, builds an
ice mask `(surface - bedrock) > 50 m` at the full 60" resolution, and paints
those cells with a dedicated pale blue-white gradient by surface elevation:

- 0 -> `#dfe9f1` (ice shelves and low margins)
- 1500 -> `#e7eef4`
- 3000 -> `#f0f5f9`
- 4500 -> `#f7fafc` (interior high plateau)

The same Horn hillshade is multiplied in at the same strength, so ice reads
with relief. The PaleoDEM has no bedrock companion, so paleo slices carry no
ice tint - the polar cover simply disappears between 0 and 5 Ma. This is
called out in `meta.json` under `caveats` and in `index.json` under
`modern.ice_mask`. A downsampled preview of the mask is written to
`data/processed/textures/ice_mask.png`.

## Hillshade

Horn algorithm, azimuth 315 deg, altitude 45 deg, in pixel-space with a
z-factor tuned so relief reads on the globe overview without being harsh
(~6x vertical exaggeration at equator). Latitude compression on `dz/dx` is
corrected by dividing by `cos(lat)`.

The hillshade is **multiply-blended** onto the palette at strength 0.6, so
flat areas keep the tint at ~40% brightness and steepest slopes drop to about
0% (in shadow) or hold at full brightness (in sun).

Polar guards (hillshade and normal map alike). The east-west pixel spacing
shrinks with `cos(lat)`, so near the poles `dz/dx / cos(lat)` explodes and
every column converging on the pole turns into a streak - a radial fan on the
globe. Two fixes: `cos(lat)` is clamped at `cos(85 deg)`, and between
|lat| 80 deg and the pole the hillshade is blended linearly toward its
flat-ground value (`cos(zenith)` = 0.707) while the normal-map relief is
blended toward the flat normal (0, 0, 1). Polar pixels therefore keep
flat-terrain brightness (no bright halo over Antarctica) without the streaks.
Nothing equatorward of 80 deg changes. Recorded in `index.json` as
`hillshade.cos_lat_min_deg`, `hillshade.polar_taper_deg` and
`hillshade.polar_taper_target`.

The PaleoDEM's own rows nearest the poles show longitudinal banding
(elevation varies by hundreds of metres along rows that converge on the pole),
so a faint radial fan remains around the pole on some paleo slices, e.g. the
240 Ma south pole. It is in the source data and is left as is.

All outputs (WebP and JSON) are written to `<name>.tmp` and renamed over the
target, so a running app never reads a half-written file.

## Normal maps

Written to `4k/{age}-normal.webp`. Encoded tangent-space normals: R = (nx+1)/2,
G = (ny+1)/2, B = (nz+1)/2. Height scale = 12000 m per pixel-width unit,
chosen so the resulting bumps look subtle on the globe.

## Output layout (per contract `docs/04-data-contracts.md` section 1.1)

```
app/public/data/globe/textures/
  index.json                 # ages, sizes, palette, hillshade params
  meta.json                  # dataset id, labels, attribution, license, caveats
  4k/{0,5,...,300}.webp             # RGB 4096x2048, WebP q85
  4k/{0,5,...,300}-normal.webp      # normal map 4096x2048, WebP q85
  2k/{0,5,...,300}.webp             # RGB 2048x1024, WebP q85
```

## How to run

```
python data/scripts/textures/download.py     # downloads + verifies + extracts
python data/scripts/textures/inspect_nc.py   # prints conventions as JSON
python data/scripts/textures/render.py       # renders all 61 slices (idempotent)
python data/scripts/textures/render.py --only 0,5,100   # a subset
python data/scripts/textures/render.py --force          # regenerate
python data/scripts/textures/preview.py      # contact sheet + full previews (0, 5, 240 Ma) + size totals
```

All scripts run against the project venv at `E:/Projects/Dolomites/.venv/`.
They are idempotent: `download.py` skips completed files, `render.py` skips
slices whose outputs already exist unless `--force`.
