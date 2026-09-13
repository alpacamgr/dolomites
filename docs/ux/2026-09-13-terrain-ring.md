# 2026-09-13 - Terrain outer ring

Follow-up to `2026-09-13-terrain-look.md` finding 5: pitched cameras look past the
core bbox (10.3-12.7 E, 45.8-47.2 N) and a zoom-out reveals a rectangle of
mountains floating in haze. Add a coarse outer ring of relief so the region
reads as a complete landscape.

Branch: `terrain-ring` off `main`.

## Design decisions

### 1. Source for the ring

- Existing sources kept exactly as today for the core bbox: TINITALY 1.1 (10 m,
  Italy) as primary, Copernicus DEM GLO-30 (30 m, 9 raw tiles covering
  10-13 E / 45-48 N) as fill for TINITALY nodata and outside Italy.
- New source for the outer strips: **Copernicus DEM GLO-90** (~90 m; 3 arc-sec)
  from the public AWS bucket `copernicus-dem-90m`, same ESA CCM licence as the
  GLO-30 already used. Fetched via `data/scripts/terrain/fetch_copernicus_glo90.py`
  with per-tile SHA-256 in `data/raw/copernicus-dem-glo90/checksums.json` and
  manifest `data/manifests/copernicus-dem-glo90.yaml`.
- Tiles fetched: N45..N47 x E009 and E013 (six 1 deg tiles). The other twelve
  tiles that would make a uniform 5x3 GLO-90 grid across 9-14 E / 45-48 N sit
  inside the existing GLO-30 coverage (10-13 E / 45-48 N), so they are not
  fetched: the GLO-30 pixels are used there. This keeps one source per pixel
  and adds no redundancy.
- Ring bbox: **9.0 E to 14.0 E, 45.0 N to 48.0 N** (matches
  `2026-09-13-terrain-look.md` recommendation). Core stays 10.3-12.7 E,
  45.8-47.2 N.
- Honesty: per `docs/03-data-policy.md` rule 6 and the build's
  0.7 x source guideline, a 90 m source is safe at z9 (105 m/px at 46.5 N)
  and coarser; at z10 the tile pixel drops to 52.6 m (below 63 m = 0.7 x 90).
  So the ring is built at **z6-z9 only**. z10-z12 remain built only inside the
  core bbox, where TINITALY 10 m and GLO-30 30 m still support them (see
  `data/scripts/terrain/README.md` "Maxzoom arithmetic").

### 2. Tile layout

- One tileset, one `tiles.json`. Widened bounds (9.0, 45.0, 14.0, 48.0),
  `minzoom: 6`, `maxzoom: 12`. At z6-9 the tileset covers the ring bbox; at
  z10-12 tiles are emitted only where the tile intersects the core bbox
  (10.3-12.7 E / 45.8-47.2 N). MapLibre falls back to the parent DEM tile for
  missing z10-12 tiles outside the core (verified below).
- Mosaic priority per pixel: **TINITALY > GLO-30 > GLO-90**. Existing 300 m
  cosine cross-fade along TINITALY validity edges preserved as-is. GLO-30 and
  GLO-90 are combined by simple priority (GLO-30 wherever it exists in the raw
  9-tile grid, GLO-90 in the two outer strips). No cross-fade between GLO-30
  and GLO-90: both are DSMs with the same EGM2008 vertical datum, and any
  step at 10 E / 13 E is smaller than the tile pixel at z6-9 (105-840 m ground)
  so it is not visible on the hillshade (checked with the pipeline's z9
  hillshade preview under `data/processed/terrain/preview/`).
- The z6-9 core tiles are rebuilt so a single z6 tile can cover core and
  ring together (a z6 tile spans ~840 m/px at 46.5 N; the two pre-existing
  z6 core tiles sat entirely inside the smaller bbox and had to be replaced
  to carry ring pixels). z10-12 core tiles are byte-identical to the previous
  build: same source data, same code path, same seed of tiles.

### 3. MapLibre behaviour with missing z10-12 in the ring

To be verified empirically after the build. If the terrain mesh does not fall
back cleanly, or if the 404 count per view is more than a handful, an in-engine
`transformRequest` will short-circuit ring-only z>=10 tiles to a URL that fails
without a network round trip, using the core bbox recorded in `tiles.json` and
the tile x/y/z. Numbers recorded below after the build.

### 4. Geology edge

The geology drape stops visibly at the core rectangle now that relief continues
beyond it. Draw a subtle "extent of the geological maps" line at the core bbox
in the terrain engine, only when a geology layer is on. Add a matching row in
`GeologyKey.svelte`, strings in `content/ui/{en,de,it}.json`. No fading tricks;
the ring reads as terrain-only outside the maps.

### 5. Camera bounds

`app/src/lib/terrain/index.ts` reads `bounds` from the DEM's `tiles.json`, so
`maxBounds` widens automatically to (about) 6.5 E to 16.5 E and 43.5 N to
49.5 N. `minZoom` currently 6.5; drop to 6 so a whole-region zoom-out settles
on a ring view. Story cameras (`content/timeline/*.yaml`) not touched. Fog/sky
kept as tuned in the previous pass, checked after.

### 6. Honesty and docs

- `docs/04-data-contracts.md` 2.1 updated: bounds (9.0, 45.0, 14.0, 48.0),
  z6-9 across the ring, z10-12 core only, ring source `copernicus-dem-glo90`.
- `app/public/data/terrain/dolomites-terrain.meta.json`: third source entry
  with attribution, licence, resolution, role; attribution string names all
  three sources.
- `data/scripts/terrain/README.md`: fetch step for GLO-90, updated bbox and
  per-zoom coverage rows, per-zoom byte counts.
- UI strings: `layers.dolomites-terrain` in en/de/it names all three sources.
- `data/manifests/copernicus-dem-glo90.yaml`: full manifest with URL, licence,
  attribution, checksum policy.

## Measurements

Tile counts and served bytes per zoom before / after (fill in after the build).

## Seam fix (2026-09-13, post-review)

A reviewer decoded the first ring build's z9 tiles and found a one-pixel-wide
N-S trench of false low ground along 10 E and (fainter) 13 E. Example: in
`app/public/data/terrain/elevation/9/270/180.webp` the column at lon ~9.9996 E
(col 113) reads a mean height of ~1027 m, roughly 53% below its neighbours
(col 112 = 2205 m, col 114 = 2184 m), while the raw GLO-90 E009 tile and
GLO-30 both read ~2400 m at that point.

Cause. `data/scripts/terrain/build_terrain_pmtiles.py:load_glo90_mosaic()`
called `rasterio.merge.merge` on the six GLO-90 tiles (N45..N47 x E009 and
E013). The result is a single 9-14 E raster whose 10-13 E middle is empty
because no tile was fetched there (correctly so: GLO-30 covers 10-13 E). GLO-90
tiles set no nodata attribute, so `rio_merge` fills that empty area with 0 m
(a valid elevation, not nodata). The subsequent bilinear
`rasterio.warp.reproject(..., src_nodata=None, ...)` in `read_glo30_window`
then treats the fill as real data, and destination pixels just west of 10 E or
just east of 13 E get a bilinear average of a real GLO-90 cell and a 0 m fill
cell -> the low column at the seam.

Fix. Build one gap-free mosaic per longitude strip instead of merging the two
strips into one raster with a hole. `load_glo90_strip_mosaics` groups the
tiles by the `E<lon>` tag in the filename and merges each group on its own, so
each source array only holds contiguous observed cells. `read_glo30_window`
now reprojects each strip separately into the fill array; no fill value ever
enters the bilinear kernel.

Additionally, the GLO-90 E009 strip's east edge (~9.99958 E) sits ~28 m west
of the GLO-30 mosaic's west edge (~9.99986 E), leaving a sliver where a
destination pixel is off the east end of the strip and off the west end of
GLO-30. To bridge that sliver without inventing data, `load_glo90_strip_mosaics`
pads the strip by one GLO-90 pixel of edge-nearest values on the side facing
the GLO-30 mosaic (a ~90 m nearest extrapolation of the observed edge cell).
No padding on the outer sides, so pixels beyond the ring bbox at 9 E / 14 E
still fall through to 0 m as before. The 13 E seam had no gap (GLO-30 east
edge already overlaps the E013 strip's west edge by ~28 m), only the seam
kernel picking up the zero fill; per-strip mosaicking is enough there.

Before / after, per `data/scripts/terrain/check_ring_seams.py` (column mean
across the tile, metres; rel = (centre - mean(left,right)) / mean(left,right)):

10 E seam at z9 (col 113, seam-lon 9.9996 E):

| tile             | col 112 | col 113 before | col 113 after | col 114 | rel before | rel after |
|------------------|---------|----------------|---------------|---------|------------|-----------|
| `9/270/178.webp` | 730.1   | 341.2          | 730.2         | 731.9   | -53.3%     | -0.1%     |
| `9/270/179.webp` | 1492.3  | 699.6          | 1497.1        | 1503.5  | -53.3%     | -0.0%     |
| `9/270/180.webp` | 2205.4  | 1027.5         | 2197.7        | 2183.6  | -53.2%     | +0.1%     |
| `9/270/181.webp` | 2116.7  | 986.8          | 2110.7        | 2097.0  | -53.2%     | +0.2%     |
| `9/270/182.webp` | 967.5   | 448.8          | 959.5         | 947.9   | -53.1%     | +0.2%     |
| `9/270/183.webp` | 80.6    | 37.6           | 80.5          | 80.3    | -53.3%     | -0.0%     |

13 E seam at z9 (col 250, seam-lon 13.0003 E):

| tile             | col 249 | col 250 before | col 250 after | col 251 | rel before | rel after |
|------------------|---------|----------------|---------------|---------|------------|-----------|
| `9/274/178.webp` | 733.3   | 641.2          | 735.2         | 736.5   | -12.8%     | +0.0%     |
| `9/274/179.webp` | 1489.9  | 1314.6         | 1507.4        | 1522.9  | -12.7%     | +0.1%     |
| `9/274/180.webp` | 1651.4  | 1453.1         | 1651.2        | 1648.1  | -11.9%     | +0.1%     |

z8 spot checks: same seam columns at `8/135/{88..92}.webp` (col 56, 9.9989 E)
and `8/137/{89..91}.webp` (col 125, 13.0009 E) all fall within +/- 1 % of the
neighbour mean after the fix (previously off by tens of percent).

Cross-check against raw sources (single-pixel decode of the WebP vs the raw
GLO-90 / GLO-30 cell at the same lon/lat):

| tile pixel                                | before | after  | GLO-90 raw | note |
|-------------------------------------------|--------|--------|-----------|------|
| `8/135/90.webp` px (256, 56), 9.9989 E    | 2030.5 | 2828.2 | 2864.2    | fix restores height to within 1.3 % of the raw source (was ~30 % low) |
| `9/274/179.webp` px (100, 250), 13.0003 E | 1028.3 | 1179.0 | 1158.8    | fix aligns with raw source; was ~10 % low |
| `9/274/179.webp` px (256, 250), 13.0003 E | 1103.6 | 1265.5 | 1247.0    | fix aligns with raw source; was ~12 % low |

Changed tiles per zoom (from `git status`):

| zoom | changed | byte delta |
|------|---------|------------|
| z6   |   3     | +1 310     |
| z7   |   5     | +3 402     |
| z8   |  12     | +10 098    |
| z9   |  13     | -246       |
| z10  |   4     | -262       |
| z11  |   0     | 0          |
| z12  |   0     | 0          |

The 4 changed z10 tiles are all at `x=548, y in {359, 360, 361, 365}`. Their
Web-Mercator extent is 12.6563-13.0078 E, so each tile's easternmost column
(col 500) sits at 13.0000 E. That column is east of the GLO-30 mosaic's east
edge (12.99986 E) and previously read the merged-mosaic zero fill in the
10-13 E gap; the fix corrects it (e.g. `10/548/359.webp` col 500 row 499:
2507.8 -> 2788.7 m). No other core z10-12 tile crosses either seam, so
z11 and z12 are byte-identical.

Verification: `data/scripts/terrain/check_ring_seams.py` prints per-column
means at both seams at z9; run it after every rebuild.

## Notes

- No fabricated data. GLO-90 is measured elevation; it is labelled the same as
  the other DEM sources (`observed`), with its own resolution and datum
  recorded.
- Ice frames (bounds 9.5-13.5 E, 45.5-47.5 N) sit inside the widened DEM
  bounds; no change to the frames themselves.
