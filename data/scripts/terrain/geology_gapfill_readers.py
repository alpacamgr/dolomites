"""
Readers for the gap-fill geology sources of build_geology_pmtiles.py (priorities 4-6):
  swisstopo-geocover            GeoCover 1:25,000 GeoPackages (4 sheet zips), EPSG:2056
  ispra-geologia-100k-inspire   Carta Geologica d'Italia 1:100.000, INSPIRE GE GML 3.2 (lat, lon axis order), EPSG:4258
  geosphere-geologicunits-500k  INSPIRE Geologische Einheiten 1:500.000 Oesterreich, GeoPackage, EPSG:4258

Each reader returns raw records (geometry in lon/lat plus the source's own attributes) for polygons intersecting a
bbox; age mapping and properties are done by the loaders in build_geology_pmtiles.py. EPSG:4258 (ETRS89) coordinates
are used as EPSG:4326 without transformation (the two frames differ by well under 1 m in 2026, far below the 1:100,000
and 1:500,000 map accuracy).

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe (numpy, shapely, pyogrio, pyproj).
Run directly for an inventory of the in-bbox records: geology_gapfill_readers.py [--out JSON]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import pickle
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon, box

ROOT = Path(r"E:/Projects/Dolomites")
SWISS_RAW = ROOT / "data/raw/swisstopo-geocover"
ISPRA_ZIP = ROOT / "data/raw/ispra-geologia-100k-inspire/Carta_geologica_100k_INSPIRE-GE_nord.zip"
GEOSPHERE_GPKG = ROOT / "data/raw/geosphere-geologicunits-500k/insp_ge_gu_sg500_epsg4258.gpkg"
CACHE_DIR = ROOT / "data/processed/terrain/geology-gapfill-cache"
BBOX_LL = (10.3, 45.8, 12.7, 47.2)
SWISS_SHEETS = ("1179", "1199", "1219", "1239")

NS = {"gml": "http://www.opengis.net/gml/3.2", "ge": "http://inspire.ec.europa.eu/schemas/ge-core/4.0",
      "xlink": "http://www.w3.org/1999/xlink"}
GML, GE, XL = "{%s}" % NS["gml"], "{%s}" % NS["ge"], "{%s}" % NS["xlink"]


def _file_key(path: Path) -> str:
    st = path.stat()
    return f"{path.name}|{st.st_size}|{int(st.st_mtime)}"


def _cached(name: str, key: str, build):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / f"{name}.pkl"
    if f.exists():
        with open(f, "rb") as fh:
            d = pickle.load(fh)
        if d.get("key") == key:
            return d["value"]
    value = build()
    tmp = f.with_name(f.name + ".part")
    with open(tmp, "wb") as fh:
        pickle.dump({"key": key, "value": value}, fh, protocol=5)
    os.replace(tmp, f)
    return value


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- ISPRA 1:100,000 (INSPIRE GML)

def _title(el, tag):
    e = el.find(tag)
    return None if e is None else e.get(XL + "title")


def _href_tail(el, tag):
    e = el.find(tag)
    href = None if e is None else e.get(XL + "href")
    return href.rstrip("/").rsplit("/", 1)[-1] if href else None


def _ring(pos_list: str) -> np.ndarray:
    return np.array(pos_list.split(), dtype=float).reshape(-1, 2)[:, ::-1]  # lat lon -> lon lat


def _parse_ispra(bbox=BBOX_LL) -> dict:
    t0 = time.time()
    units, features = {}, []
    n_mf = 0
    frames = collections.Counter()
    with zipfile.ZipFile(ISPRA_ZIP) as z, z.open(z.namelist()[0]) as fh:
        ctx = ET.iterparse(fh, events=("start", "end"))
        _, root = next(ctx)
        for ev, el in ctx:
            if ev != "end":
                continue
            if el.tag == GE + "GeologicUnit":
                gid = el.get(GML + "id")
                event = el.find(f"{GE}geologicHistory/{GE}GeologicEvent")
                units[gid] = {
                    "id": gid,
                    "name": (el.findtext(GE + "name") or "").strip() or None,
                    "description": (el.findtext(GML + "description") or "").strip() or None,
                    "unit_type": _title(el, GE + "geologicUnitType"),
                    "materials": [m.get(XL + "title") for m in el.iter(GE + "material") if m.get(XL + "title")],
                    "event_process": _title(event, GE + "eventProcess") if event is not None else None,
                    "event_environment": _title(event, GE + "eventEnvironment") if event is not None else None,
                    "older": _href_tail(event, GE + "olderNamedAge") if event is not None else None,
                    "younger": _href_tail(event, GE + "youngerNamedAge") if event is not None else None,
                    "older_title": _title(event, GE + "olderNamedAge") if event is not None else None,
                    "younger_title": _title(event, GE + "youngerNamedAge") if event is not None else None,
                }
                root.clear()
            elif el.tag == GE + "MappedFeature":
                n_mf += 1
                frame = _title(el, GE + "mappingFrame")
                frames[frame] += 1
                spec = (el.find(GE + "specification").get(XL + "href") or "").lstrip("#")
                polys = el.findall(f"{GE}shape//{GML}Polygon")
                for poly in polys:
                    ext = _ring(poly.findtext(f"{GML}exterior/{GML}LinearRing/{GML}posList"))
                    if (ext[:, 0].max() < bbox[0] or ext[:, 0].min() > bbox[2] or
                            ext[:, 1].max() < bbox[1] or ext[:, 1].min() > bbox[3]):
                        continue
                    holes = [_ring(r.text) for r in poly.findall(f"{GML}interior/{GML}LinearRing/{GML}posList")]
                    features.append({"mf_id": el.get(GML + "id"), "unit": spec, "frame": frame,
                                     "wkb": shapely.to_wkb(Polygon(ext, holes))})
                root.clear()
    print(f"[ispra] parsed {len(units)} units, {n_mf} mapped features, {len(features)} polygons near the bbox "
          f"({time.time()-t0:.0f} s)", flush=True)
    return {"units": units, "features": features, "mapping_frames": dict(frames), "mapped_features": n_mf}


def read_ispra(bbox=BBOX_LL) -> dict:
    """-> {"units": {gml id: attrs}, "features": [{"mf_id", "unit", "frame", "geom"}], ...} for polygons whose
    exterior ring's envelope meets the bbox."""
    d = _cached("ispra-100k", _file_key(ISPRA_ZIP) + f"|{bbox}", lambda: _parse_ispra(bbox))
    feats = [{**f, "geom": shapely.from_wkb(f["wkb"])} for f in d["features"]]
    return {**d, "features": feats}


# ---------------------------------------------------------------- GeoSphere Austria 1:500,000 (GeoPackage)

def read_geosphere(bbox=BBOX_LL) -> list[dict]:
    import pyogrio
    df = pyogrio.read_dataframe(GEOSPHERE_GPKG, layer="geologicunitview", bbox=bbox)
    cols = ["id", "description", "name", "inspireId_localId", "geologicUnitType", "material", "representativeLithology",
            "olderNamedAge", "olderNamedAge_href", "youngerNamedAge", "youngerNamedAge_href", "eventEnvironment",
            "eventProcess", "eventName"]
    out = []
    for rec, geom in zip(df[cols].to_dict("records"), df.geometry.values):
        out.append({**{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in rec.items()},
                    "geom": geom})
    return out


# ---------------------------------------------------------------- swisstopo GeoCover (GeoPackages in zips)

SWISS_LAYERS = ("Unconsolidated_Deposits_PLG", "Bedrock_PLG")


def swiss_gpkg(sheet: str) -> Path:
    """Extract the German GeoPackage of a sheet zip (entries use backslashes) into data/raw/swisstopo-geocover/extracted/."""
    zpath = SWISS_RAW / f"geologie-geocover_{sheet}_2056.gpkg.zip"
    out_dir = SWISS_RAW / "extracted" / sheet
    with zipfile.ZipFile(zpath) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".gpkg") and ("\\de\\" in n.lower() or "/de/" in n.lower())]
        if len(names) != 1:
            sys.exit(f"{zpath.name}: expected one German GeoPackage, found {names}")
        target = out_dir / names[0].replace("\\", "/").rsplit("/", 1)[-1]
        info = z.getinfo(names[0])
        if not (target.exists() and target.stat().st_size == info.file_size):
            out_dir.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(target.name + ".part")
            with z.open(info) as src, open(tmp, "wb") as dst:
                for chunk in iter(lambda: src.read(1 << 22), b""):
                    dst.write(chunk)
            os.replace(tmp, target)
    return target


def read_swisstopo(bbox=BBOX_LL) -> list[dict]:
    import pyogrio
    from pyproj import Transformer
    tr = Transformer.from_crs(2056, 4326, always_xy=True)
    bb = box(*bbox)
    out = []
    for sheet in SWISS_SHEETS:
        gpkg = swiss_gpkg(sheet)
        for layer in SWISS_LAYERS:
            df = pyogrio.read_dataframe(gpkg, layer=layer)
            geoms = shapely.transform(np.asarray(df.geometry.values, dtype=object),
                                      lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))
            attrs = df.drop(columns="geometry").to_dict("records")
            for i, (rec, g) in enumerate(zip(attrs, geoms)):
                if g is None or g.is_empty or not g.intersects(bb):
                    continue
                out.append({"sheet": sheet, "layer": layer, "row": i, "geom": g,
                            **{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in rec.items()}})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write an inventory JSON here")
    ap.add_argument("--only", choices=["ispra", "geosphere", "swisstopo"])
    args = ap.parse_args()
    inv = {}
    bb = box(*BBOX_LL)
    if args.only in (None, "ispra"):
        d = read_ispra()
        inb = [f for f in d["features"] if f["geom"].intersects(bb)]
        used = collections.Counter(f["unit"] for f in inb)
        units = d["units"]
        inv["ispra"] = {
            "mapping_frames_all": d["mapping_frames"], "polygons_in_bbox": len(inb), "units_in_bbox": len(used),
            "frames_in_bbox": dict(collections.Counter(f["frame"] for f in inb)),
            "event_process_units": dict(collections.Counter(units[u]["event_process"] for u in used)),
            "age_names": dict(collections.Counter(a for u in used for a in (units[u]["older"], units[u]["younger"]))),
            "units": [{**units[u], "polygons": n} for u, n in used.most_common()],
        }
        print(json.dumps({k: v for k, v in inv["ispra"].items() if k != "units"}, indent=1))
    if args.only in (None, "geosphere"):
        g = read_geosphere()
        inv["geosphere"] = {"polygons": len(g), "units": dict(collections.Counter(r["description"] for r in g))}
        print(f"[geosphere] {len(g)} polygons")
    if args.only in (None, "swisstopo"):
        s = read_swisstopo()
        inv["swisstopo"] = {"polygons": len(s), "per_layer": dict(collections.Counter(r["layer"] for r in s))}
        print(f"[swisstopo] {len(s)} polygons {inv['swisstopo']['per_layer']}")
    if args.out:
        Path(args.out).write_text(json.dumps(inv, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
