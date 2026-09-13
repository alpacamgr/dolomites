"""
Download Copernicus DEM GLO-90 tiles for the outer ring around the core DEM
bbox (docs/ux/2026-09-13-terrain-ring.md).

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe.

Coverage
--------
Six tiles N45..N47 x E009 and E013 (six 1 deg x 1 deg tiles at 3 arc-seconds /
~90 m). These are the two outer strips of the ring bbox 9-14 E / 45-48 N
outside the existing GLO-30 coverage (10-13 E / 45-48 N). The build uses GLO-30
inside its own bbox and GLO-90 in these strips.

Vertical datum
--------------
Copernicus DEM heights are referenced to EGM2008 (EPSG:3855), i.e. orthometric
(Copernicus DEM Product Handbook v5.0, 2022-11-29, sec. 1.2). Same as GLO-30
so no geoid correction is applied; see data/manifests/copernicus-dem-glo90.yaml.

Output
------
data/raw/copernicus-dem-glo90/Copernicus_DSM_COG_30_<lat>_00_<lon>_00_DEM.tif
data/raw/copernicus-dem-glo90/checksums.json  (sha256 + bytes + URL per tile)
data/raw/copernicus-dem-glo90/fetch.log

Idempotent: existing files with matching Content-Length are kept; sha256 is
recorded either way.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import requests

RAW_DIR = Path(r"E:/Projects/Dolomites/data/raw/copernicus-dem-glo90")
BASE_URL = "https://copernicus-dem-90m.s3.amazonaws.com"

# Six tiles: two longitude strips (E009 and E013) x three latitudes (N45..N47).
# The remaining 3x3 grid at E010..E012 is inside the existing GLO-30 coverage
# and is not fetched here (the build uses GLO-30 there).
TILES: list[tuple[str, str]] = [
    (lat, lon)
    for lat in ("N45", "N46", "N47")
    for lon in ("E009", "E013")
]


def tile_name(lat: str, lon: str) -> str:
    return f"Copernicus_DSM_COG_30_{lat}_00_{lon}_00_DEM"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_one(lat: str, lon: str, log: list[str]) -> dict:
    name = tile_name(lat, lon)
    url = f"{BASE_URL}/{name}/{name}.tif"
    out = RAW_DIR / f"{name}.tif"

    head = requests.head(url, timeout=30, allow_redirects=True)
    head.raise_for_status()
    expected = int(head.headers["Content-Length"])
    if out.exists() and out.stat().st_size == expected:
        line = f"[skip] {name} ({expected} bytes)"
    else:
        t0 = time.time()
        with requests.get(url, timeout=600, stream=True) as r:
            r.raise_for_status()
            tmp = out.with_suffix(".tif.part")
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
            tmp.replace(out)
        line = f"[get ] {name} ({expected} bytes, {time.time()-t0:.1f} s)"
    print(line, flush=True)
    log.append(line)
    return {
        "name": name,
        "url": url,
        "bytes": out.stat().st_size,
        "sha256": sha256_file(out),
    }


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log: list[str] = []
    log.append(f"# fetched {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} from {BASE_URL}")
    records: list[dict] = []
    for lat, lon in TILES:
        try:
            records.append(download_one(lat, lon, log))
        except Exception as e:
            line = f"[err ] {tile_name(lat, lon)}: {e!r}"
            print(line, flush=True)
            log.append(line)
    total = sum(r["bytes"] for r in records)
    line = f"# total {len(records)} tiles, {total} bytes ({total/1e6:.1f} MB)"
    log.append(line)
    print(line, flush=True)

    (RAW_DIR / "checksums.json").write_text(
        json.dumps({r["name"]: {"sha256": r["sha256"], "bytes": r["bytes"], "url": r["url"]}
                    for r in records}, indent=2) + "\n"
    )
    (RAW_DIR / "fetch.log").write_text("\n".join(log) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
