"""
Extract the age statement of every Trentino geological unit from the PAT unit legend and
write it into data/scripts/terrain/geology_age_mapping.json (sources."pat-geology-carta-geologica".unit_ages).

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe (needs pyshp); needs pdftotext
(Git for Windows ships it in /mingw64/bin).

Why: the PAT shapefiles (fetch_geology_tn.py) carry only the map symbol (sigla_cart) and the
unit name (nome), no age. The Servizio Geologico publishes the ages in
"Legenda della Carta Geologica - Descrizione delle Unita", Versione Ottobre 2019
(data/raw/pat-geology-carta-geologica/docs/Descrizione_delle_Unita_-_Carta_geologica_del_Trentino.pdf,
linked from https://www.provincia.tn.it/News/Approfondimenti/Carta-Geologica-della-Provincia-Autonoma-di-Trento).
Each unit there is a block "SIGLA NAME description ... Eta: <age>.".

Rules (no age is invented; every string below is the PDF's own text):
  own     the unit's block has an "Eta:" statement (the colon is missing in a few blocks, e.g. LRE "Eta Permiano").
  parent  the block has none (or the unit has no block), and the unit's name starts with
          "<parent name> -" where <parent> is a unit whose sigla is a prefix of this sigla
          and which has its own statement (members inherit the formation's age, an outer
          envelope). Example: SCIb "FORMAZIONE DELLO SCILIAR - Brecce ..." <- SCI.
  by_name a sigla used for several blocks (dykes such as fy, fa in different magmatic
          groups) is resolved only if exactly one of those blocks starts with the unit's name.
  none    anything else: the age stays null and the unit is listed.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import shapefile

RAW = Path(r"E:/Projects/Dolomites/data/raw/pat-geology-carta-geologica")
PDF = RAW / "docs" / "Descrizione_delle_Unita_-_Carta_geologica_del_Trentino.pdf"
LEGEND_PDF = RAW / "docs" / "Legenda_Carta_Geologica_del_Trentino.pdf"
MAPPING = Path(r"E:/Projects/Dolomites/data/scripts/terrain/geology_age_mapping.json")
SOURCE_ID = "pat-geology-carta-geologica"
LAYERS = ("substrato", "sintemi")
SKIP = re.compile(r"^(Servizio Geologico - Via Zambra|PROVINCIA AUTONOMA DI TRENTO|SIGLA_CART NOME DESCRIZIONE|"
                  r"Legenda della Carta Geologica|Versione Ottobre)")


def pdf_text(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-raw", "-enc", "UTF-8", str(pdf), "-"], check=True,
                          capture_output=True).stdout.decode("utf-8")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().upper()


def main() -> int:
    units: collections.Counter = collections.Counter()
    for layer in LAYERS:
        r = shapefile.Reader(glob.glob(str(RAW / layer / "*.shp"))[0], encoding="latin-1")
        fields = [f[0] for f in r.fields[1:]]
        i_s, i_n = fields.index("sigla_cart"), fields.index("nome")
        for rec in r.iterRecords():
            units[(rec[i_s], rec[i_n])] += 1

    legend_siglas = set(re.findall(r"^([A-Za-z][A-Za-z0-9\-]{0,8}) - ", pdf_text(LEGEND_PDF), re.M))
    anchors = {s for s, _ in units if s} | legend_siglas
    blocks: dict[str, list[dict]] = collections.defaultdict(list)
    cur = None
    for ln in pdf_text(PDF).splitlines():
        if SKIP.match(ln):
            continue
        m = re.match(r"^(\S+)(?: (.*))?$", ln)
        if m and m.group(1) in anchors and (not m.group(2) or m.group(2)[:1].isupper()):
            cur = [m.group(2) or ""]
            blocks[m.group(1)].append(cur)
            continue
        if cur is not None:
            cur.append(ln)
    parsed: dict[str, list[dict]] = {}
    for s, bl in blocks.items():
        out = []
        for body in bl:
            txt = re.sub(r"\s+", " ", " ".join(body)).strip()
            m = re.search(r"(?<![A-Za-z])Et[àa](?:\s*:\s*|\s+)(.+?)\s*$", txt)
            out.append({"text": txt, "age": m.group(1).rstrip(".").strip() if m else None})
        parsed[s] = out

    def own(sigla: str, name: str) -> tuple[str | None, str]:
        bl = parsed.get(sigla, [])
        if len(bl) == 1:
            return bl[0]["age"], "own"
        hits = [b for b in bl if norm(b["text"]).startswith(norm(name))]
        if len(hits) == 1:
            return hits[0]["age"], "by_name"
        return None, "ambiguous" if bl else "no_block"

    by_sigla_name = {s: n for s, n in units}
    rows, counts = {}, collections.Counter()
    for (sigla, name), n_poly in sorted(units.items()):
        if not sigla:
            continue
        age, how = own(sigla, name)
        if age is None:
            parents = [p for p in parsed if p != sigla and sigla.startswith(p) and p in by_sigla_name
                       and norm(name).startswith(norm(by_sigla_name[p]) + " -")]
            parents.sort(key=len, reverse=True)
            for p in parents:
                page, _ = own(p, by_sigla_name[p])
                if page:
                    age, how = page, f"parent {p}"
                    break
        if age is None:
            how = {"own": "block without age statement", "by_name": "block without age statement"}.get(how, how)
        key = f"{sigla}|{name}"
        rows[key] = {"sigla": sigla, "name": name, "age": age, "resolved": how if age else f"none ({how})",
                     "polygons": n_poly}
        counts["own" if how in ("own", "by_name") else ("parent" if how.startswith("parent") else "none")] += 1

    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    src = mapping.setdefault("sources", {}).setdefault(SOURCE_ID, {})
    src["unit_ages"] = {
        "extracted_by": "data/scripts/terrain/extract_pat_unit_ages.py",
        "document": "Provincia autonoma di Trento, Servizio Geologico: Legenda della Carta Geologica - Descrizione delle Unita, Versione Ottobre 2019",
        "document_url": "https://www.provincia.tn.it/content/download/4931/50119/file/Descrizione+delle+Unit%C3%A0+-+Carta+geologica+del+Trentino.pdf",
        "join": "shapefile sigla_cart + nome -> the document's unit block (see the script docstring for own / parent / by_name)",
        "counts": dict(counts),
        "units": rows,
    }
    tmp = MAPPING.with_name(MAPPING.name + ".tmp")
    tmp.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, MAPPING)

    ages = collections.Counter()
    for r in rows.values():
        if r["age"]:
            ages[r["age"]] += r["polygons"]
    print(json.dumps(dict(counts)))
    print(f"{len(ages)} distinct age strings (polygons):")
    for a, c in sorted(ages.items(), key=lambda x: x[0].lower()):
        print(f"  {c:6d}  {a}")
    print("units without age:")
    for r in rows.values():
        if not r["age"]:
            print(f"  {r['polygons']:6d}  {r['sigla']:8s} {r['name'][:70]}  [{r['resolved']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
