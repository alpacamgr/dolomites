"""
Point-sampling check of the served geology tiles (docs/04-data-contracts.md 2.2).

Draws N uniform random points (fixed seed) in the tiles.json bounds and, for every zoom, decodes the MVT tile
containing each point and tests point-in-polygon on its "units" features. Reports per zoom:
  covered            points inside some unit polygon
  dated              covered points whose unit has a colour (i.e. an age mapped to the ICS chart)
  missing_vs_max     points covered at maxzoom but not at this zoom (holes that open at low zoom)
  extra_vs_max       points covered at this zoom but not at maxzoom
  overlap            points inside more than one polygon (should be 0: no double polygons)
  tiles / bytes / max tile bytes   over every .pbf file of the zoom (not just the sampled ones)
plus, at maxzoom, covered / undated per source and the age_basis counts.

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe (mapbox_vector_tile, shapely, numpy).
Usage: check_geology_tiles.py [--tiles DIR] [--n 3000] [--seed 20260912] [--json OUT] [--workers N]
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import mapbox_vector_tile
import numpy as np
import shapely
from shapely.geometry import shape
from shapely.strtree import STRtree

ROOT = Path(r"E:/Projects/Dolomites")
DEFAULT_TILES = ROOT / "app/public/data/terrain/geology"
EARTH_R = 6378137.0
ORIGIN_M = math.pi * EARTH_R
PROPS = ("source", "color", "age_basis", "age_withheld_reason", "unit_name")


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    rad = math.radians(lat)
    return int((lon + 180.0) / 360.0 * n), int((1.0 - math.log(math.tan(rad) + 1.0 / math.cos(rad)) / math.pi) / 2.0 * n)


def merc(lon: float, lat: float) -> tuple[float, float]:
    return math.radians(lon) * EARTH_R, math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * EARTH_R


def probe_tile(task: tuple[str, int, int, int, list[tuple[int, float, float]]]) -> list[tuple[int, int, dict | None]]:
    """-> [(point index, number of polygons hit, properties of the first hit or None)]"""
    tiles, z, x, y, pts = task
    path = Path(tiles) / str(z) / str(x) / f"{y}.pbf"
    if not path.exists():
        return [(i, 0, None) for i, _, _ in pts]
    data = path.read_bytes()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    layer = mapbox_vector_tile.decode(data).get("units", {})
    extent = layer.get("extent", 4096)
    geoms, props = [], []
    for f in layer.get("features", []):
        if f["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
            continue
        g = shape(f["geometry"])
        if not g.is_valid:
            g = shapely.make_valid(g)
        geoms.append(g)
        props.append({k: f["properties"].get(k) for k in PROPS})
    tree = STRtree(geoms) if geoms else None
    span = 2 * ORIGIN_M / 2 ** z
    minx, miny = -ORIGIN_M + x * span, ORIGIN_M - (y + 1) * span
    out = []
    for i, lon, lat in pts:
        if tree is None:
            out.append((i, 0, None))
            continue
        mx, my = merc(lon, lat)
        pt = shapely.Point((mx - minx) / span * extent, (my - miny) / span * extent)
        hits = tree.query(pt, predicate="intersects")
        out.append((i, len(hits), props[hits[0]] if len(hits) else None))
    return out


def zoom_files(tiles: Path, z: int) -> tuple[int, int, int, str | None]:
    n = total = biggest = 0
    where = None
    zdir = tiles / str(z)
    if not zdir.exists():
        return 0, 0, 0, None
    for xd in os.scandir(zdir):
        for f in os.scandir(xd.path):
            s = f.stat().st_size
            n += 1
            total += s
            if s > biggest:
                biggest, where = s, f"{z}/{xd.name}/{f.name}"
    return n, total, biggest, where


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", default=str(DEFAULT_TILES))
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=20260912)
    ap.add_argument("--json", help="write the result as JSON to this path")
    ap.add_argument("--gaps", default=str(ROOT / "app/public/data/terrain/geology-gaps.geojson"),
                    help="geology-gaps.geojson whose area is reported (skipped if missing)")
    ap.add_argument("--workers", type=int, default=max(1, min(16, (os.cpu_count() or 2) - 2)))
    args = ap.parse_args()
    tiles = Path(args.tiles)
    tj = json.loads((tiles / "tiles.json").read_text(encoding="utf-8"))
    lon0, lat0, lon1, lat1 = tj["bounds"]
    zooms = list(range(tj["minzoom"], tj["maxzoom"] + 1))
    zmax = zooms[-1]
    rng = np.random.default_rng(args.seed)
    lons = rng.uniform(lon0, lon1, args.n)
    lats = rng.uniform(lat0, lat1, args.n)

    tasks = []
    for z in zooms:
        groups = collections.defaultdict(list)
        for i, (lon, lat) in enumerate(zip(lons, lats)):
            groups[lonlat_to_tile(lon, lat, z)].append((i, float(lon), float(lat)))
        tasks.extend((str(tiles), z, x, y, pts) for (x, y), pts in groups.items())
    hit: dict[int, list] = {z: [None] * args.n for z in zooms}
    nhits: dict[int, list] = {z: [0] * args.n for z in zooms}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for task, res in zip(tasks, ex.map(probe_tile, tasks, chunksize=8)):
            z = task[1]
            for i, n, p in res:
                hit[z][i], nhits[z][i] = p, n

    rows = []
    top = hit[zmax]
    top_cov = sum(p is not None for p in top)
    top_dated = sum(p is not None and p["color"] is not None for p in top)
    for z in zooms:
        cov = sum(p is not None for p in hit[z])
        dated = sum(p is not None and p["color"] is not None for p in hit[z])
        missing = sum(top[i] is not None and hit[z][i] is None for i in range(args.n))
        extra = sum(top[i] is None and hit[z][i] is not None for i in range(args.n))
        n_files, total, biggest, where = zoom_files(tiles, z)
        rows.append({
            "zoom": z, "covered": cov, "dated": dated,
            "dated_share_of_covered": round(dated / cov, 4) if cov else None,
            "dated_share_delta_vs_max_pp": round(100 * (dated / cov - top_dated / top_cov), 2) if cov and top_cov else None,
            "missing_vs_max": missing, "missing_vs_max_pct": round(100 * missing / top_cov, 2) if top_cov else None,
            "extra_vs_max": extra, "overlap_points": sum(n > 1 for n in nhits[z]),
            "tiles": n_files, "bytes": total, "max_tile_bytes": biggest, "max_tile": where,
        })

    per_source = collections.defaultdict(collections.Counter)
    for p in top:
        if p is None:
            continue
        s = per_source[p["source"]]
        s["covered"] += 1
        s["undated"] += p["color"] is None
        s[f"age_basis:{p.get('age_basis')}"] += 1
        if p.get("age_withheld_reason"):
            s[f"withheld:{p['age_withheld_reason']}"] += 1
    undated_names = collections.defaultdict(collections.Counter)
    for p in top:
        if p is not None and p["color"] is None:
            undated_names[p["source"]][p["unit_name"]] += 1
    gaps = None
    gaps_path = Path(args.gaps)
    if gaps_path.exists():
        from pyproj import Geod
        geod = Geod(ellps="WGS84")
        fc = json.loads(gaps_path.read_text(encoding="utf-8"))
        area = sum(abs(geod.geometry_area_perimeter(shape(f["geometry"]))[0]) for f in fc["features"])
        bbox_area = abs(geod.geometry_area_perimeter(shapely.box(lon0, lat0, lon1, lat1))[0])
        gaps = {"file": gaps_path.name, "area_km2": round(area / 1e6, 1), "share_of_bounds": round(area / bbox_area, 4)}
    result = {
        "uncovered_points_at_max_zoom": args.n - top_cov,
        "uncovered_share_at_max_zoom": round((args.n - top_cov) / args.n, 4),
        "gaps_file": gaps,
        "method": (f"{args.n} uniform random points (numpy default_rng seed {args.seed}) in the tiles.json bounds {tj['bounds']}; "
                   "for each zoom the tile containing the point is decoded and the point tested against its 'units' polygons "
                   "(tile coordinates, Web Mercator). dated = the hit unit has a non-null color. missing_vs_max = covered at "
                   f"z{zmax} but not at this zoom. Bytes are the served .pbf file sizes (raw MVT) of every tile of the zoom."),
        "tiles_dir": str(tiles).replace("\\", "/"),
        "per_zoom": rows,
        "at_max_zoom_per_source": {s: {**dict(c), "undated_share": round(c["undated"] / c["covered"], 4)} for s, c in sorted(per_source.items())},
        "undated_units_at_max_zoom": {s: dict(c.most_common(12)) for s, c in sorted(undated_names.items())},
        "total_tiles": sum(r["tiles"] for r in rows), "total_bytes": sum(r["bytes"] for r in rows),
    }

    print(result["method"])
    print(f"{'z':>3} {'covered':>8} {'dated':>6} {'dated%':>7} {'d_pp':>6} {'missing':>8} {'miss%':>6} {'extra':>6} {'ovl':>4} {'tiles':>6} {'MB':>7} {'max kB':>7}  max tile")
    for r in rows:
        print(f"{r['zoom']:>3} {r['covered']:>8} {r['dated']:>6} {100*(r['dated_share_of_covered'] or 0):>6.1f}% {r['dated_share_delta_vs_max_pp'] or 0:>6.2f} "
              f"{r['missing_vs_max']:>8} {r['missing_vs_max_pct'] or 0:>5.2f}% {r['extra_vs_max']:>6} {r['overlap_points']:>4} {r['tiles']:>6} "
              f"{r['bytes']/1e6:>7.2f} {r['max_tile_bytes']/1e3:>7.0f}  {r['max_tile']}")
    print(f"total: {result['total_tiles']} tiles, {result['total_bytes']/1e6:.1f} MB")
    print(f"uncovered sample points at z{zmax}: {result['uncovered_points_at_max_zoom']} ({100*result['uncovered_share_at_max_zoom']:.1f}%); "
          f"gaps file: {result['gaps_file']}")
    print(f"at z{zmax} per source:")
    for s, c in result["at_max_zoom_per_source"].items():
        print(f"  {s}: {c}")
        print(f"     undated units: {result['undated_units_at_max_zoom'].get(s, {})}")
    if args.json:
        out = Path(args.json)
        tmp = out.with_name(out.name + ".tmp")
        tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, out)
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
