"""
Download the Regione del Veneto regional lithology database (1:250,000) from the IDT2 GeoServer WFS.

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe (needs requests only).

Source record: r_veneto:c0501031_LitologiaReg, "Database delle diverse litologie che compongono
il territorio della Regione Veneto scala 1:250.000" (Regione Veneto, Sezione Geologia e georisorse),
https://idt2.regione.veneto.it/geoportal/rest/document?id=r_veneto:c0501031_LitologiaReg
Licence stated in that record (fetched 2026-09-12): gmd:useLimitation "IODL 2.0",
gmd:otherConstraints "http://publications.europa.eu/resource/authority/licence/IODL_2_0".

WFS layer rv:c0501031_litologiareg_ (5 048 features for the whole region; native EPSG:3003),
requested as GeoJSON reprojected server-side to EPSG:4326. The layer is small, so the whole
region is fetched and clipping to the Dolomites bbox is left to the build.
Output is written to a .part file and renamed; SHA-256 goes to checksums.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests

RAW_DIR = Path(r"E:/Projects/Dolomites/data/raw/veneto-litologia-250k")
WFS = "https://idt2-geoserver.regione.veneto.it/geoserver/wfs"
LAYER = "rv:c0501031_litologiareg_"
RECORD = "https://idt2.regione.veneto.it/geoportal/rest/document?id=r_veneto:c0501031_LitologiaReg"


def write_atomic(path: Path, payload: bytes) -> None:
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(payload)
    os.replace(tmp, path)


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "c0501031_litologiareg.geojson"
    params = {"service": "WFS", "version": "1.0.0", "request": "GetFeature", "typeName": LAYER,
              "outputFormat": "application/json", "srsName": "EPSG:4326"}
    if out.exists() and out.stat().st_size > 0:
        print(f"[skip] {out.name} exists")
        payload = out.read_bytes()
    else:
        r = requests.get(WFS, params=params, timeout=300)
        r.raise_for_status()
        payload = r.content
        n = len(json.loads(payload)["features"])
        write_atomic(out, payload)
        print(f"wrote {out.name} ({len(payload)/1e6:.1f} MB, {n} features)")
    rec = requests.get(RECORD, timeout=60)
    rec.raise_for_status()
    write_atomic(RAW_DIR / "c0501031_LitologiaReg.metadata.xml", rec.content)
    sums = {out.name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                       "features": len(json.loads(payload)["features"]), "wfs": WFS, "layer": LAYER,
                       "params": params, "metadata_record": RECORD, "fetched": time.strftime("%Y-%m-%d")}}
    write_atomic(RAW_DIR / "checksums.json", (json.dumps(sums, indent=2) + "\n").encode())
    print(json.dumps(sums, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
