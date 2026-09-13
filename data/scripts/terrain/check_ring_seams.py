"""
Check the served terrain-elevation tiles for seam artefacts along the
GLO-30 / GLO-90 boundaries at 10 E and 13 E in the outer ring.

Motivated by the reviewer's finding (2026-09-13) that at zoom 9 the WebP
column containing lon ~= 10.0 / 13.0 E reads several hundred metres below
its neighbours: `rasterio.merge.merge` fills the 10-13 E gap of the
GLO-90 mosaic with 0 m (GLO-90 tiles set no nodata), and the subsequent
reproject with `src_nodata=None` treats those zeros as valid heights, so
bilinear resampling next to 10 E and 13 E mixes real elevations with the
fill.

Terrain-RGB decode:  h = -10000 + (R*65536 + G*256 + B) * 0.1

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe (Pillow, numpy).

Usage:
  check_ring_seams.py                  # default tiles listed below
  check_ring_seams.py --tiles A B ...  # any z/x/y.webp files
  check_ring_seams.py --json OUT       # write the per-column summary as JSON

For each tile the script prints, for the columns straddling the seam
(computed from the tile's Web-Mercator bounds), the mean height across
the tile column together with its left and right neighbour, and flags
any column whose mean deviates by more than a few percent from the
mean of the two neighbours.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"E:/Projects/Dolomites")
DEFAULT_TILES = [
    # z9 ring tiles that straddle 10 E and 13 E (from the reviewer's evidence).
    ROOT / "app/public/data/terrain/elevation/9/270/178.webp",
    ROOT / "app/public/data/terrain/elevation/9/270/179.webp",
    ROOT / "app/public/data/terrain/elevation/9/270/180.webp",
    ROOT / "app/public/data/terrain/elevation/9/270/181.webp",
    ROOT / "app/public/data/terrain/elevation/9/270/182.webp",
    ROOT / "app/public/data/terrain/elevation/9/270/183.webp",
    ROOT / "app/public/data/terrain/elevation/9/274/178.webp",
    ROOT / "app/public/data/terrain/elevation/9/274/179.webp",
    ROOT / "app/public/data/terrain/elevation/9/274/180.webp",
]
SEAM_LONS = (10.0, 13.0)
TILE_PX = 512
EARTH_R = 6378137.0
ORIGIN_M = math.pi * EARTH_R
# Flag columns whose mean is >5% below the mean of the two neighbours.
FLAG_FRAC = 0.05


def decode_terrain_rgb(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.int64)
    g = rgb[..., 1].astype(np.int64)
    b = rgb[..., 2].astype(np.int64)
    return -10000.0 + (r * 65536 + g * 256 + b) * 0.1


def tile_bounds_lonlat(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return (minLon, minLat, maxLon, maxLat) of tile (z, x, y)."""
    n = 2 ** z
    span_m = 2 * ORIGIN_M / n
    minx_m = -ORIGIN_M + x * span_m
    maxx_m = minx_m + span_m
    maxy_m = ORIGIN_M - y * span_m
    miny_m = maxy_m - span_m
    min_lon = math.degrees(minx_m / EARTH_R)
    max_lon = math.degrees(maxx_m / EARTH_R)
    min_lat = math.degrees(math.atan(math.sinh(miny_m / EARTH_R)))
    max_lat = math.degrees(math.atan(math.sinh(maxy_m / EARTH_R)))
    return (min_lon, min_lat, max_lon, max_lat)


def col_for_lon(lon: float, min_lon_m: float, max_lon_m: float) -> int:
    """Return the 0-based pixel column index in a 512-px tile for a given lon."""
    lon_m = math.radians(lon) * EARTH_R
    frac = (lon_m - min_lon_m) / (max_lon_m - min_lon_m)
    return int(math.floor(frac * TILE_PX))


def parse_zxy(path: Path) -> tuple[int, int, int]:
    z = int(path.parent.parent.name)
    x = int(path.parent.name)
    y = int(path.stem)
    return z, x, y


def check_tile(path: Path) -> dict:
    z, x, y = parse_zxy(path)
    minlon, minlat, maxlon, maxlat = tile_bounds_lonlat(z, x, y)
    minx_m = math.radians(minlon) * EARTH_R
    maxx_m = math.radians(maxlon) * EARTH_R
    img = np.asarray(Image.open(path).convert("RGB"))
    h = decode_terrain_rgb(img)  # (H, W) heights in metres
    result = {
        "file": str(path).replace("\\", "/"),
        "z": z, "x": x, "y": y,
        "bounds_lonlat": [minlon, minlat, maxlon, maxlat],
        "seams": [],
    }
    for seam_lon in SEAM_LONS:
        if not (minlon <= seam_lon <= maxlon):
            continue
        c = col_for_lon(seam_lon, minx_m, maxx_m)
        if not (1 <= c <= TILE_PX - 2):
            continue
        # Report the columns [c-1, c, c+1] and (for context) also c-2..c+2 means.
        cols = list(range(max(0, c - 2), min(TILE_PX, c + 3)))
        means = {int(k): float(h[:, k].mean()) for k in cols}
        left, right = means[c - 1], means[c + 1]
        centre = means[c]
        neigh = 0.5 * (left + right)
        # Deviation of the centre column relative to its two neighbours.
        rel = (centre - neigh) / neigh if neigh else 0.0
        result["seams"].append({
            "seam_lon_e": seam_lon,
            "col": c,
            "col_lon_e": math.degrees((minx_m + (c + 0.5) / TILE_PX * (maxx_m - minx_m)) / EARTH_R),
            "col_means_m": means,
            "left_neighbour_col": c - 1,
            "right_neighbour_col": c + 1,
            "centre_mean_m": centre,
            "neighbour_mean_m": neigh,
            "rel_deviation": rel,
            "flag_low": rel <= -FLAG_FRAC,
        })
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tiles", nargs="*", help="WebP tiles to check; default: the z9 ring seam tiles")
    ap.add_argument("--json", help="write the full per-tile report to this JSON file")
    args = ap.parse_args()
    paths = [Path(p) for p in (args.tiles or DEFAULT_TILES)]

    rows = []
    any_flagged = False
    for p in paths:
        r = check_tile(p)
        rows.append(r)
        for seam in r["seams"]:
            tag = " LOW" if seam["flag_low"] else "    "
            means = seam["col_means_m"]
            c = seam["col"]
            print(
                f"{r['z']}/{r['x']}/{r['y']}  seam {seam['seam_lon_e']:.4f} E"
                f"  col {c:>3} ({seam['col_lon_e']:.4f} E)"
                f"  left(c{c-1})={means[c-1]:.1f}"
                f"  centre(c{c})={seam['centre_mean_m']:.1f}"
                f"  right(c{c+1})={means[c+1]:.1f}"
                f"  rel={seam['rel_deviation']*100:+.1f}%{tag}"
            )
            if seam["flag_low"]:
                any_flagged = True
                cols = sorted(means.keys())
                ctx = ", ".join(f"c{k}={means[k]:.1f}" for k in cols)
                print(f"     context columns: {ctx}")

    if args.json:
        out = Path(args.json)
        out.write_text(json.dumps({"tiles": rows}, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out}")

    return 1 if any_flagged else 0


if __name__ == "__main__":
    sys.exit(main())
