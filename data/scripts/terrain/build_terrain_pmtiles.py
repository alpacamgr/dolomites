"""
Build data/processed/terrain/dolomites-terrain.pmtiles per docs/04-data-contracts.md 2.1.
The archive is a pipeline intermediate (ADR 0006); export_tiles.py turns it into the served WebP tiles.

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe (rasterio 1.5, Pillow, pmtiles, scipy).

Inputs
------
17 TINITALY v1.1 10 m GeoTIFF tiles under data/raw/tinitaly-v1-1-10m/*.tif
(UTM 32N / EPSG:32632, nodata -9999).
9 Copernicus DEM GLO-30 GeoTIFF tiles under data/raw/copernicus-dem-glo30/
(EPSG:4326, ~30 m, no nodata over the study area). Fills the Austrian side
of the border (north of ~46.9 N) and any TINITALY voids inside Italy.
6 Copernicus DEM GLO-90 GeoTIFF tiles under data/raw/copernicus-dem-glo90/
(EPSG:4326, ~90 m, N45..N47 x E009 and E013). Covers the two outer strips of
the ring bbox 9-14 E / 45-48 N that lie outside GLO-30 coverage
(10-13 E / 45-48 N); ring z6-9 only, see docs/ux/2026-09-13-terrain-ring.md.

Output
------
data/processed/terrain/dolomites-terrain.pmtiles (intermediate)

Encoding: 512 px PNG tiles in EPSG:3857 with Mapbox Terrain-RGB heights
  height_m = -10000 + (R * 65536 + G * 256 + B) * 0.1
Zoom 6 to 12, bounds 9.0 to 14.0 E and 45.0 to 48.0 N (ring). At z6-9 tiles
cover the whole ring; at z10-12 tiles are emitted only where the tile
intersects the core bbox 10.3-12.7 E / 45.8-47.2 N (MapLibre falls back to
parent tiles for the missing z10-12 outside the core).

Choice of maxzoom
-----------------
At latitude 46.5 N in Web Mercator, the ground resolution of a 512 px tile at
zoom z is

  m/pix = 2 * pi * R * cos(lat) / (2^z * 512)  ,  R = 6378137 m
        = 40 075 016.7 * cos(46.5 deg) / (2^z * 512)
        = 53 892 / 2^z  m/pixel

giving 12: 13.16 m/pixel, 11: 26.31 m/pixel, 10: 52.63 m/pixel.

Source resolution is 10 m/pixel (TINITALY). The data-honesty policy (docs/03,
rule 6) forbids upsampling that creates false detail. Target guideline is
"not finer than about 0.7 x source" -> at least 7 m/pixel. z12 (13.2 m/pixel)
is 1.32 x source, so tile pixels are safely coarser than source pixels.
z13 would give 6.6 m/pixel, i.e. tile pixels ~35 % finer than source; that
crosses the honesty threshold, so we stop at z12.

For zoom 6..12 that is 1, 3, 9, 25, 78, 260, 926 = ~1300 tiles across the
bbox (approximate; actual is counted at build time).

Border fill (GLO-30 behind TINITALY)
------------------------------------
TINITALY nodata (-9999) is mostly the Austrian side of the border plus the
Marmolada north face and a couple of Alpine ridge cells. Instead of encoding
those as sea level (0 m, an obvious cliff at the border), we mosaic in
Copernicus DEM GLO-30 heights where TINITALY has no value.

Along the TINITALY validity edge we cross-fade to GLO-30 over FEATHER_M
metres of ground distance using a cosine ramp on the distance-to-edge
computed with scipy.ndimage.distance_transform_edt. The weights are geometric
(distance-based, not derived from either source's heights), so the transition
does not fabricate elevations that neither source reports.

Both DEMs are orthometric (heights above a geoid, not the ellipsoid):
- GLO-30: "The vertical reference datum is the Earth Gravitational Model 2008
  (EGM2008; EPSG 3855)" - Copernicus DEM Product Handbook v5.0 (2022-11-29), sec. 1.2.
- TINITALY 1.1: neither the accompanying notes nor the download pages state a
  vertical datum; the DEM is interpolated from topographic contour lines and
  spot heights. Checked empirically: TINITALY minus GLO-30 over the bbox has a
  median of about -2 m (see README), whereas an ellipsoidal source would be
  offset by the ~47 m geoid undulation here.
No vertical shift is applied at the seam.

Idempotence
-----------
- If dolomites-terrain.pmtiles already exists and --force is not passed the
  script exits.
- No intermediate GeoTIFF is written; the GLO-30 mosaic is built in memory
  once at start and referenced by rasterio.warp.reproject per output tile.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from pmtiles.tile import Compression, HeaderDict, TileType, zxy_to_tileid
from pmtiles.writer import Writer
from rasterio.enums import Resampling
from rasterio.merge import merge as rio_merge
from rasterio.vrt import WarpedVRT
from rasterio.warp import Resampling as WarpResampling
from rasterio.warp import reproject, transform_bounds
from scipy.ndimage import distance_transform_edt

RAW_DIR = Path(r"E:/Projects/Dolomites/data/raw/tinitaly-v1-1-10m")
GLO30_DIR = Path(r"E:/Projects/Dolomites/data/raw/copernicus-dem-glo30")
GLO90_DIR = Path(r"E:/Projects/Dolomites/data/raw/copernicus-dem-glo90")
OUT_DIR = Path(r"E:/Projects/Dolomites/app/public/data/terrain")
PROCESSED_DIR = Path(r"E:/Projects/Dolomites/data/processed/terrain")
PREVIEW_DIR = PROCESSED_DIR / "preview"

DATASET_ID = "tinitaly-v1-1-10m"
DATASET_ID_FILL = "copernicus-dem-glo30"
DATASET_ID_RING = "copernicus-dem-glo90"
ATTRIBUTION = (
    "TINITALY 1.1 &copy; INGV (Tarquini et al. 2023, "
    "<a href='https://doi.org/10.13127/tinitaly/1.1'>doi:10.13127/tinitaly/1.1</a>), CC BY 4.0; "
    "outside Italy: produced using Copernicus WorldDEM-30 &copy; DLR e.V. 2010-2014 "
    "and &copy; Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS "
    "by the European Union and ESA; all rights reserved; "
    "outer area (9-14 E, 45-48 N outside 10-13 E): produced using Copernicus "
    "WorldDEM-90 with the same rights and attribution"
)

# Widened ring bbox for z6-9 coverage (docs/ux/2026-09-13-terrain-ring.md).
BBOX_LL = (9.0, 45.0, 14.0, 48.0)
# Original core bbox: TINITALY + GLO-30, kept for z10-12.
CORE_BBOX_LL = (10.3, 45.8, 12.7, 47.2)
# Ring source (GLO-90) is honesty-capped at z9 (105 m/px at 46.5 N is >= 0.7 x 90 m).
MAX_Z_RING = 9
MIN_Z = 6
MAX_Z = 12
TILE_PX = 512
EARTH_R = 6378137.0
ORIGIN_M = math.pi * EARTH_R  # ~20037508.342789
FEATHER_M = 300.0  # ground-metres of cross-fade along the TINITALY validity edge
TINITALY_NODATA = -9999.0
# Sentinel for "no GLO-30 data here" so the reprojection falls through to GLO-90
# in the outer ring strips (9-10 E and 13-14 E). Chosen well below any real
# elevation so it never collides with a valid height.
GLO_NODATA = -32768.0


# ---------------------------------------------------------------- Web Mercator

def lonlat_to_merc(lon: float, lat: float) -> tuple[float, float]:
    x = math.radians(lon) * EARTH_R
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * EARTH_R
    return x, y


def tile_bounds_m(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return the Web Mercator bounds (minX, minY, maxX, maxY) of tile (z,x,y)."""
    n = 2 ** z
    span = 2 * ORIGIN_M / n
    minx = -ORIGIN_M + x * span
    maxx = minx + span
    maxy = ORIGIN_M - y * span
    miny = maxy - span
    return (minx, miny, maxx, maxy)


def tile_range(z: int, bbox_ll: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    """Return (xmin, ymin, xmax, ymax) tile indices at zoom z covering bbox."""
    min_x_m, min_y_m = lonlat_to_merc(bbox_ll[0], bbox_ll[1])
    max_x_m, max_y_m = lonlat_to_merc(bbox_ll[2], bbox_ll[3])
    n = 2 ** z
    span = 2 * ORIGIN_M / n
    tx0 = int((min_x_m + ORIGIN_M) // span)
    tx1 = int((max_x_m + ORIGIN_M) // span)
    ty0 = int((ORIGIN_M - max_y_m) // span)
    ty1 = int((ORIGIN_M - min_y_m) // span)
    return tx0, ty0, tx1, ty1


# ---------------------------------------------------------------- Terrain-RGB

def encode_terrain_rgb(heights: np.ndarray) -> np.ndarray:
    """Encode heights (float32 metres) into Mapbox Terrain-RGB PNG channels."""
    v = ((heights + 10000.0) * 10.0)  # -10000..~6500 m -> 0..~165000
    # Clamp to the 24-bit valid range (0..16777215)
    np.clip(v, 0, 16777215, out=v)
    vi = v.astype(np.uint32)
    r = ((vi >> 16) & 0xFF).astype(np.uint8)
    g = ((vi >> 8) & 0xFF).astype(np.uint8)
    b = (vi & 0xFF).astype(np.uint8)
    return np.stack([r, g, b], axis=-1)


def decode_terrain_rgb(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.int64)
    g = rgb[..., 1].astype(np.int64)
    b = rgb[..., 2].astype(np.int64)
    return -10000.0 + (r * 65536 + g * 256 + b) * 0.1


# ---------------------------------------------------------------- Sources

def open_tinitaly() -> list:
    tifs = sorted(RAW_DIR.glob("*.tif"))
    if not tifs:
        raise SystemExit(f"no TINITALY tifs in {RAW_DIR}; run fetch_tinitaly.py")
    print(f"opening {len(tifs)} TINITALY tiles")
    return [rasterio.open(p) for p in tifs]


def load_glo30_mosaic() -> tuple[np.ndarray, rasterio.Affine]:
    """Merge the 9 GLO-30 tiles into a single in-memory float32 array."""
    tifs = sorted(GLO30_DIR.glob("Copernicus_DSM_COG_10_*_DEM.tif"))
    if not tifs:
        raise SystemExit(f"no GLO-30 tifs in {GLO30_DIR}; run fetch_copernicus_glo30.py")
    print(f"opening {len(tifs)} GLO-30 tiles and merging")
    dss = [rasterio.open(p) for p in tifs]
    try:
        merged, transform = rio_merge(dss, method="first", resampling=Resampling.nearest)
    finally:
        for ds in dss:
            ds.close()
    arr = merged[0].astype("float32")
    print(f"GLO-30 mosaic: {arr.shape} float32, {arr.nbytes/1e6:.0f} MB")
    return arr, transform


def load_glo90_mosaic() -> tuple[np.ndarray, rasterio.Affine] | None:
    """Merge the GLO-90 outer-ring tiles into a single in-memory float32 array.
    Returns None when no GLO-90 tile is present (build proceeds without a ring)."""
    tifs = sorted(GLO90_DIR.glob("Copernicus_DSM_COG_30_*_DEM.tif"))
    if not tifs:
        print(f"no GLO-90 tifs in {GLO90_DIR}; ring will read as GLO-30 nodata (0 m)")
        return None
    print(f"opening {len(tifs)} GLO-90 tiles and merging")
    dss = [rasterio.open(p) for p in tifs]
    try:
        merged, transform = rio_merge(dss, method="first", resampling=Resampling.nearest)
    finally:
        for ds in dss:
            ds.close()
    arr = merged[0].astype("float32")
    print(f"GLO-90 mosaic: {arr.shape} float32, {arr.nbytes/1e6:.0f} MB")
    return arr, transform


def tile_intersects_bbox(z: int, x: int, y: int, bbox_ll: tuple[float, float, float, float]) -> bool:
    """True when the tile (z,x,y) intersects the lon/lat bbox in Web Mercator."""
    tb = tile_bounds_m(z, x, y)
    bx0, by0 = lonlat_to_merc(bbox_ll[0], bbox_ll[1])
    bx1, by1 = lonlat_to_merc(bbox_ll[2], bbox_ll[3])
    return tb[2] > bx0 and tb[0] < bx1 and tb[3] > by0 and tb[1] < by1


# ---------------------------------------------------------------- Tile read

def build_pmtiles(out_path: Path) -> dict:
    tin_datasets = open_tinitaly()
    src_info = [
        (ds, ds.bounds, ds.nodata if ds.nodata is not None else TINITALY_NODATA)
        for ds in tin_datasets
    ]
    glo_arr, glo_transform = load_glo30_mosaic()
    glo90 = load_glo90_mosaic()
    glo90_arr, glo90_transform = (None, None) if glo90 is None else glo90

    from pyproj import Transformer
    to_utm = Transformer.from_crs("EPSG:3857", tin_datasets[0].crs, always_xy=True)

    def read_tinitaly_window(e_minx, e_miny, e_maxx, e_maxy, W, H) -> np.ndarray:
        """Read TINITALY heights into a (H, W) float32 array covering the given
        Web-Mercator bbox. Returns TINITALY_NODATA where no TINITALY data exists."""
        # Convert bbox corners to UTM to find intersecting sources
        xs = [e_minx, e_maxx, e_minx, e_maxx]
        ys = [e_miny, e_miny, e_maxy, e_maxy]
        ux, uy = to_utm.transform(xs, ys)
        u_minx, u_maxx = min(ux), max(ux)
        u_miny, u_maxy = min(uy), max(uy)
        buf = 20.0
        u_minx -= buf; u_miny -= buf; u_maxx += buf; u_maxy += buf
        keep = [
            ds for ds, b, _nd in src_info
            if b.right > u_minx and b.left < u_maxx and b.top > u_miny and b.bottom < u_maxy
        ]
        if not keep:
            return np.full((H, W), TINITALY_NODATA, dtype=np.float32)
        merged, transform = rio_merge(
            keep,
            bounds=(u_minx, u_miny, u_maxx, u_maxy),
            nodata=TINITALY_NODATA,
            resampling=Resampling.nearest,
            method="first",
        )
        # Reproject the little UTM window to the padded Web Mercator patch
        from rasterio.io import MemoryFile
        with MemoryFile() as memf:
            with memf.open(
                driver="GTiff",
                height=merged.shape[1],
                width=merged.shape[2],
                count=1,
                dtype="float32",
                crs=tin_datasets[0].crs,
                transform=transform,
                nodata=TINITALY_NODATA,
            ) as tmp:
                tmp.write(merged[0].astype("float32"), 1)
            with memf.open() as tmp:
                with WarpedVRT(
                    tmp,
                    crs="EPSG:3857",
                    transform=rasterio.transform.from_bounds(
                        e_minx, e_miny, e_maxx, e_maxy, W, H
                    ),
                    width=W,
                    height=H,
                    resampling=WarpResampling.bilinear,
                    src_nodata=TINITALY_NODATA,
                    nodata=TINITALY_NODATA,
                ) as vrt:
                    return vrt.read(1).astype(np.float32)

    def read_glo30_window(e_minx, e_miny, e_maxx, e_maxy, W, H) -> np.ndarray:
        """Reproject the pre-merged GLO-30 mosaic into a (H, W) float32 array.
        Where GLO-30 has no data (outside its 10-13 E / 45-48 N coverage), fall
        through to GLO-90 (outer ring). Where neither source has data, keep 0.
        """
        dst = np.full((H, W), GLO_NODATA, dtype=np.float32)
        dst_transform = rasterio.transform.from_bounds(
            e_minx, e_miny, e_maxx, e_maxy, W, H
        )
        reproject(
            source=glo_arr,
            destination=dst,
            src_transform=glo_transform,
            src_crs="EPSG:4326",
            dst_transform=dst_transform,
            dst_crs="EPSG:3857",
            resampling=WarpResampling.bilinear,
            src_nodata=None,
            dst_nodata=GLO_NODATA,
            init_dest_nodata=False,
        )
        if glo90_arr is not None:
            missing = dst == GLO_NODATA
            if missing.any():
                fill = np.full((H, W), GLO_NODATA, dtype=np.float32)
                reproject(
                    source=glo90_arr,
                    destination=fill,
                    src_transform=glo90_transform,
                    src_crs="EPSG:4326",
                    dst_transform=dst_transform,
                    dst_crs="EPSG:3857",
                    resampling=WarpResampling.bilinear,
                    src_nodata=None,
                    dst_nodata=GLO_NODATA,
                    init_dest_nodata=False,
                )
                dst = np.where(missing, fill, dst)
        # Any remaining nodata (should not happen inside the ring bbox) becomes 0
        dst[dst == GLO_NODATA] = 0.0
        return dst

    def read_tile_hybrid(z: int, x: int, y: int) -> np.ndarray:
        """Return a (TILE_PX, TILE_PX) height array, TINITALY first, GLO-30
        behind, with a FEATHER_M-wide cosine cross-fade along the TINITALY
        validity edge."""
        minx_m, miny_m, maxx_m, maxy_m = tile_bounds_m(z, x, y)
        span_x = maxx_m - minx_m
        px_planar = span_x / TILE_PX  # projection-plane metres per pixel
        # Ground metres per pixel at the tile centre latitude
        lat_c = math.degrees(math.atan(math.sinh((miny_m + maxy_m) / 2 / EARTH_R)))
        ground_m_per_pix = px_planar * math.cos(math.radians(lat_c))
        # Pad by feather + 4 pixels of safety so the distance transform reflects
        # seams sitting just outside the tile.
        pad = int(math.ceil(FEATHER_M / max(ground_m_per_pix, 1e-6))) + 4
        W = TILE_PX + 2 * pad
        H = TILE_PX + 2 * pad
        e_minx = minx_m - pad * px_planar
        e_maxx = maxx_m + pad * px_planar
        e_miny = miny_m - pad * px_planar
        e_maxy = maxy_m + pad * px_planar

        tin = read_tinitaly_window(e_minx, e_miny, e_maxx, e_maxy, W, H)
        tin_valid = tin != TINITALY_NODATA

        # Fast path A: no TINITALY within padded window -> pure GLO-30
        if not tin_valid.any():
            glo = read_glo30_window(e_minx, e_miny, e_maxx, e_maxy, W, H)
            return glo[pad:pad + TILE_PX, pad:pad + TILE_PX]
        # Fast path B: TINITALY covers the whole padded window -> pure TINITALY
        if tin_valid.all():
            return tin[pad:pad + TILE_PX, pad:pad + TILE_PX]

        # Feather blend
        glo = read_glo30_window(e_minx, e_miny, e_maxx, e_maxy, W, H)
        # distance_transform_edt returns 0 at invalid pixels and, at valid
        # pixels, the distance to the nearest invalid pixel (in the metric
        # given by `sampling`).
        dist = distance_transform_edt(tin_valid, sampling=(ground_m_per_pix, ground_m_per_pix))
        t = np.clip(dist / FEATHER_M, 0.0, 1.0)
        w = 0.5 - 0.5 * np.cos(np.pi * t)  # cosine smoothstep
        # Where TINITALY is invalid, w == 0, so tin is never sampled there.
        tin_safe = np.where(tin_valid, tin, 0.0)
        out = w * tin_safe + (1.0 - w) * glo
        return out[pad:pad + TILE_PX, pad:pad + TILE_PX].astype(np.float32)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # PMTiles writer needs tiles in ascending tileid order (clustered layout).
    # z6-9 span the whole ring bbox; z10-12 are emitted only where the tile
    # intersects the core bbox (MapLibre falls back to parent tiles outside).
    tiles_by_id: list[tuple[int, int, int, int]] = []
    per_zoom_counts: dict[int, int] = {}
    for z in range(MIN_Z, MAX_Z + 1):
        bbox = BBOX_LL if z <= MAX_Z_RING else CORE_BBOX_LL
        tx0, ty0, tx1, ty1 = tile_range(z, bbox)
        for x in range(tx0, tx1 + 1):
            for y in range(ty0, ty1 + 1):
                # z10-12: the core bbox may partially cover a tile that also lies outside;
                # keep only tiles whose Web Mercator extent actually intersects the core.
                if z > MAX_Z_RING and not tile_intersects_bbox(z, x, y, CORE_BBOX_LL):
                    continue
                tiles_by_id.append((zxy_to_tileid(z, x, y), z, x, y))
                per_zoom_counts[z] = per_zoom_counts.get(z, 0) + 1
    tiles_by_id.sort(key=lambda t: t[0])
    print(f"total tiles to build: {len(tiles_by_id)}")
    for z in sorted(per_zoom_counts):
        print(f"  z{z}: {per_zoom_counts[z]} tiles")

    t0 = time.time()
    # Build into data/processed/terrain/ (never at the final path, which the app
    # may be reading), then atomically rename over the archive (same volume).
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = PROCESSED_DIR / (out_path.name + ".part")
    if tmp_path.exists():
        tmp_path.unlink()

    written = 0
    min_lon_e7 = int(BBOX_LL[0] * 10_000_000)
    min_lat_e7 = int(BBOX_LL[1] * 10_000_000)
    max_lon_e7 = int(BBOX_LL[2] * 10_000_000)
    max_lat_e7 = int(BBOX_LL[3] * 10_000_000)
    # Center on the core bbox so a default zoom-in lands on the Dolomites,
    # not the widened ring's geometric centre.
    center_lon_e7 = int((CORE_BBOX_LL[0] + CORE_BBOX_LL[2]) / 2 * 10_000_000)
    center_lat_e7 = int((CORE_BBOX_LL[1] + CORE_BBOX_LL[3]) / 2 * 10_000_000)
    center_zoom = 10

    log_every = max(1, len(tiles_by_id) // 40)
    with open(tmp_path, "wb") as fh:
        w = Writer(fh)
        for i, (tid, z, x, y) in enumerate(tiles_by_id, 1):
            heights = read_tile_hybrid(z, x, y)
            rgb = encode_terrain_rgb(heights)
            img = Image.fromarray(rgb, mode="RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=False, compress_level=6)
            w.write_tile(tid, buf.getvalue())
            written += 1
            if i % log_every == 0 or i == len(tiles_by_id):
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(tiles_by_id) - i) / rate if rate > 0 else 0
                print(f"  {i}/{len(tiles_by_id)} (z={z}) - {rate:.1f} tiles/s - eta {eta/60:.1f} min")

        header = HeaderDict(
            version=3,
            root_offset=0,
            root_length=0,
            metadata_offset=0,
            metadata_length=0,
            leaf_directory_offset=0,
            leaf_directory_length=0,
            tile_data_offset=0,
            tile_data_length=0,
            addressed_tiles_count=0,
            tile_entries_count=0,
            tile_contents_count=0,
            clustered=True,
            internal_compression=Compression.GZIP,
            tile_compression=Compression.NONE,  # PNG already compressed
            tile_type=TileType.PNG,
            min_zoom=MIN_Z,
            max_zoom=MAX_Z,
            min_lon_e7=min_lon_e7,
            min_lat_e7=min_lat_e7,
            max_lon_e7=max_lon_e7,
            max_lat_e7=max_lat_e7,
            center_zoom=center_zoom,
            center_lon_e7=center_lon_e7,
            center_lat_e7=center_lat_e7,
        )
        metadata = {
            "name": "Dolomites terrain (TINITALY 10 m + Copernicus GLO-30 + GLO-90 ring)",
            "description": (
                "Elevation for the Dolomites, Mapbox Terrain-RGB. "
                "Core (10.3-12.7 E, 45.8-47.2 N, z6-12): TINITALY inside Italy, "
                "GLO-30 fills the Austrian side and any TINITALY voids, "
                "cross-faded over 300 m along the seam. "
                "Ring (9-14 E, 45-48 N, z6-9 only): GLO-30 where available, "
                "GLO-90 in the two outer strips (E009 and E013)."
            ),
            "attribution": ATTRIBUTION,
            "encoding": "mapbox",
            "format": "png",
            "type": "baselayer",
            "tilesize": TILE_PX,
            "minzoom": MIN_Z,
            "maxzoom": MAX_Z,
            "bounds": list(BBOX_LL),
            "center": [
                (CORE_BBOX_LL[0] + CORE_BBOX_LL[2]) / 2,
                (CORE_BBOX_LL[1] + CORE_BBOX_LL[3]) / 2,
                center_zoom,
            ],
            "source_datasets": [DATASET_ID, DATASET_ID_FILL, DATASET_ID_RING],
            "seam_feather_m": FEATHER_M,
            "core_bbox": list(CORE_BBOX_LL),
            "ring_max_zoom": MAX_Z_RING,
        }
        w.finalize(header, metadata)
        fh.flush()
        os.fsync(fh.fileno())

    atomic_replace(tmp_path, out_path)
    print(f"finalised {out_path} in {time.time()-t0:.0f} s; size {out_path.stat().st_size/1e6:.1f} MB")
    for ds in tin_datasets:
        ds.close()
    return {"tiles_written": written}


def atomic_replace(src: Path, dst: Path, attempts: int = 30) -> None:
    """os.replace = atomic rename on one volume. On Windows it raises
    PermissionError while another process holds dst open without delete
    sharing; retry instead of ever writing into dst in place."""
    for i in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == attempts - 1:
                raise SystemExit(f"could not replace {dst} (held open?); new file left at {src}")
            time.sleep(2)


# ---------------------------------------------------------------- Verification

def _tile_xy_for_lonlat(z: int, lon: float, lat: float) -> tuple[int, int, int, int]:
    """Return (x, y, px, py) for the tile at zoom z containing (lon, lat) and
    the pixel indices (px, py) within that tile."""
    x_m, y_m = lonlat_to_merc(lon, lat)
    n = 2 ** z
    span = 2 * ORIGIN_M / n
    x = int((x_m + ORIGIN_M) // span)
    y = int((ORIGIN_M - y_m) // span)
    tb = tile_bounds_m(z, x, y)
    fx = (x_m - tb[0]) / (tb[2] - tb[0])
    fy = (tb[3] - y_m) / (tb[3] - tb[1])
    px = int(fx * TILE_PX)
    py = int(fy * TILE_PX)
    px = max(0, min(TILE_PX - 1, px))
    py = max(0, min(TILE_PX - 1, py))
    return x, y, px, py


def _read_tinitaly_at(tin_datasets, to_utm, lon: float, lat: float) -> float | None:
    x_m, y_m = lonlat_to_merc(lon, lat)
    utm_x, utm_y = to_utm.transform(x_m, y_m)
    for ds in tin_datasets:
        b = ds.bounds
        if b.left <= utm_x < b.right and b.bottom <= utm_y < b.top:
            row, col = ds.index(utm_x, utm_y)
            v = ds.read(1, window=((row, row + 1), (col, col + 1)))
            val = float(v[0, 0])
            if val == TINITALY_NODATA:
                return None
            return val
    return None


def _read_glo30_at(glo_arr, glo_transform, lon: float, lat: float) -> float | None:
    inv = ~glo_transform
    col_f, row_f = inv * (lon, lat)
    col = int(col_f)
    row = int(row_f)
    if not (0 <= row < glo_arr.shape[0] and 0 <= col < glo_arr.shape[1]):
        return None
    return float(glo_arr[row, col])


def verify_pmtiles(
    archive: Path,
    zoom_samples: list[tuple[int, int, int]],
    lonlat_samples: list[tuple[str, float, float, str]],
) -> dict:
    """Read back a few tiles: (a) at three zooms, tile centre vs raw source at
    the same point; (b) at six named lon/lat points (three Austrian, three
    Italian), z=12, decoded pixel vs the appropriate raw source."""
    from pmtiles.reader import MmapSource, Reader
    from pyproj import Transformer

    tin_datasets = [rasterio.open(p) for p in sorted(RAW_DIR.glob("*.tif"))]
    to_utm = Transformer.from_crs("EPSG:3857", tin_datasets[0].crs, always_xy=True)
    glo_arr, glo_transform = load_glo30_mosaic()

    zoom_results = []
    lonlat_results = []
    with open(archive, "rb") as fh:
        src = MmapSource(fh)
        rd = Reader(src)

        # (a) zoom samples: tile centre, compared to raw TINITALY (may be None
        # if the centre is outside Italy - then compared to GLO-30 instead).
        for z, x, y in zoom_samples:
            data = rd.get(z, x, y)
            if data is None:
                zoom_results.append({"z": z, "x": x, "y": y, "error": "tile missing"})
                continue
            img = Image.open(io.BytesIO(data))
            arr = np.array(img)
            h = decode_terrain_rgb(arr)
            cx = cy = TILE_PX // 2
            tb = tile_bounds_m(z, x, y)
            world_x = tb[0] + (cx + 0.5) / TILE_PX * (tb[2] - tb[0])
            world_y = tb[3] - (cy + 0.5) / TILE_PX * (tb[3] - tb[1])
            # Convert back to lonlat for source lookups
            lon = math.degrees(world_x / EARTH_R)
            lat = math.degrees(math.atan(math.sinh(world_y / EARTH_R)))
            tin_val = _read_tinitaly_at(tin_datasets, to_utm, lon, lat)
            glo_val = _read_glo30_at(glo_arr, glo_transform, lon, lat)
            zoom_results.append({
                "z": z, "x": x, "y": y,
                "centre_lonlat": [lon, lat],
                "tile_height_center_m": float(h[cy, cx]),
                "tinitaly_at_center_m": tin_val,
                "glo30_at_center_m": glo_val,
                "diff_vs_tinitaly_m": None if tin_val is None else float(h[cy, cx]) - tin_val,
                "diff_vs_glo30_m": None if glo_val is None else float(h[cy, cx]) - glo_val,
                "tile_min_m": float(h.min()),
                "tile_max_m": float(h.max()),
            })

        # (b) named lon/lat samples at z=12
        z = 12
        for name, lon, lat, expected_src in lonlat_samples:
            x, y, px, py = _tile_xy_for_lonlat(z, lon, lat)
            data = rd.get(z, x, y)
            if data is None:
                lonlat_results.append({
                    "name": name, "lon": lon, "lat": lat, "z": z,
                    "error": f"tile z{z}/{x}/{y} missing",
                })
                continue
            img = Image.open(io.BytesIO(data))
            arr = np.array(img)
            h = decode_terrain_rgb(arr)
            tile_h = float(h[py, px])
            tin_val = _read_tinitaly_at(tin_datasets, to_utm, lon, lat)
            glo_val = _read_glo30_at(glo_arr, glo_transform, lon, lat)
            ref_val = tin_val if expected_src == "tinitaly" else glo_val
            lonlat_results.append({
                "name": name,
                "lon": lon, "lat": lat, "z": z, "x": x, "y": y, "px": px, "py": py,
                "expected_source": expected_src,
                "tile_height_m": tile_h,
                "tinitaly_at_point_m": tin_val,
                "glo30_at_point_m": glo_val,
                "diff_vs_expected_m": None if ref_val is None else tile_h - ref_val,
            })

    for ds in tin_datasets:
        ds.close()
    return {"zoom_samples": zoom_results, "lonlat_samples": lonlat_results}


def make_hillshade_preview(
    archive: Path,
    out_png: Path,
    z: int = 9,
    lat_range: tuple[float, float] | None = None,
) -> None:
    """Read all z tiles from the archive covering the (optionally lat-clipped)
    bbox, assemble, hillshade, save preview PNG."""
    from pmtiles.reader import MmapSource, Reader
    bbox = BBOX_LL
    if lat_range is not None:
        bbox = (BBOX_LL[0], lat_range[0], BBOX_LL[2], lat_range[1])
    tx0, ty0, tx1, ty1 = tile_range(z, bbox)
    cols = tx1 - tx0 + 1
    rows = ty1 - ty0 + 1
    print(f"preview mosaic z={z}: {cols}x{rows} tiles ({cols*TILE_PX}x{rows*TILE_PX} px)")
    mosaic = np.zeros((rows * TILE_PX, cols * TILE_PX), dtype=np.float32)
    with open(archive, "rb") as fh:
        src = MmapSource(fh)
        rd = Reader(src)
        for xi, x in enumerate(range(tx0, tx1 + 1)):
            for yi, y in enumerate(range(ty0, ty1 + 1)):
                data = rd.get(z, x, y)
                if data is None:
                    continue
                arr = np.array(Image.open(io.BytesIO(data)))
                h = decode_terrain_rgb(arr).astype(np.float32)
                mosaic[yi*TILE_PX:(yi+1)*TILE_PX, xi*TILE_PX:(xi+1)*TILE_PX] = h
    az = math.radians(315.0)
    alt = math.radians(45.0)
    # Approximate pixel size in metres at the mosaic centre latitude
    lat_c = (bbox[1] + bbox[3]) / 2
    m_per_pix = (2 * ORIGIN_M / (2 ** z) / TILE_PX) * math.cos(math.radians(lat_c))
    dzdx = (mosaic[1:-1, 2:] - mosaic[1:-1, :-2]) / (2 * m_per_pix)
    dzdy = (mosaic[2:, 1:-1] - mosaic[:-2, 1:-1]) / (2 * m_per_pix)
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(-dzdx, dzdy)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    shade = np.clip(shade, 0, 1)
    img8 = (shade * 255).astype(np.uint8)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img8, mode="L").save(out_png, optimize=True)
    print(f"wrote {out_png} ({out_png.stat().st_size/1024:.0f} kB)")


# ---------------------------------------------------------------- CLI

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite existing archive")
    ap.add_argument("--verify-only", action="store_true", help="skip build; verify existing")
    args = ap.parse_args()

    out_path = PROCESSED_DIR / "dolomites-terrain.pmtiles"  # intermediate (ADR 0006)
    if out_path.exists() and not args.force and not args.verify_only:
        print(f"{out_path} exists ({out_path.stat().st_size/1e6:.1f} MB); pass --force to rebuild")
    else:
        if not args.verify_only:
            build_pmtiles(out_path)

    # (a) three-zoom bbox-centre samples
    zoom_samples = []
    for z in (8, 10, 12):
        tx0, ty0, tx1, ty1 = tile_range(z, BBOX_LL)
        cx = (tx0 + tx1) // 2
        cy = (ty0 + ty1) // 2
        zoom_samples.append((z, cx, cy))

    # (b) three Austrian (should match GLO-30), three Italian (should match TINITALY)
    lonlat_samples = [
        # 46.95 N 11.40 E was tried first but lies inside Italy (TINITALY 1160.8 m).
        ("Austria: Wipptal N of Brenner",  11.45, 47.05, "glo30"),
        ("Austria: 47.10 N 12.00 E",       12.00, 47.10, "glo30"),
        ("Austria: East Tyrol",            12.30, 46.90, "glo30"),
        ("Italy: Marmolada area",          11.85, 46.44, "tinitaly"),
        ("Italy: Cortina d'Ampezzo",       12.14, 46.54, "tinitaly"),
        ("Italy: Bolzano",                 11.35, 46.50, "tinitaly"),
    ]

    checks = verify_pmtiles(out_path, zoom_samples, lonlat_samples)
    for c in checks["zoom_samples"]:
        print("zoom  :", json.dumps(c))
    for c in checks["lonlat_samples"]:
        print("point :", json.dumps(c))

    ver_tmp = PROCESSED_DIR / "verification.json.part"
    ver_tmp.write_text(json.dumps(checks, indent=2) + "\n")
    atomic_replace(ver_tmp, OUT_DIR / "verification.json")

    # Full-bbox z=9 hillshade preview (kept from previous pipeline)
    preview = PREVIEW_DIR / "dolomites-terrain-z9-hillshade.png"
    if not preview.exists() or args.force:
        make_hillshade_preview(out_path, preview, z=9)

    # Northern-edge preview for inspecting the TINITALY / GLO-30 seam.
    border_preview = PREVIEW_DIR / "border-fill.png"
    if not border_preview.exists() or args.force:
        make_hillshade_preview(out_path, border_preview, z=10, lat_range=(46.7, 47.2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
