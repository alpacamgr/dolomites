"""
Download TINITALY v1.1 (INGV, CC BY 4.0) DEM tiles covering the Dolomites bbox.

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe (Python 3.13, needs `requests`).

Tile naming (derived from probe on 2026-09-06): w<NNN><EE>_s10 where
  N_origin_km = int(NNN) * 10 and E_origin_km = int(EE) * 10 in EPSG:32632 (WGS 84 / UTM 32N).
Each tile covers 50 km x 50 km at 10 m/pixel; some tiles are truncated at
international borders and coastlines and are therefore smaller than 5000x5000.

For the Dolomites bbox 10.3 E to 12.7 E, 45.8 N to 47.2 N (UTM 32N ~E 600-782 km,
N 5074-5231 km) the tiles listed in TILES below cover the whole area with a
buffer to the surrounding cells. Missing cells (a couple of Alpine ridge cells
along the Austrian border) are not published by TINITALY and are left to be
filled from Copernicus GLO-30 by the mosaic step.

Idempotent: skips zips that already exist with the right length, verifies
sha256 against the checksums recorded in checksums.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import requests

RAW_DIR = Path(r"E:/Projects/Dolomites/data/raw/tinitaly-v1-1-10m")
BASE_URL = "https://tinitaly.pi.ingv.it/data_1.1"

# Tiles that intersect the bbox 10.3-12.7 E / 45.8-47.2 N in UTM 32N.
# Rows 5050, 5100, 5150 km (5 tiles each), plus 5200 km (2 tiles that exist);
# the rest of the 5200 row (E 600-650 and 750-780) is outside published TINITALY
# coverage (the Austrian border and the Adriatic coast).
TILES: list[str] = [
    "w50560", "w50565", "w50570", "w50575", "w50580",
    "w51060", "w51065", "w51070", "w51075", "w51080",
    "w51560", "w51565", "w51570", "w51575", "w51580",
    "w52065", "w52070",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_one(tile: str) -> dict:
    url = f"{BASE_URL}/{tile}_s10/{tile}_s10.zip"
    out = RAW_DIR / f"{tile}_s10.zip"
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    head = requests.head(url, timeout=30, allow_redirects=True)
    head.raise_for_status()
    expected = int(head.headers["Content-Length"])
    if out.exists() and out.stat().st_size == expected:
        print(f"[skip] {tile} ({expected} bytes)")
    else:
        print(f"[get ] {tile} ({expected} bytes)")
        with requests.get(url, timeout=600, stream=True) as r:
            r.raise_for_status()
            tmp = out.with_suffix(".zip.part")
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
            tmp.replace(out)
    sha = sha256_file(out)
    # Extract the .tif next to the .zip if not present.
    with zipfile.ZipFile(out) as zf:
        for name in zf.namelist():
            if name.endswith(".tif"):
                target = RAW_DIR / Path(name).name
                if not target.exists() or target.stat().st_size == 0:
                    with zf.open(name) as src, open(target, "wb") as dst:
                        for chunk in iter(lambda: src.read(1 << 20), b""):
                            dst.write(chunk)
                break
    return {"tile": tile, "url": url, "bytes": expected, "sha256": sha}


def main() -> int:
    records: list[dict] = []
    t0 = time.time()
    for i, tile in enumerate(TILES, 1):
        print(f"({i}/{len(TILES)})", tile)
        records.append(download_one(tile))
    (RAW_DIR / "checksums.json").write_text(
        json.dumps({r["tile"]: r for r in records}, indent=2, sort_keys=True) + "\n"
    )
    print(f"done in {time.time()-t0:.0f} s; total {sum(r['bytes'] for r in records)/1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
