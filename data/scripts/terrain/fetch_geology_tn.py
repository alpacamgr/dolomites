"""
Download the Provincia autonoma di Trento geological map (Carta Geologica della PAT) shapefiles.

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe (needs requests only).

Source: PAT Geocatalogo (GeoNetwork, https://siatservices.provincia.tn.it/geonetwork),
one metadata record per layer of the Geological Database, each linking a zipped
ESRI shapefile under https://siatservices.provincia.tn.it/idt/vector/.
Licence stated in each record (gmd:useLimitation / resourceConstraints, fetched 2026-09-12):
"Creative Commons Attribuzione 4.0 Internazionale (CC BY 4.0) -
https://creativecommons.org/licenses/by/4.0/deed.it".

Layers fetched (polygon layers that together make the geological map surface):
  Substrato            p_TN:5d2495a7-6747-42e4-b898-9d10231f4042  bedrock formations
  Depositi Quaternari  p_TN:3f2b086a-33f7-43bc-afe7-ef101383e42e  Quaternary cover
  Depositi di Frana    p_TN:2989436c-8c94-4a3c-a116-4e62a07e963c  landslide deposits
  Sintemi              p_TN:01a91b16-04e9-4ff7-8be3-f7af49dc8c37  Quaternary synthems

Also fetched (legend documents published with the map on
https://www.provincia.tn.it/News/Approfondimenti/Carta-Geologica-della-Provincia-Autonoma-di-Trento,
where the page states the CC BY licence and the attribution "Dati elaborati dal Servizio geologico
della Provincia autonoma di Trento"): the unit descriptions with the age of each unit, the legend,
and the December 2019 update note, into docs/.

Each zip is streamed to <name>.zip.part and renamed into place; SHA-256 and byte
counts go to checksums.json. Each zip is extracted into a folder of the same name (substrato/, sintemi/, ...),
which the build reads. Idempotent: an existing zip of the advertised size and an existing folder are skipped.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import requests
import zipfile

RAW_DIR = Path(r"E:/Projects/Dolomites/data/raw/pat-geology-carta-geologica")
BASE = "https://siatservices.provincia.tn.it/idt/vector/p_TN_{uuid}.zip"
RECORD = "https://siatservices.provincia.tn.it/geonetwork/srv/api/records/p_TN:{uuid}/formatters/xml"
LAYERS = {
    "substrato": "5d2495a7-6747-42e4-b898-9d10231f4042",
    "depositi_quaternari": "3f2b086a-33f7-43bc-afe7-ef101383e42e",
    "depositi_frana": "2989436c-8c94-4a3c-a116-4e62a07e963c",
    "sintemi": "01a91b16-04e9-4ff7-8be3-f7af49dc8c37",
}

DOCS = {
    "Descrizione_delle_Unita_-_Carta_geologica_del_Trentino.pdf":
        "https://www.provincia.tn.it/content/download/4931/50119/file/Descrizione+delle+Unit%C3%A0+-+Carta+geologica+del+Trentino.pdf",
    "Legenda_Carta_Geologica_del_Trentino.pdf":
        "https://www.provincia.tn.it/content/download/5604/54416/file/Legenda+Carta+Geologica+del+Trentino.pdf",
    "Carta_geologica_del_Trentino_-_aggiornamento_dicembre_2019.pdf":
        "https://www.provincia.tn.it/content/download/4916/50028/file/Carta+geologica+del+Trentino+-+aggiornamento+dicembre+2019.pdf",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sums_path = RAW_DIR / "checksums.json"
    sums = json.loads(sums_path.read_text()) if sums_path.exists() else {}
    only = set(sys.argv[1:]) or set(LAYERS)
    for name, uuid in LAYERS.items():
        if name not in only:
            continue
        url = BASE.format(uuid=uuid)
        out = RAW_DIR / f"{name}.zip"
        head = requests.head(url, timeout=60)
        head.raise_for_status()
        size = int(head.headers.get("Content-Length", 0))
        if out.exists() and out.stat().st_size == size:
            print(f"[skip] {out.name} ({size/1e6:.1f} MB)")
        else:
            t0 = time.time()
            tmp = out.with_suffix(".zip.part")
            with requests.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
            if tmp.stat().st_size != size:
                sys.exit(f"{name}: got {tmp.stat().st_size} bytes, server advertised {size}")
            os.replace(tmp, out)
            print(f"wrote {out.name} ({size/1e6:.1f} MB) in {time.time()-t0:.0f} s")
        folder = RAW_DIR / name
        if not folder.exists():
            tmpdir = RAW_DIR / (name + ".part")
            if tmpdir.exists():
                shutil.rmtree(tmpdir)
            with zipfile.ZipFile(out) as zf:
                zf.extractall(tmpdir)
            os.replace(tmpdir, folder)
            print(f"extracted {out.name} -> {folder.name}/")
        # keep the metadata record next to the data (licence evidence)
        rec = requests.get(RECORD.format(uuid=uuid), headers={"Accept": "application/xml"}, timeout=60)
        rec.raise_for_status()
        rec_path = RAW_DIR / f"{name}.metadata.xml"
        tmp = rec_path.with_suffix(".xml.part")
        tmp.write_bytes(rec.content)
        os.replace(tmp, rec_path)
        sums[out.name] = {
            "bytes": out.stat().st_size, "sha256": sha256(out), "url": url,
            "metadata_record": RECORD.format(uuid=uuid), "last_modified": head.headers.get("Last-Modified"),
            "fetched": time.strftime("%Y-%m-%d"),
        }
    (RAW_DIR / "docs").mkdir(exist_ok=True)
    for name, url in DOCS.items():
        out = RAW_DIR / "docs" / name
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        tmp = out.with_name(out.name + ".part")
        tmp.write_bytes(r.content)
        os.replace(tmp, out)
        sums["docs/" + name] = {"bytes": out.stat().st_size, "sha256": sha256(out), "url": url,
                                "fetched": time.strftime("%Y-%m-%d")}
        print(f"wrote docs/{name} ({out.stat().st_size/1e3:.0f} kB)")
    tmp = sums_path.with_suffix(".json.part")
    tmp.write_text(json.dumps(sums, indent=2) + "\n")
    os.replace(tmp, sums_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
