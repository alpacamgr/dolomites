# Terrain pipeline

Builds the Dolomites terrain PMTiles (elevation), the merged Dolomites geology
PMTiles (South Tyrol, Trentino and Veneto open vector maps) with its coverage
outlines, and the WMS overlay descriptor consumed by the terrain view per
`docs/04-data-contracts.md` sections 2.1, 2.2 and the "wms.json" mention.

All scripts are idempotent. Re-running with the raw files already downloaded
will regenerate the PMTiles archives. Pass `--force` to force a rebuild.

## Prerequisites

- Interpreter: `E:/Projects/Dolomites/.venv/Scripts/python.exe` (Python 3.13).
  `data/pip-install.log` records `rasterio 1.5.1 GDAL 3.12.4` on this
  interpreter, so rasterio does install on 3.13 in this environment and the
  fallback `.venv311` is not needed. The terrain build also uses scipy
  (distance transform for the seam cross-fade) and pyproj, both already present.
- One extra runtime package installed manually in an earlier pass:
  `mapbox-vector-tile==2.2.0`. Install with:

  ```powershell
  E:/Projects/Dolomites/.venv/Scripts/python.exe -m pip install mapbox-vector-tile
  ```

- The geology build also needs `pyshp` (3.1.6 in this venv) for the Trentino
  shapefiles, and `extract_pat_unit_ages.py` needs `pdftotext` (Git for Windows
  ships it in `/mingw64/bin`; prefix `PATH="/mingw64/bin:$PATH"` in Git Bash).
- Total disk space to expect: ~1.2 GB of raw TINITALY zips + tifs, ~0.38 GB of
  raw Copernicus GLO-30 tiles, ~1.1 GB of raw geology (South Tyrol GeoJSON
  0.2 GB, Trentino zips 0.27 GB plus 0.65 GB extracted shapefiles, Veneto
  GeoJSON 20 MB), plus ~0.39 GB of processed PMTiles and the geology build's
  intermediate pickles. The terrain build holds the merged GLO-30 mosaic in RAM
  (467 MB) on top of the per-tile TINITALY reads.

## Order of operations

1. `python data/scripts/terrain/fetch_tinitaly.py` (~2-3 min at typical
   home broadband, downloads 17 UTM-tiles of TINITALY 1.1 zipped and
   extracts the enclosed .tif next to each .zip).
2. `python data/scripts/terrain/fetch_copernicus_glo30.py` (~1 min; downloads
   the nine Copernicus DEM GLO-30 tiles N45..N47 x E010..E012, 377 MB, from the
   public AWS bucket into `data/raw/copernicus-dem-glo30/` and writes
   `checksums.json`).
2b. `python data/scripts/terrain/fetch_copernicus_glo90.py` (~10 s; downloads
   six Copernicus DEM GLO-90 tiles N45..N47 x E009 and E013, ~29 MB, for the
   two outer strips of the widened ring bbox 9-14 E / 45-48 N; see
   docs/ux/2026-09-13-terrain-ring.md).
3. `python data/scripts/terrain/build_terrain_pmtiles.py --force`
   (produces the intermediate `data/processed/terrain/dolomites-terrain.pmtiles` plus
   `verification.json`, the full-bbox z9 hillshade and the z10 northern-edge
   `border-fill.png` under `data/processed/terrain/preview/`). The archive is
   written to `data/processed/terrain/dolomites-terrain.pmtiles.part` and then
   renamed over the final path with `os.replace` (same volume, atomic), so the
   app never sees a half-written archive. If another process holds the file
   open, the rename is retried for 60 s; failing that, the new build is left at
   the .part path. `verification.json` is replaced the same way. Run log:
   `data/processed/terrain/build.log`.
4. `python data/scripts/terrain/fetch_geology_bz.py` (~1 min; downloads all
   66 133 CARG-vector features into
   `data/raw/bz-geology-carg/GeologicalUnits-Detailed.geojson`).
5. `python data/scripts/terrain/fetch_geology_tn.py` (~30 s; the four PAT
   Geocatalogo shapefile zips Substrato, Sintemi, Depositi Quaternari and
   Depositi di Frana, 271 MB, and the three legend PDFs into
   `data/raw/pat-geology-carta-geologica/`. Each zip is extracted into a folder
   of the same name; each layer's GeoNetwork metadata record, whose licence
   field is the licence evidence, is saved next to it; `checksums.json`).
6. `python data/scripts/terrain/fetch_geology_veneto.py` (~10 s; Regione del
   Veneto lithology 1:250,000 from the IDT2 GeoServer WFS, whole region, 20 MB
   GeoJSON in EPSG:4326, plus its metadata record, into
   `data/raw/veneto-litologia-250k/`).
7. `python data/scripts/terrain/extract_pat_unit_ages.py` (seconds; needs
   `pdftotext`). Reads the age statement of every Trentino unit from the PAT
   unit legend PDF and writes it into `geology_age_mapping.json`
   (`sources.pat-geology-carta-geologica.unit_ages`). Only needed when the PAT
   data or legend change; the result is checked in.
7b. Gap-fill sources (priorities 4-6), downloaded by hand on 2026-09-12 (no
   fetch scripts; URLs and SHA-256 in each `data/raw/<id>/checksums.json` and
   manifest): `data/raw/swisstopo-geocover/` (4 GeoCover sheet zips),
   `data/raw/ispra-geologia-100k-inspire/` (INSPIRE GML zip) and
   `data/raw/geosphere-geologicunits-500k/` (GeoPackage). They are read by
   `geology_gapfill_readers.py` (ISPRA parse cached in
   `data/processed/terrain/geology-gapfill-cache/`; swisstopo GeoPackages
   extracted to `data/raw/swisstopo-geocover/extracted/`). Then
   `python data/scripts/terrain/review_ispra_100k_units.py` (~2 min) writes the
   per-unit ISPRA age decisions into `geology_age_mapping.json`; it reads the
   South Tyrol/Trentino/Veneto polygons of the previous build's intermediates
   for its cross-check, so run it again after a first build if they were missing.
8. `python data/scripts/quaternary/build_ics_chart.py`, then
   `python data/scripts/terrain/build_geology_pmtiles.py --force`
   (~25 min: noding the six sources into one coverage, per-zoom generalisation,
   tile encoding with `--workers N` processes; `--reuse coverage` or
   `--reuse generalised` skip the first stages when only ages or tile settings
   changed). Then `export_tiles.py` (vector, see below),
   `python data/scripts/terrain/check_geology_tiles.py --json data/processed/terrain/geology-check/after.json`
   and `build_geology_pmtiles.py --qa-only` so the meta embeds the check. Produces
   the intermediate `data/processed/terrain/geology-dolomites.pmtiles`,
   `geology-dolomites.meta.json`, `geology-coverage.geojson`,
   `geology-gaps.geojson` and
   `data/processed/terrain/preview/geology-dolomites-by-age.png`, and runs the
   checks in "Geology verification". Intermediate files in
   `data/processed/terrain/`: `geology-dolomites-features.pkl` (clipped
   features, loaded by the workers), `geology-dolomites-extents.pkl` and
   `geology-dolomites-build-result.json`; `--qa-only` re-runs coverage,
   verification, preview and meta.json from them. Every output is written to a
   temp file and renamed into place (retried for 10 s if another process holds
   it open). Run log: `data/processed/terrain/build-geology-dolomites.log`.
   This script no longer writes `geology-suedtirol.pmtiles`: that archive,
   built 2026-09-12 by the South Tyrol-only version of the script, stays in
   place for the app until it switches to `geology-dolomites.pmtiles`, and the
   build reads it as the "before" state of its checks.
9. `terrain/wms.json` is authored by hand from OGC GetCapabilities responses
   the pipeline actually fetched (currently just the ISPRA CARG 1:50k raster
   WMS). Its `not_included` entries say why the PAT and Veneto services are not
   listed (their vector data is in the merged archive) and what is still
   unverified.

## Choice of source DEM

Per `docs/04-data-contracts.md` 2.1: core (10.3-12.7 E / 45.8-47.2 N, z6-12)
uses TINITALY 10 m inside Italy, Copernicus GLO-30 for voids and areas outside
Italy. Ring (9-14 E / 45-48 N, z6-9 only) additionally uses Copernicus GLO-90
in the two outer strips (9-10 E and 13-14 E) that lie outside the fetched
GLO-30 raw tiles.

- **TINITALY 1.1** (INGV, CC BY 4.0) is the primary source. Direct-download
  zips live under `https://tinitaly.pi.ingv.it/data_1.1/<tileid>_s10/<tileid>_s10.zip`;
  tile naming was reverse-engineered from the download page's `<area>` map
  (see the docstring of `fetch_tinitaly.py`). It stops at the Italian border
  (nodata -9999).
- **Copernicus DEM GLO-30** (ESA / DLR / Airbus, free licence, see
  `data/manifests/copernicus-dem-glo30.yaml`) fills everything TINITALY lacks:
  the Austrian side north of ~46.9 N, the Marmolada north-face strip and the
  missing ridge cells. These used to be encoded as 0 m, which drew a cliff
  along the border.
- **Copernicus DEM GLO-90** (same licence as GLO-30, see
  `data/manifests/copernicus-dem-glo90.yaml`) fills the two outer strips of
  the ring (9-10 E and 13-14 E). Six raw tiles at ~5 MB each. Used only at
  z6-9 (0.7 x 90 m = 63 m; z9 tile pixel is 105 m at 46.5 N, safe; z10 tile
  pixel is 52.6 m, below the honesty floor).

### Border fill

For every output tile the build reads TINITALY (bilinear, as before) and the
merged GLO-30 mosaic (bilinear, `rasterio.warp.reproject`) onto the same Web
Mercator grid, padded by the feather width plus 4 px. With `d` = ground
distance from a valid TINITALY pixel to the nearest TINITALY nodata pixel
(`scipy.ndimage.distance_transform_edt`, pixel size = tile m/pix at the tile
centre latitude):

    t = clip(d / 300 m, 0, 1);   w = 0.5 - 0.5 * cos(pi * t)
    height = w * TINITALY + (1 - w) * GLO-30        (w = 0 where TINITALY is nodata)

So the output is TINITALY wherever it lies more than 300 m inside its own
edge, GLO-30 wherever TINITALY has no value, and a weighted mean of the two
observed heights in the 300 m band. No height is invented. The padding lets
seams just outside a tile still feather correctly. At z6-z8 a tile pixel
(105-840 m) is wider than the feather, so the transition there is effectively
a hard switch.

### Vertical datum

- GLO-30: "The vertical reference datum is the Earth Gravitational Model 2008
  (EGM2008; EPSG 3855)" (Copernicus DEM Product Handbook v5.0, 2022-11-29,
  sec. 1.2), i.e. orthometric.
- TINITALY 1.1: no datum is stated in the accompanying notes or on the download
  pages. It is interpolated from topographic contour lines and spot heights.
- Empirical check (8 793 913 valid TINITALY cells sampled every 50 m inside the
  bbox, GLO-30 bilinear at the same point): TINITALY minus GLO-30 median
  **-3.25 m** (p25 -11.15, p75 +0.69). An ellipsoid-vs-geoid mismatch would show
  up as the ~47 m geoid undulation. Within 0-300 m of the TINITALY edge the
  median is +0.9 to +1.7 m (p5 about -12 m, p95 +22 to +32 m).
- Conclusion: both sources are orthometric and **no geoid correction is
  applied**. The small negative median is consistent with GLO-30 being a
  surface model (canopy, buildings) and TINITALY bare ground.

## Maxzoom arithmetic

At latitude 46.5 N in Web Mercator, the ground resolution of one pixel of a
512-px tile at zoom z is

    m/pix = 2 * pi * R_earth * cos(46.5 deg) / (2^z * 512)
          = 40 075 016.7 * 0.68835 / (2^z * 512)
          = 53 892 / 2^z  m/pixel

    z9  -> 105.3 m/pix
    z10 ->  52.6 m/pix
    z11 ->  26.3 m/pix
    z12 ->  13.2 m/pix
    z13 ->   6.6 m/pix

The data-honesty policy (`docs/03-data-policy.md`, rule 6) forbids
upsampling that fabricates detail. We stop at the zoom whose tile pixel is
still >= 0.7 * source pixel (i.e. tile pixels stay coarser than or
similar to the source):

    - TINITALY 10 m: 0.7 * 10 = 7 m. z12 gives 13.2 m/pix (safe);
      z13 gives 6.6 m/pix (upsamples ~35 % beyond source). -> **maxzoom = 12**.
    - Copernicus GLO-30: 0.7 * 30 = 21 m. z11 gives 26.3 m/pix (safe);
      z12 gives 13.2 m/pix (upsamples ~130 % beyond source). -> maxzoom = 11.

`docs/04-data-contracts.md` currently declares "zoom 6 to 13" for the
terrain archive. This build ships z6-12 because the TINITALY source cannot
honestly support z13. The corresponding change to the contract has been
proposed inline in `terrain/dolomites-terrain.meta.json` (`max_zoom = 12`);
edit the contract to match if the app team agrees.

## Verification

`build_terrain_pmtiles.py` decodes tiles from the finished archive and writes
`app/public/data/terrain/verification.json` (summarised in
`dolomites-terrain.meta.json`):

1. Read-back at three zooms: the bbox-centre tile at z=8, 10 and 12. The
   centre pixel is compared with the raw TINITALY cell at the same point.
2. Point checks at z=12: three points outside TINITALY (compared with GLO-30)
   and three inside Italy (compared with TINITALY). The first Austrian
   candidate, 46.95 N 11.40 E, turned out to be inside Italy (TINITALY 1160.8 m,
   Pflersch valley) and was replaced by 47.05 N 11.45 E.

Results of the 2026-09-12 build (tile height minus source, metres):

| check | point | tile | source | diff |
|---|---|---|---|---|
| z8 centre | 11.9545 E 46.5579 N | 1630.9 | TINITALY 1632.6 | -1.74 |
| z10 centre | 11.4261 E 46.4376 N | 1271.1 | TINITALY 1271.3 | -0.20 |
| z12 centre | 11.4698 E 46.5286 N | 905.5 | TINITALY 901.8 | +3.75 |
| Austria, Wipptal N of Brenner | 11.45 E 47.05 N | 1912.6 | GLO-30 1915.9 | -3.29 |
| Austria | 12.00 E 47.10 N | 1586.9 | GLO-30 1584.8 | +2.12 |
| Austria, East Tyrol | 12.30 E 46.90 N | 1882.9 | GLO-30 1885.0 | -2.15 |
| Italy, Marmolada area | 11.85 E 46.44 N | 2889.9 | TINITALY 2893.5 | -3.64 |
| Italy, Cortina d'Ampezzo | 12.14 E 46.54 N | 1248.4 | TINITALY 1247.7 | +0.71 |
| Italy, Bolzano | 11.35 E 46.50 N | 270.0 | TINITALY 270.0 | +0.04 |

All nine are within 3.8 m. That is the 0.1 m Terrain-RGB quantisation plus
bilinear resampling onto 13-53 m tile pixels, compared against a single
nearest 10 m or 30 m source cell (larger on steep slopes). At the Austrian
points TINITALY is nodata, so the old build would have encoded 0 m there.

Archive: 958 tiles, 309 847 777 bytes (309.8 MB; the 0 m-fill build was
221.5 MB, and the extra bytes are the real relief north of the border). The
archive header and metadata read back with z6-12, the 10.3-12.7 E /
45.8-47.2 N bounds, both attributions, `source_datasets` and
`seam_feather_m: 300`.

Seam inspection: `data/processed/terrain/preview/border-fill.png` is a z10
hillshade (4094 x 1534 px, whole tiles covering 46.7-47.2 N across the bbox)
decoded from the archive itself.

The geology checks are described under "Geology verification" below.

## Geology sources and coverage

The South Tyrol CARG layer (CC0) holds only the province's published CARG
sheets, so the chapter 05 reef platforms (Latemar, Marmolada) and everything in
Trentino and Belluno were missing. Sources checked on 2026-09-12; a source is
used only if a record actually fetched states a licence that allows
redistributing derived tiles with attribution:

| priority | dataset id | content | licence and where it is stated | used |
|---|---|---|---|---|
| 1 | `bz-geology-carg` | P_BZ Carta geologica CARG, detailed units (1:10,000 survey) | CC0 1.0, data.civis.bz.it | yes |
| 2 | `pat-geology-carta-geologica` | Carta Geologica della PAT, layers Substrato + Sintemi (1:10,000) | CC BY 4.0 in each Geocatalogo record (`gmd:useLimitation`); the landing page says CC BY (linking the 3.0 IT legal code) and asks for the credit "Dati elaborati dal Servizio geologico della Provincia autonoma di Trento" | yes |
| 3 | `veneto-litologia-250k` | Regione del Veneto lithology database (1:250,000) | IODL 2.0 in the IDT2 metadata record; IODL 2.0 requires naming source and licensor and linking the licence | yes |
| 4 | `swisstopo-geocover` | swisstopo GeoCover 1:25,000, sheets 1179/1199/1219/1239 (Swiss strip) | swisstopo OGD terms (free use, source attribution mandatory), geocat record | yes |
| 5 | `ispra-geologia-100k-inspire` | ISPRA Carta Geologica d'Italia 1:100,000, INSPIRE GML (South Tyrol outside the CARG sheets, Lombardy and Friuli edges) | CC BY 4.0 in the RNDT record and the INSPIRE Atom feed | yes, with the per-unit age review |
| 6 | `geosphere-geologicunits-500k` | GeoSphere Austria geological units 1:500,000 (Austria) | CC BY 4.0 in the ISO record | yes |
| - | ISPRA CARG sheet databases 028, 029, 044, 045, 046 | CARG-Gate states CC-BY 4.0 for its downloads | not published: `banca_dati` is "No" (028), "In corso di pubblicazione" (029, 046), "In corso di realizzazione" (044) or empty (045), no download link | no |

Also checked: the IDT2 catalogue has no Veneto geological map finer than the
1:250,000 lithology (searches for geologia, carta geologica, CARG, litologia,
formazioni, substrato); the dati.trentino.it CKAN search API returned a Solr
error, so the PAT Geocatalogo (GeoNetwork) was used. South Tyrol also serves
`p_bz-Geology:GeologicalUnitsOverview` (245 polygons, tectonic-unit legend
only, no age fields), which would reach Bletterbach, Bolzano and Brixen at
overview scale; it is not part of this build. Manifests:
`data/manifests/pat-geology-carta-geologica.yaml`,
`veneto-litologia-250k.yaml` and `geology-dolomites.yaml` (the merged product).

How `build_geology_pmtiles.py` merges them (gap-free rebuild of 2026-09-12;
gap-fill candidates and their evaluation: research/geology/geology-gap-fill-sources.md):

- Loaders per source return polygons in EPSG:4326 with the tile properties.
  Trentino tiles only Substrato (bedrock, 121 443 polygons) and Sintemi
  (Quaternary cover, 104 556), which do not overlap (15 x 15 km test window
  around Latemar: intersection 0 m2); Depositi Quaternari/Frana give the deposit
  type (`denom`) used as `lithology` of Sintemi units. swisstopo: Unconsolidated
  deposits are listed before Bedrock, so they win where the two layers overlap.
  ISPRA and GeoSphere EPSG:4258 coordinates are used as EPSG:4326.
- Coverage: every polygon is clipped to the bbox, the boundaries of all
  332 539 polygons (26.3 M vertices) are noded together on a 1e-7 deg grid
  (`shapely.union_all(..., grid_size)`), polygonized into 738 630 faces, and
  each face goes to the highest-priority polygon containing it. 333 unions came
  out with self-touching rings and were split with `make_valid(method="structure")`;
  the result is a valid coverage (`shapely.coverage_is_valid`), 0 invalid
  polygons. Polygons kept: South Tyrol 66 051, Trentino 201 323, Veneto 2 554,
  swisstopo 5 984, ISPRA 16 005 (of 45 118 in the bbox), GeoSphere 644. Areas
  (geodesic, per source extent): 4 401, 5 532, 5 478, 547, 6 411 and 6 173 km2.
  ~10 min.
- Generalisation per zoom in Web Mercator: units below `merge_below_px2` tile
  pixels (512 px tiles) are merged into the neighbour with the longest shared
  edge (adjacency from identical segments; the merged unit keeps its largest
  member's attributes), then `shapely.coverage_simplify` with `simplify_px`:

  | zoom | 8 | 9 | 10 | 11 | 12 | 13 |
  |---|---|---|---|---|---|---|
  | merge below (px2) | 2 | 2 | 1 | 1 | 1 | - |
  | VW tolerance (px) | 1.25 | 1.25 | 1 | 1 | 0.5 | - |
  | units | 34 411 | 77 461 | 177 306 | 236 769 | 273 897 | 292 561 |
  | served MB (raw MVT) | 1.88 | 4.20 | 10.14 | 15.51 | 29.54 | 61.58 |

  Every simplified zoom is a valid coverage. With 1 px2 / 1 px at z8-z9 three
  tiles were 1.19-1.22 MB, hence the coarser setting there.
- Tiles: the zoom's coverage clipped to the tile plus 16/4096 units
  (`clip_by_rect`), quantized to 4096 in Web Mercator, invalid rings repaired by
  the encoder. Archive 71.8 MB gzip, 3 537 tiles (0 empty); served 122.9 MB,
  largest tile 880 kB (10/544/363). The first merged build (per-feature
  Douglas-Peucker per tile) served 117.3 MB in 2 070 tiles with up to 3.5 MB
  per tile and lost polygons at low zoom.
- `geology-coverage.geojson`: per source, the union of its polygons, simplified
  0.005 deg and repaired, with `source`, `attribution`, `license`, `scale`,
  `scale_denominator`, `label: interpreted`. `geology-gaps.geojson`: DEM bbox minus
  all coverage (128.6 km2, 0.45% of the bbox), opened with 0.0001 deg,
  simplified 0.0001 deg, parts under 1e-7 deg2 dropped (128.4 km2 listed in
  277 parts, one feature per part with `kind: no_open_geology`, `area_km2`,
  `mean_width_m` = 2 x area / perimeter in EPSG:25832: 105 parts under 50 m
  (0.88 km2), 120 of 50-200 m (12.89 km2), 52 wider (114.56 km2); thin parts are
  mostly seams along sheet and source borders and are not filled).

## Geology verification

Stored under `verification` in `geology-dolomites.meta.json` (full grids and
unit lists there); the grid/point "before" is `geology-suedtirol.pmtiles`.

- Served tiles, `check_geology_tiles.py` (3 000 random points, seed 20260912,
  point-in-polygon on the decoded tile of each zoom):

  | zoom | covered before | covered after | dated share before / after | missing vs z13 before / after | max tile before / after |
  |---|---|---|---|---|---|
  | 8 | 1 317 | 2 991 | 76.9% / 87.1% | 16.6% / 0.10% | 3 525 / 801 kB |
  | 9 | 1 384 | 2 988 | 77.0% / 87.3% | 12.3% / 0.17% | 3 037 / 854 kB |
  | 10 | 1 457 | 2 989 | 77.8% / 87.6% | 7.6% / 0.13% | 1 634 / 880 kB |
  | 11 | 1 531 | 2 993 | 78.1% / 87.7% | 2.7% / 0% | 766 / 558 kB |
  | 12 | 1 566 | 2 993 | 78.3% / 87.5% | 0.5% / 0% | 423 / 429 kB |
  | 13 | 1 574 | 2 993 | 78.4% / 87.5% | 0 / 0 | 435 / 438 kB |

  After: points inside two polygons 0 at every zoom (before: up to 151 at z8);
  dated share within 0.41 percentage points of z13 at every zoom. Undated share
  at z13 per source, before / after: Veneto 50.9% / 1.5%, Trentino 9.7% / 8.8%,
  South Tyrol 0.9% / 0.9%; new sources: swisstopo 0%, ISPRA 31.9%, GeoSphere
  12.9% (glaciers). Uncovered points 7 of 3 000 (before 1 426).
- Point coverage (z12 tile decoded; approximate diagnostic points, not
  content): Latemar, Tesero, Predazzo, Pale di San Martino Trentino; Civetta
  and Cortina Veneto (Cortina now legend_join Ladinian-Carnian); Schlern and
  Sella South Tyrol; Bolzano, Brixen, Bruneck ISPRA 1:100k (Quaternary
  deposits); Bletterbach ISPRA scree at 11.434 E 46.358 N and, at 11.42 E 46.36 N,
  ISPRA 'arenarie quarzose' dated Lopingian by its description '(Arenarie di Val
  Gardena)' (legend_join); Mayrhofen GeoSphere; S-charl swisstopo.
- 0.05 deg grid over the bbox, 1 344 cell centres against z12 tiles: before 211
  covered; after 1 335 covered (South Tyrol 215, Trentino 261, Veneto 250,
  swisstopo 26, ISPRA 292, GeoSphere 291), 9 empty (border slivers).
- Borders between the clipped extents (EPSG:25832): overlaps and unmapped
  strips within 50 m of both sources are listed per source pair in the meta.
- Preview `data/processed/terrain/preview/geology-dolomites-by-age.png`: z10
  mosaic from the archive, units in their ICS colour (grey where null),
  coverage outlines per source.

## Withheld ages and basement consistency

Tile contract since 2026-09-13 (docs/04 section 2.2): every uncoloured unit says
why. `age_basis: "withheld"` means the source states an age that the site does not
use for colour; the source's own text stays in `age_label` and
`age_withheld_reason` is one of `metamorphic_event`, `contradiction`,
`young_bedrock`, `unmappable_interval` or `open_range`. `age_basis: "none"` means
the source gives no usable age. Numbers and colour are null for both. Per source:
South Tyrol 'Terziario (?)' younger bounds are `unmappable_interval`; Trentino
'pre-Permiano' / 'post-Carbonifero' are `open_range` and '?Terziario'
`unmappable_interval`; swisstopo open ranges are `open_range`, legend or description
contradictions `contradiction`, 'frühes Paläozoikum' `unmappable_interval`; ISPRA
reasons come from the per-unit review (metamorphic and faulting events, name /
description / age contradictions, young bedrock, 'Unknown'); GeoSphere's subduction
unit is `metamorphic_event`. Glaciers, water, anthropic and unmappable ground are
`none`.

Young bedrock (ISPRA 1:100,000): a unit dated within 0-66 Ma whose name or
description names volcanic, plutonic, dyke, metamorphic or (for a bare
'Cenozoic') lithified bedrock is withheld, unless its name or description joins
unambiguously to a South Tyrol / Trentino formation or its age names a specific
epoch that a cited authority confirms for the named body (Adamello-Presanella
tonalites from the Trentino unit legend; Paleogene basalts from the Veneto map).

Basement across source borders: one rule for all sources, an age is withheld when
the source's attributes call it a metamorphic or deformation event, an open range
or contradictory, and used otherwise. The sources record the same crystalline
basement differently, so colours still jump at their borders: GeoSphere gives
formation ranges ('Altkristallin' paragneiss, event 'deposition', Neoproterozoic -
Devonian), swisstopo chronostratigraphic ranges (e.g. Proterozoikum - Paläozoikum)
and South Tyrol 'Paleozoico', while ISPRA gives a metamorphic event (withheld)
and Trentino only 'pre-Permiano' (withheld). No source gives both ages, so this
is documented (meta `ages.basement_ages_across_sources`) rather than harmonised.

The geology layer is labelled `interpreted` (docs/03): a geological map is drawn
by researchers from field evidence, and the numeric ages are derived here.

## Geology ages

### South Tyrol (`bz-geology-carg`)

The CARG units carry stratigraphic names, not numbers: `ETA_CODICE_MIN_IT`
(youngest age) and `ETA_CODICE_MAX_IT` (oldest age), each with a German twin
in `*_DE`. The WFS download has 89 distinct Italian strings over both fields:
stages ("Anisico"), series ("Triassico medio"), periods and eras, many with
the qualifier "(p.p.)" (pro parte) or "(?)" (uncertain).
`build_geology_pmtiles.py` turns them into numbers and colours:

- `geology_age_mapping.json` maps every distinct Italian string and its German
  twin to one ICS chart interval name (chart 2026-06, the same `chart.ttl` that
  builds `app/public/data/ics-chart.json`). The build stops on a string missing
  from the table, on a German string that does not match its Italian twin, and
  if `ics-chart.json` was built from a different chart.
- `age_max_ma` is the older bound of the interval named in `ETA_CODICE_MAX_IT`
  and `age_min_ma` the younger bound of the interval named in
  `ETA_CODICE_MIN_IT`, so `age_min_ma <= age_max_ma`. Qualified strings use the
  full interval, so the range is an outer envelope. For 255 units
  (Formazione del Catinaccio CAT/CAT1/CATa: "Ladinico" / "Anisico"; ZUU1:
  "Retico" / "Norico (?)") the source puts the younger name in the MAX field;
  the build orders the two names by chart age first and counts these units in
  meta.json.
- `color` is the official ICS colour of the interval named in
  `ETA_CODICE_MIN_IT`, at the rank the string names (stage colour for a stage,
  period colour for a period). `age_label` keeps the original Italian strings
  as "MAX - MIN".
- Two strings stay unmapped and give null: "Carbonifero superiore" (the
  European Upper Carboniferous and the Pennsylvanian start at different
  boundaries) and "Terziario (?)" (not an ICS unit). Mapping Lower and Upper
  Permian to the Cisuralian and Lopingian series is a judgement call, noted in
  the table.
- The polygons and their attributions are the map's (label `interpreted` since
  2026-09-13: a geological map is drawn from field evidence); the numbers are the
  chart's boundary ages, not ages published by the map. Mapped and unmapped
  unit counts are under `sources[].ages` in `geology-dolomites.meta.json`.

### Trentino (`pat-geology-carta-geologica`)

The shapefiles carry no ages. The Servizio Geologico publishes them in the unit
legend "Legenda della Carta Geologica - Descrizione delle Unita" (Versione
Ottobre 2019), one block "SIGLA NAME description ... Eta: <age>" per unit.
`extract_pat_unit_ages.py` reads that text with `pdftotext` and joins it to
the shapefiles on `sigla_cart` + `nome`: 390 units have their own statement,
18 members without one take their formation's (name starts with
"<formation name> -", e.g. SCIb <- SCI; 4 204 polygons), and 65 units have no
statement and stay null (the Predazzo and Monzoni plutons, the Monte Fernazza
facies, Formazione di Regnana, glaciers, anthropogenic deposits, "area non
rilevabile"; 7 663 polygons). Dyke symbols reused by different groups (fl, fm,
ft) are only resolved when the unit name matches one block.

The 142 distinct age strings (after whitespace/case normalization) map to an
ICS interval pair in `sources.pat-geology-carta-geologica.terms`:
`age_max_ma` = start of `older`, `age_min_ma` = end of `younger`, `color` =
colour of `younger`. Rules, all listed in the table: substage qualifiers and
Anisian/Ladinian substages (Pelsonico, Illirico, Fassanico ...) use the full
stage; Pleistocene/Holocene inf./medio/sup. use the chart's subseries stages;
Eocene/Oligocene/Miocene/Paleocene inf./medio/sup. use the conventional stages
(judgement call); Permiano inf./sup. -> Cisuralian/Lopingian as for South
Tyrol; "attuale" -> Holocene; "Scitico" -> Lower Triassic. Unmapped, null:
"pre-Permiano" (13 853 polygons; open-ended), "post-Carbonifero" (141),
"?Terziario" (124), and the older half of "Carbonifero sup. - Permiano inf."
(2, one bound). Result: 204 215 polygons with both bounds, 2 with one, 21 782
with none. `age_label` is the legend's own age text.

### Veneto (`veneto-litologia-250k`)

The age is the text in the final parentheses of `depositi_a`, e.g. "Dolomia
Principale (Trias sup.)". `sources.veneto-litologia-250k.terms` has one row
per class in the bbox (49); the source often writes the younger age first, and
the rows are ordered by chart age. Lias/Dogger/Malm are the Lower/Middle/Upper
Jurassic; "Miocene medio" -> Langhian-Serravallian and "Paleocene sup." ->
Thanetian are judgement calls. 18 classes have no age text and stay null
(including "Dolomia Cassiana, D. dello Sciliar, D. del Serla Sup., C. della
Marmolada", the Quaternary deposits and the metamorphic sequences; formation
names are not turned into ages), and "Conglomerato di Ponte Gardena (Permiano
inf.-? Carbonifero sup.)" keeps only its younger bound. Result: 1 177 of 2 608
polygons with both bounds, 2 with one, 1 429 with none.

## Notes on missing data

- No cell of the terrain bbox is encoded as a placeholder height any more:
  TINITALY nodata is filled from GLO-30 (see "Border fill").
- On the GLO-30 side the source is ~30 m (1 arc-second; ~21 m E-W x 31 m N-S
  at 46.5 N). The contract fixes z6-12 for the whole archive, so Austrian z12
  tiles (13.2 m/pix) and, to a lesser degree, z11 tiles (26.3 m/pix) are
  bilinear interpolations of 30 m data: smooth, with no added detail, and finer
  than the 0.7x-source guideline above. The app should not present Austrian
  terrain at z12 as 13 m data. The GLO-30 side is also a surface model (it
  includes forest canopy and buildings), unlike TINITALY.
- Geology gaps with no open vector source found (outside the outlines in
  `geology-coverage.geojson`): South Tyrol outside its published CARG sheets
  (Bletterbach, Bolzano, Brixen and more), Austria, Switzerland, and the parts
  of Lombardy and Friuli inside the bbox. Within the covered area, Veneto is
  1:250,000 and many Trentino and Veneto units have no age (see "Geology
  ages"); those draw in grey, not as missing data.
- Geology ages are the ICS chart's boundary ages for the stage names the
  sources record, not ages measured or published by the maps (see
  "Geology ages"). Units whose age string cannot be mapped with confidence,
  and the "zona non rilevabile" areas with no age string, carry null ages.

## Export to served tiles (ADR 0006)

The PMTiles archives are intermediates and are not shipped. After rebuilding either archive, export it:

```bash
.venv/Scripts/python.exe data/scripts/terrain/export_tiles.py --in data/processed/terrain/dolomites-terrain.pmtiles --out app/public/data/terrain/elevation --kind raster-dem --template "terrain/elevation/{z}/{x}/{y}.webp"
.venv/Scripts/python.exe data/scripts/terrain/export_tiles.py --in data/processed/terrain/geology-dolomites.pmtiles --out app/public/data/terrain/geology --kind vector --template "terrain/geology/{z}/{x}/{y}.pbf"
```

Elevation tiles are re-encoded as lossless WebP and checked pixel by pixel; vector tiles are written as raw MVT. The dev server does not watch `public/data`, so restart it after an export.
