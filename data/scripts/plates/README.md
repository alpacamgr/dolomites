# Plates pipeline

Builds per-age reconstructed geometry for the globe view from a single plate
model for 0-300 Ma: **Scotese and Wright 2018 / PALEOMAP** (gplately
PlateModelManager name `scotese_and_wright2018`; manifest
`data/manifests/scotese-wright-2018-model.yaml`).

## Why this model

The globe's paleogeography textures are the PALEOMAP PaleoDEMs (Scotese and
Wright 2018), which are built in the PALEOMAP reference frame. The first build
used Muller 2019 (mantle frame) plus Matthews 2016; its outlines missed the
painted continents by about ten degrees of latitude at 240 Ma and jumped 7
degrees at the 250 Ma model switch. Using the PALEOMAP plate model for every
vector layer puts raster and vectors in the same frame by construction and
removes the switch. Decision record: `docs/decisions/0005-globe-reference-frame.md`.
The Muller 2019 and Matthews 2016 manifests stay, marked `superseded_for: globe`.

Outputs (all relative to the repo root):
- `app/public/data/globe/plates/{0..300}.json` - per-age GeoJSON (contract 1.2)
- `app/public/data/globe/plates/index.json` - age index (contract 1.2)
- `app/public/data/globe/plates/meta.json` - dataset metadata, attribution,
  citation, caveats
- `app/public/data/globe/dolomites-path.json` - Dolomites paleoposition track
  (contract 1.3)
- `data/processed/plates/preview/{age}Ma.png` - diagnostic Mollweide previews
- `data/processed/plates/preview/overlay_{age}.png` - frame check: landmass
  outline (thick magenta), continent block edges (faint red) and Dolomites
  marker on the 2k PaleoDEM texture (20, 100, 240 Ma)

## How to run

The interpreter is the project venv at `E:/Projects/Dolomites/.venv`
(ignore the PyGMT import error gplately prints).

```bash
# 1. Download the model (idempotent - reuses cached layers) into
#    data/raw/scotese-wright-2018-model/ and rewrite checksums.txt
E:/Projects/Dolomites/.venv/Scripts/python.exe data/scripts/plates/download.py

# 2. Build all 301 per-age JSON files, index.json, meta.json and
#    dolomites-path.json. Skips existing per-age files unless FORCE_REBUILD=1.
#    Prints the size range and the Dolomites paleolatitude table at the end.
FORCE_REBUILD=1 E:/Projects/Dolomites/.venv/Scripts/python.exe data/scripts/plates/build.py

# 3. Mollweide previews (0, 50, 100, 150, 200, 240, 280, 300 Ma) and
#    texture overlays (240, 100, 20 Ma). Needs the 2k textures.
E:/Projects/Dolomites/.venv/Scripts/python.exe data/scripts/plates/preview.py
```

After a model or texture change, open the three `overlay_{age}.png` files: the
red outlines must follow the painted land and shelf edges. If they do not,
check the layer, the frame and lon/lat order before shipping anything.
The magenta landmass line must trace the outer land edge without a web of
interior block edges.

## Design notes

- Layers: continents from `ContinentalPolygons`; boundaries from the shared
  sub-segments of `Topologies` resolved at each age; the Dolomites point is
  partitioned with `StaticPolygons`. In this model `StaticPolygons`,
  `ContinentalPolygons` and `COBs` are the same file and there is no
  `Coastlines` layer, so no `coastline` features are emitted.
- `landmass` (contract 1.2, added 2026-09-12): one MultiPolygon per age, the
  `unary_union` of all reconstructed continental polygons after the
  antimeridian split, closed by 0.5 deg (`buffer(+0.5).buffer(-0.5)`, mitre
  joins, clipped to the world box) to fill the thin gaps the model leaves
  between blocks, interior holes under 0.5 deg^2 filled, simplified at
  0.1 deg (`preserve_topology=True`) and snapped to the 0.001 deg output grid
  (`shapely.set_precision`) so rounding cannot make it self-intersect. Parts
  under 2 deg^2 are dropped unless
  they touch lon +-180, so both sides of an antimeridian cut survive. It is
  the outer outline the globe draws by default; `continent` block edges are
  the optional detail layer.
  - The closing step is not in the contract text; it was added because the
    plain union left a web of sliver lines inside Pangea. Gaps wider than
    about 1 deg between blocks still show as interior loops or notches (for
    example inside Pangea at 240 Ma, Tibet at 20 Ma). Filling all holes or a
    larger closing distance would remove more of them, but would also close
    real seaways and merge islands.
  - Rings keep cut edges along lon +-180 (land crossing the antimeridian) and
    lat +-90 (land covering a pole); a renderer stroking the outline should
    skip those segments.
  - `continent` features are not snapped (unchanged code); about 166 of them
    across the 301 files are slightly invalid (ring self-intersections from
    3-decimal rounding). Renderers that triangulate them should tolerate that.
- Boundary `type` comes from the GPML feature type: SubductionZone ->
  subduction, MidOceanRidge -> ridge, Transform/FractureZone -> transform,
  everything else -> other. The model has no subduction polarity property,
  so `polarity` is always `unknown`. The model's topologies only cover
  0-100 Ma (no topology feature exists before 100 Ma), so the per-age files
  for 101-300 Ma contain no `boundary` features.
- The Dolomites reference point (46.5 N, 11.8 E) falls on plate id 307
  (rotation file label `ITL-AFR`) and is carried passively by that plate.
  Its paleolatitude is model-dependent (7.3 N at 240 Ma here; see ADR 0005
  and `meta.json` for the comparison with other models and paleomagnetic data).
- Antimeridian splits use `pygplates.DateLineWrapper`. Continent polygons are
  dissolved per plate id (`shapely.ops.unary_union`), simplified with
  `preserve_topology=True` at 0.4 deg and dropped below 2 deg^2; boundary
  lines are simplified at 0.1 deg. Coordinates are rounded to 3 decimals.

## Idempotence and concurrent readers

- `download.py` calls `gplately.PlateModelManager.get_model()` which reuses
  layers already in the target dir. It always recomputes `checksums.txt`.
- `build.py` writes every JSON (per-age files, `index.json`, `meta.json`,
  `dolomites-path.json`) to a `.tmp` file and renames it into place, retrying
  if a reader holds the file, so the app never sees a half-written file. It
  skips existing per-age files unless `FORCE_REBUILD=1`; the index, meta and
  path files are always rewritten.
- `preview.py` overwrites its PNGs on every run and only reads the textures.
