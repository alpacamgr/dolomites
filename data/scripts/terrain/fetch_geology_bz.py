"""
Download the South Tyrol Geological Units - Detailed layer from the P_BZ Geological Map WFS.

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe (needs requests only).

Source dataset: "Servizi OGC P_BZ Carta geologica CARG" on data.civis.bz.it.
Dataset licence: CC0 1.0 Universal (portal default).
Layer: p_bz-GeologicalMap:GeologicalUnits-Detailed (66 133 features, CARG-derived).

WFS 2.0 paginates by numberMatched/count; we page through until the last chunk
returns fewer than `PAGE` features. Requested output is GeoJSON (EPSG:4326)
clipped to the Dolomites bbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import requests

RAW_DIR = Path(r"E:/Projects/Dolomites/data/raw/bz-geology-carg")
WFS = "https://geoservices1.civis.bz.it/geoserver/ows"
LAYER = "p_bz-GeologicalMap:GeologicalUnits-Detailed"
BBOX = (10.3, 45.8, 12.7, 47.2)  # minLon, minLat, maxLon, maxLat
# The layer's native CRS is EPSG:25832 (ETRS89 / UTM 32N). GeoServer's WFS
# only honours the BBOX filter in the native axis order, so we send the
# reprojected bounding box; server-side reprojection to EPSG:4326 for the
# JSON output still works.
BBOX_25832 = (601000.0, 5072600.0, 780300.0, 5234100.0)
PAGE = 5000


def fetch_page(start: int) -> dict:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": LAYER,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "bbox": f"{BBOX_25832[0]},{BBOX_25832[1]},{BBOX_25832[2]},{BBOX_25832[3]},EPSG:25832",
        "count": str(PAGE),
        "startIndex": str(start),
    }
    r = requests.get(WFS, params=params, timeout=180)
    r.raise_for_status()
    return r.json()


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{LAYER.split(':')[1]}.geojson"

    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"[skip] {out_path.name} exists ({out_path.stat().st_size/1e6:.1f} MB)")
        return 0

    all_features: list[dict] = []
    start = 0
    t0 = time.time()
    while True:
        page = fetch_page(start)
        feats = page.get("features", [])
        n = page.get("numberMatched", "?")
        print(f"  start={start} got={len(feats)} of {n}")
        if not feats:
            break
        all_features.extend(feats)
        if len(feats) < PAGE:
            break
        start += PAGE

    fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "source": {
            "layer": LAYER,
            "wfs": WFS,
            "bbox": list(BBOX),
            "fetched": time.strftime("%Y-%m-%d"),
        },
        "features": all_features,
    }
    payload = json.dumps(fc, ensure_ascii=False).encode("utf-8")
    out_path.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    print(f"wrote {out_path} ({len(payload)/1e6:.1f} MB, {len(all_features)} features) in {time.time()-t0:.0f} s")
    print("sha256", sha)
    (RAW_DIR / "checksums.json").write_text(
        json.dumps(
            {
                out_path.name: {
                    "bytes": len(payload),
                    "sha256": sha,
                    "features": len(all_features),
                    "layer": LAYER,
                    "wfs": WFS,
                    "bbox": list(BBOX),
                }
            },
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
