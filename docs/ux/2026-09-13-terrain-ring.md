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

## Notes

- No fabricated data. GLO-90 is measured elevation; it is labelled the same as
  the other DEM sources (`observed`), with its own resolution and datum
  recorded.
- Ice frames (bounds 9.5-13.5 E, 45.5-47.5 N) sit inside the widened DEM
  bounds; no change to the frames themselves.
