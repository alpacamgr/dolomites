"""Export a PMTiles archive to static {z}/{x}/{y} tile files plus a TileJSON descriptor.

Served layout per docs/04-data-contracts.md 2.1 / 2.2 and ADR 0006:
  raster-dem (Terrain-RGB PNG)  -> {out}/{z}/{x}/{y}.webp  lossless, verified bit-identical per tile
  vector (MVT)                  -> {out}/{z}/{x}/{y}.pbf   raw (decompressed) MVT
  {out}/tiles.json              TileJSON 3.0 with a template relative to the data base

Output is written to {out}.part and renamed over {out} only when complete.

Run with the project venv, e.g.:
  .venv/Scripts/python.exe data/scripts/terrain/export_tiles.py --in app/public/data/terrain/dolomites-terrain.pmtiles \
      --out app/public/data/terrain/elevation --kind raster-dem --template terrain/elevation/{z}/{x}/{y}.webp
  .venv/Scripts/python.exe data/scripts/terrain/export_tiles.py --in app/public/data/terrain/geology-dolomites.pmtiles \
      --out app/public/data/terrain/geology --kind vector --template terrain/geology/{z}/{x}/{y}.pbf
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image
from pmtiles.reader import MmapSource, Reader, all_tiles
from pmtiles.tile import Compression


def to_webp_lossless(item: tuple[int, int, int, bytes]) -> tuple[int, int, int, bytes, int]:
    """Re-encode one Terrain-RGB PNG tile as lossless WebP and verify the pixels round-trip exactly."""
    z, x, y, data = item
    rgb = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="WEBP", lossless=True, method=6)
    out = buf.getvalue()
    back = np.asarray(Image.open(io.BytesIO(out)).convert("RGB"))
    if not np.array_equal(rgb, back):
        raise ValueError(f"lossless WebP round trip changed pixels in tile {z}/{x}/{y}")
    return z, x, y, out, len(data)


def replace_with_retry(src: Path, dst: Path, attempts: int = 20) -> None:
    """os.replace, retried: on Windows a dev-server file watcher can briefly hold a new directory."""
    for i in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(1.5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--kind", choices=["raster-dem", "vector"], required=True)
    ap.add_argument("--template", required=True, help="tile path relative to the data base, with {z}/{x}/{y}")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    part = out.with_name(out.name + ".part")
    if part.exists():
        shutil.rmtree(part)

    with open(src, "rb") as f:
        reader = Reader(MmapSource(f))
        header = reader.header()
        meta = reader.metadata()
        compression = header.get("tile_compression")
        tiles = [(z, x, y, data) for (z, x, y), data in all_tiles(reader.get_bytes)]

    ext = "webp" if args.kind == "raster-dem" else "pbf"
    written = in_bytes = out_bytes = 0

    def write(z: int, x: int, y: int, payload: bytes) -> None:
        d = part / str(z) / str(x)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{y}.{ext}").write_bytes(payload)

    if args.kind == "raster-dem":
        with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 2)) as pool:
            for z, x, y, payload, n_in in pool.map(to_webp_lossless, tiles, chunksize=8):
                write(z, x, y, payload)
                written += 1
                in_bytes += n_in
                out_bytes += len(payload)
    else:
        for z, x, y, data in tiles:
            payload = gzip.decompress(data) if compression == Compression.GZIP else data
            write(z, x, y, payload)
            written += 1
            in_bytes += len(data)
            out_bytes += len(payload)

    bounds = [header["min_lon_e7"] / 1e7, header["min_lat_e7"] / 1e7, header["max_lon_e7"] / 1e7, header["max_lat_e7"] / 1e7]
    tilejson = {
        "tilejson": "3.0.0",
        "name": meta.get("name", src.stem),
        "tiles": [args.template],
        "minzoom": header["min_zoom"],
        "maxzoom": header["max_zoom"],
        "bounds": bounds,
        "center": [header["center_lon_e7"] / 1e7, header["center_lat_e7"] / 1e7, header["center_zoom"]],
        "attribution": meta.get("attribution", ""),
        "source_archive": str(src).replace("\\", "/"),
        "script": "data/scripts/terrain/export_tiles.py",
    }
    if args.kind == "raster-dem":
        tilejson.update({"encoding": meta.get("encoding", "mapbox"), "tileSize": 512, "format": "webp"})
    else:
        layers = meta.get("vector_layers") or [{"id": "units"}]
        tilejson.update({"vector_layers": layers, "format": "pbf"})
    (part / "tiles.json").write_text(json.dumps(tilejson, ensure_ascii=False, indent=2), encoding="utf-8")

    if out.exists():
        old = out.with_name(out.name + ".old")
        if old.exists():
            shutil.rmtree(old)
        replace_with_retry(out, old)
        replace_with_retry(part, out)
        shutil.rmtree(old)
    else:
        replace_with_retry(part, out)

    print(f"{src.name}: {written} tiles -> {out} ({in_bytes/1e6:.1f} MB in archive, {out_bytes/1e6:.1f} MB written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
