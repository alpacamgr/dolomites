# Quaternary & curves pipeline

Everything in this directory rebuilds the data under
`app/public/data/{terrain/ice, terrain/*.geojson, curves, ics-chart.json}`
from open, cited sources. Scripts are idempotent and resumable; re-running
them regenerates the outputs from the raw files in `data/raw/`.

## Run order

```
python download_seguinot.py         # 411 MB PISM run to data/raw/seguinot2018-alps-1km/
python download_glacimontis.py      # 130 MB shapefile archive to data/raw/glacimontis-2026/
python build_rgi7.py                # -> terrain/glaciers-rgi7.geojson (+meta.json)
python build_lia.py                 # -> terrain/glaciers-lia.geojson
python build_lgm_extent.py          # -> terrain/lgm-extent.geojson
python build_faults.py              # -> terrain/faults.geojson
python build_curves.py              # -> curves/*.json
python build_ics_chart.py           # -> ics-chart.json
python build_ice_frames.py          # -> terrain/ice/{ka}.png, thickness/{ka}.png, index.json, meta.json
```

`build_ice_frames.py` skips a `ka` that already has both PNGs unless
`FORCE=1` is set. It streams the NetCDF one snapshot at a time and holds
one 2048x1488 float array at a time; peak RSS is under a gigabyte.

Downloads for RGI 7.0 (5 MB), Reinthaler & Paul LIA (14 MB), DISS 3.3.1
(WFS GeoJSON, sub-MB), and the small curve text files are performed inline
by their build scripts' one-shot fetch, mediated by the raw-directory layout
below; see the individual scripts for URLs. Every raw file has a manifest
in `data/manifests/`.

Python environment: `E:/Projects/Dolomites/.venv/Scripts/python.exe`. All
packages already installed in the venv (see the pip install log at
`data/pip-install.log`). No external rasterio, no external GDAL; ice-frame
reprojection is `pyproj + scipy.ndimage.map_coordinates` on a regular UTM ->
Web Mercator target grid.

## Seguinot NetCDF - findings that drove the ice pipeline

The file `alpcyc.1km.epic.pp.ex.1ka.nc` (Zenodo record 1423176, chosen file
per the run rationale below) opens with:

- 120 time snapshots, cftime years -118999 .. +1 (NoLeap calendar, has_year_zero).
  Converted to integer ka using `ka = round(-year/1000)`, giving snapshots
  labelled 119 ka BP through 0 ka BP inclusive (120 frames total). PISM was
  initialised at 120 ka; the initial condition is not written as a snapshot,
  so the earliest available label is 119 ka.
- Grid: 901 x 601 at 1 km spacing in the UTM-32N CRS declared by the
  `mapping` variable:
  `+units=m +proj=utm +no_defs +zone=32 +a=6378137 +rf=298.257223563 +towgs84=0,0,0 +to_meter=1`
  (a "spherical" UTM built from the WGS84 ellipsoid parameters, exactly as
  PISM writes it). x in [150000, 1050000] m, y in [4820000, 5420000] m.
- Data variables include `thk` (ice thickness, m), `topg` (bed elevation, m),
  surface / basal ice-velocity components, basal-temperate-ice thickness and
  pressure-adjusted basal ice temperature. This pipeline only uses `thk`.
- Ice-thickness range at the LGM (25 ka): trunk-glacier maxima ~2.2-2.3 km,
  consistent with the ~2 km figure quoted for the Bolzano basin in the
  research notes.

Run choice: `alpcyc.1km.epic.pp.ex.1ka.nc` = 1 km resolution, EPICA-Dome-C
temperature forcing, palaeo-precipitation reduction. Chosen because it is
the reference run in Seguinot et al. 2018 figures, the finest published
resolution, and its temperature forcing shares a common climate axis with
CENOGRID and PhanDA (both already shipped on the site).

## Coordinate system used everywhere

- Ice-frame source CRS: UTM 32N (PISM run definition, see above).
- Ice-frame target CRS: Web Mercator (EPSG:3857):
  - **Colorized RGBA frames**: 640 x 465 px lossless WebP, 2x native model
    resolution (500 m per pixel), covering 9.5-13.5 deg E, 45.5-47.5 deg N.
  - **16-bit thickness PNGs**: 320 x 232 px, native 1 km resolution, same
    bounds; value range 0-65535 metres (max observed ~2300 m at LGM).
  - Bilinear resampling used for both; no detail created below the 1 km
    source resolution.
  - *Superseded 2048 x 1488 px PNGs retained in
    `data/processed/quaternary/ice-png-2048-superseded/` for reference;
    not used by the app.*
- Vector overlays (`glaciers-*.geojson`, `lgm-extent.geojson`,
  `faults.geojson`): WGS84 lon/lat, coordinates rounded to 5 decimals.

## ICS chart (`build_ics_chart.py`)

`ics-chart.json` is built from the official ICS chart data, not from a
third-party copy. The International Commission on Stratigraphy publishes the
RDF behind the online International Chronostratigraphic Chart at
https://github.com/i-c-stratigraphy/chart. Its `chart.ttl` holds the chart
version (`owl:versionInfo "2026-06"`), numeric boundary ages
(`time:hasBeginning` / `time:hasEnd` -> `inMYA`), official colours
(`schema:color`), parents (`skos:broader`) and a change note for each
boundary that moved in 2026-06.

- Pinned file: release tag `v2026-06.5` (commit 44d1043, 2026-06-29), stored as
  `data/raw/ics-2026/chart-official/chart.ttl` (sha256 `0158959e...8b355`, see
  `data/manifests/ics-2026.yaml`). The script downloads it if missing and stops
  if the checksum differs. `main` (2026-07-27) only moved the file to a new
  namespace; ages, colours and parents are identical.
- Parsing is a regular expression over the Turtle blocks (rdflib is not in the
  venv). `parse_chart()` is also imported by
  `data/scripts/terrain/build_geology_pmtiles.py`, so geology ages come from
  the same file.
- Output: eons, eras, periods, epochs and ages whose younger bound is under
  300 Ma, ages, colours and parents copied unchanged; `version` is the file's
  own `owl:versionInfo`. The Sub-Period rank (Pennsylvanian) is not in contract
  4 and is left out; its epochs take the Carboniferous as parent. Series with
  no English label in the file are named from their IRI (`MiddleTriassic` ->
  "Middle Triassic").
- Cross-check, stored in the JSON: base Ladinian 241.464, base Anisian 247.0
  and base Olenekian 250.8 Ma from `research/geology/dolomites-geological-history.md`
  all match the chart.
- The JSON is written to `ics-chart.json.tmp` and renamed over the final file
  in one step, because the site build reads it.

## What is not built here

- `content/localities.yaml` -> `terrain/localities.geojson` (out of scope; owner-curated).
- Terrain PMTiles, geology PMTiles: separate pipelines.
- Sea-level Miller 2020, Foster 2017 CO2, Scotese 2021 temperatures, CenCO2PIP:
  present in the research catalogue but not requested for this pass.
