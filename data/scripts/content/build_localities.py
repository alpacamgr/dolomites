"""Build app/public/data/terrain/localities.geojson from content/localities.yaml.

Contract: docs/04-data-contracts.md section 2.4. Every locality must carry a
`source_url` and a `verified` date; entries without them are skipped and
reported, never guessed.

Run with the project venv:
    E:/Projects/Dolomites/.venv/Scripts/python.exe data/scripts/content/build_localities.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "content" / "localities.yaml"
OUT_DIR = REPO / "app" / "public" / "data" / "terrain"
OUT = OUT_DIR / "localities.geojson"
META = OUT_DIR / "localities.meta.json"
# Terrain LGM window from the contract, generous enough for all chapters.
BOUNDS = (9.5, 45.5, 13.5, 47.5)  # minLon, minLat, maxLon, maxLat


def main() -> int:
    data = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    features, skipped = [], []
    for loc in data.get("localities", []):
        missing = [k for k in ("id", "name", "lat", "lon", "kind", "source_url", "verified") if not loc.get(k)]
        if missing:
            skipped.append((loc.get("id", "?"), f"missing {missing}"))
            continue
        lon, lat = float(loc["lon"]), float(loc["lat"])
        if not (BOUNDS[0] <= lon <= BOUNDS[2] and BOUNDS[1] <= lat <= BOUNDS[3]):
            skipped.append((loc["id"], f"outside bounds ({lon}, {lat})"))
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
            "properties": {
                "id": loc["id"],
                "kind": loc["kind"],
                "name": loc["name"],
                "source_ref": loc.get("source_ref"),
            },
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".geojson.part")
    tmp.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, OUT)

    meta = {
        "dataset_id": "project-localities",
        "label": "observed",
        "source_ref": "localities",
        "attribution": "Locality coordinates: Wikidata, ICS GSSP pages and official sources, see content/localities.yaml",
        "license": "Coordinates are facts; per-entry sources in content/localities.yaml",
        "generated": date.today().isoformat(),
        "script": "data/scripts/content/build_localities.py",
        "count": len(features),
    }
    tmp = META.with_suffix(".json.part")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, META)

    print(f"wrote {len(features)} localities to {OUT.relative_to(REPO)}")
    for sid, why in skipped:
        print(f"skipped {sid}: {why}")
    return 0 if features else 1


if __name__ == "__main__":
    sys.exit(main())
