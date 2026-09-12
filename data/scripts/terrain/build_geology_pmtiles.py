"""
Build data/processed/terrain/geology-dolomites.pmtiles per contract 2.2 (merged open vector geology).
The archive is a pipeline intermediate (ADR 0006); export_tiles.py turns it into the served tiles.

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe
Needs: shapely>=2.1 on GEOS>=3.12 (coverage_simplify), pyproj, numpy, pyshp, pyogrio, mapbox_vector_tile, pmtiles, Pillow.

Sources, in priority order (ORDER). A source is one SOURCES entry plus a loader load_<name>(ctx) that returns
[(shapely geometry in EPSG:4326, properties)] and a stats dict; adding a source means writing its loader, adding its
SOURCES entry and inserting its id into ORDER. Nothing else in the pipeline names a source.
  1. bz-geology-carg              South Tyrol CARG units, WFS GeoJSON (fetch_geology_bz.py), CC0 1.0, 1:25,000
  2. pat-geology-carta-geologica  Trentino Carta Geologica, shapefiles "substrato" + "sintemi" (fetch_geology_tn.py), CC BY 4.0, 1:10,000
  3. veneto-litologia-250k        Regione del Veneto lithology 1:250,000, WFS GeoJSON (fetch_geology_veneto.py), IODL 2.0
  4. swisstopo-geocover           swisstopo GeoCover 1:25,000, sheets 1179/1199/1219/1239 (GeoPackages), swisstopo OGD terms
  5. ispra-geologia-100k-inspire  ISPRA Carta Geologica d'Italia 1:100,000, INSPIRE GML, CC BY 4.0
  6. geosphere-geologicunits-500k GeoSphere Austria geological units 1:500,000, GeoPackage, CC BY 4.0
Sources 4-6 are read by geology_gapfill_readers.py and only fill area that sources above them leave empty.

Ages (data/scripts/terrain/geology_age_mapping.json, ICS chart via build_ics_chart.parse_chart; the
build stops if app/public/data/ics-chart.json was built from a different chart):
  bz        ETA_CODICE_MAX_IT / ETA_CODICE_MIN_IT -> top-level "terms".
  pat       sigla_cart + nome -> sources.pat.unit_ages (PAT unit legend) -> sources.pat.terms {older, younger};
            units without an age statement -> sources.pat.unit_joins (rows with evidence).
  veneto    depositi_a -> sources.veneto.terms {older, younger}; rows without an age in the class text may carry
            evidence (formation names joined to another cited legend, or a deposit-type rule).
  swisstopo CHRONO_BASE (older) / CHRONO_TOP (younger), German names -> sources.swisstopo.terms; null_pairs and a
            DESCRIPTION-vs-fields contradiction check leave units uncoloured.
  ispra     one decision per GeologicUnit in sources.ispra.units, written by review_ispra_100k_units.py (metamorphic
            and other non-formation events, internal contradictions, disagreement with the detailed maps).
  geosphere olderNamedAge / youngerNamedAge -> sources.geosphere.age_names; non-formation events and ice/water null.
  age_max_ma = start_ma(older), age_min_ma = end_ma(younger), color = colour of younger. Unmapped -> null.
  age_basis: "source" (age stated by the polygon's own map), "legend_join" (formation name joined to another cited
  legend; older/younger must equal the envelope of the evidence, which the build recomputes), "class_rule" (deposit
  type rule with a cited basis), null when there is no age.

Properties: unit_name, unit_code, age_min_ma, age_max_ma, age_label, age_basis, lithology, color, source.

Geometry:
  1. clip every source to the bbox;
  2. node the boundaries of all sources together (snap-rounding, GRID_DEG), polygonize, and give each face to the
     highest-priority source polygon containing it (then the lowest loader index). The result is a valid polygonal
     coverage: neighbours share identical vertices, no area has two units, and nothing is dropped;
  3. per zoom z12..z8, in Web Mercator: merge units smaller than GEN[z].merge_below_px2 tile pixels into the
     neighbour with which they share the longest edge (area stays covered; the merged unit keeps the attributes of
     its largest member), then shapely.coverage_simplify (Visvalingam-Whyatt on shared edges, topology kept);
     z13 is the unsimplified coverage;
  4. each tile takes the zoom's coverage clipped to the tile plus CLIP_BUFFER_UNITS and is quantized to 4096.

Outputs: vector PMTiles (MVT, layer "units", z8-13, bbox 10.3-12.7 E / 45.8-47.2 N); geology-dolomites.meta.json;
geology-coverage.geojson (one dissolved extent per source, simplified 0.005 deg); geology-gaps.geojson (DEM bbox
minus all source coverage); data/processed/terrain/preview/geology-dolomites-by-age.png. Every output is written
to a temp file and renamed into place. geology-suedtirol.pmtiles is read (for the "before" checks) but never written.
Served-tile check: check_geology_tiles.py writes data/processed/terrain/geology-check/{before,after}.json, which
the meta embeds (run export_tiles.py, check_geology_tiles.py --json .../after.json, then this script --qa-only).

Usage: build_geology_pmtiles.py [--force] [--qa-only] [--reuse coverage|generalised] [--workers N]
"""
from __future__ import annotations

import argparse
import collections
import glob
import gzip
import heapq
import itertools
import json
import math
import os
import pickle
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import mapbox_vector_tile
import numpy as np
import shapefile
import shapely
from mapbox_vector_tile.encoder import on_invalid_geometry_make_valid
from pmtiles.tile import Compression, HeaderDict, TileType, zxy_to_tileid
from pmtiles.writer import Writer
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Point, Polygon, box, mapping, shape
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quaternary"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_ics_chart import parse_chart  # noqa: E402  same chart.ttl as ics-chart.json
import geology_gapfill_readers as GF  # noqa: E402

ROOT = Path(r"E:/Projects/Dolomites")
BZ_SOURCE = ROOT / "data/raw/bz-geology-carg/GeologicalUnits-Detailed.geojson"
PAT_RAW = ROOT / "data/raw/pat-geology-carta-geologica"
VEN_SOURCE = ROOT / "data/raw/veneto-litologia-250k/c0501031_litologiareg.geojson"
TERRAIN = ROOT / "app/public/data/terrain"
META = TERRAIN / "geology-dolomites.meta.json"
COVERAGE = TERRAIN / "geology-coverage.geojson"
GAPS = TERRAIN / "geology-gaps.geojson"
ELEVATION_TILEJSON = TERRAIN / "elevation/tiles.json"
PROCESSED = ROOT / "data/processed/terrain"
OUT = PROCESSED / "geology-dolomites.pmtiles"  # intermediate; served tiles: app/public/data/terrain/geology/
BEFORE = PROCESSED / "geology-suedtirol.pmtiles"
FEATURES_PKL = PROCESSED / "geology-dolomites-features.pkl"  # clean coverage, EPSG:4326, + feature keys
PROPS_PKL = PROCESSED / "geology-dolomites-props.pkl"  # properties aligned with FEATURES_PKL
EXTENTS_PKL = PROCESSED / "geology-dolomites-extents.pkl"
GEN_DIR = PROCESSED / "geology-dolomites-gen"  # z{z}.pkl: per-zoom coverage in EPSG:3857
CHECK_DIR = PROCESSED / "geology-check"
PREVIEW = PROCESSED / "preview/geology-dolomites-by-age.png"
MAPPING = ROOT / "data/scripts/terrain/geology_age_mapping.json"
ICS_JSON = ROOT / "app/public/data/ics-chart.json"

BZ, PAT, VEN = "bz-geology-carg", "pat-geology-carta-geologica", "veneto-litologia-250k"
SWISS, ISPRA, GEOS = "swisstopo-geocover", "ispra-geologia-100k-inspire", "geosphere-geologicunits-500k"
SOURCES = {
    BZ: {
        "title": "P_BZ Carta geologica CARG - Geological Units (Detailed)",
        "provider": "Provincia autonoma di Bolzano - Alto Adige, Cartografia provinciale",
        "attribution": "Provincia autonoma di Bolzano - Alto Adige, Cartografia provinciale - P_BZ Carta geologica CARG - CC0 1.0",
        "license": "CC0 1.0 Universal",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "manifest": "data/manifests/bz-geology-carg.yaml",
        "scale": "1:10,000 survey, published 1:25,000", "scale_denominator": 25000,
        "loader": "load_bz",
        "grid": "B", "outline_rgb": (20, 60, 200), "tile_point": ("Schlern", 46.515, 11.576),
    },
    PAT: {
        "title": "Carta Geologica della Provincia autonoma di Trento (Substrato, Sintemi)",
        "provider": "Provincia autonoma di Trento, Servizio Geologico",
        "attribution": "Dati elaborati dal Servizio geologico della Provincia autonoma di Trento - Carta Geologica della PAT - CC BY 4.0 (modified)",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "manifest": "data/manifests/pat-geology-carta-geologica.yaml",
        "scale": "1:10,000", "scale_denominator": 10000,
        "loader": "load_pat",
        "grid": "T", "outline_rgb": (0, 0, 0), "tile_point": ("Latemar", 46.367, 11.567),
    },
    VEN: {
        "title": "Database delle diverse litologie che compongono il territorio della Regione Veneto scala 1:250.000",
        "provider": "Regione del Veneto, Sezione Geologia e georisorse",
        "attribution": "Regione del Veneto - Database delle litologie scala 1:250.000 - IODL 2.0 (https://www.dati.gov.it/content/italian-open-data-license-v20) (modified)",
        "license": "IODL 2.0",
        "license_url": "https://www.dati.gov.it/content/italian-open-data-license-v20",
        "manifest": "data/manifests/veneto-litologia-250k.yaml",
        "scale": "1:250,000 (digitised from 1:100,000 author originals)", "scale_denominator": 250000,
        "loader": "load_veneto",
        "grid": "V", "outline_rgb": (200, 20, 20), "tile_point": ("Civetta", 46.38, 12.05),
    },
    SWISS: {
        "title": "Geological Vector Datasets GeoCover (sheets 1179 Samnaun, 1199 Scuol, 1219 S-charl, 1239 Sta. Maria)",
        "provider": "Federal Office of Topography swisstopo, Swiss Geological Survey",
        "attribution": "Federal Office of Topography swisstopo - GeoCover (modified)",
        "license": "swisstopo terms of use for free geodata (OGD)",
        "license_url": "https://www.swisstopo.admin.ch/en/free-geodata-geoservices-terms-use-ogd",
        "manifest": "data/manifests/swisstopo-geocover.yaml",
        "scale": "1:25,000", "scale_denominator": 25000,
        "loader": "load_swisstopo",
        "grid": "S", "outline_rgb": (0, 140, 70), "tile_point": ("S-charl", 46.72, 10.34),
    },
    ISPRA: {
        "title": "Carta Geologica d'Italia 1:100.000 - Dataset (INSPIRE GE, GML 'nord')",
        "provider": "ISPRA - Dipartimento Servizio Geologico d'Italia",
        "attribution": "ISPRA - Servizio Geologico d'Italia, Carta Geologica d'Italia 1:100.000 (dataset INSPIRE) - CC BY 4.0 (modified)",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "manifest": "data/manifests/ispra-geologia-100k-inspire.yaml",
        "scale": "1:100,000 (sheets surveyed 1880-1980)", "scale_denominator": 100000,
        "loader": "load_ispra",
        "grid": "I", "outline_rgb": (150, 90, 0), "tile_point": ("Bolzano", 46.498, 11.354),
    },
    GEOS: {
        "title": "INSPIRE Geologische Einheiten 1:500.000 Oesterreich (Oberflaechengeologie)",
        "provider": "GeoSphere Austria",
        "attribution": "© GeoSphere Austria - INSPIRE Geologische Einheiten 1:500.000 Österreich - CC BY 4.0 (modified)",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "manifest": "data/manifests/geosphere-geologicunits-500k.yaml",
        "scale": "1:500,000", "scale_denominator": 500000,
        "loader": "load_geosphere",
        "grid": "A", "outline_rgb": (120, 0, 160), "tile_point": ("Mayrhofen", 47.167, 11.865),
    },
}
ORDER = [BZ, PAT, VEN, SWISS, ISPRA, GEOS]  # priority: a face covered by several sources goes to the first one listed
DETAILED_DENOMINATOR = 25000  # sources coarser than this carry a coarse-map note in the meta

BBOX_LL = (10.3, 45.8, 12.7, 47.2)
MIN_Z, MAX_Z = 8, 13
EARTH_R = 6378137.0
ORIGIN_M = math.pi * EARTH_R
TILE_PX, TILE_EXTENT = 512, 4096
GRID_DEG = 1e-7  # snap-rounding grid for noding (about 1 cm); coordinates of the coverage lie on it
CLIP_BUFFER_UNITS = 16  # tile units (of 4096) kept beyond each tile edge so quantized neighbours overlap the seam
# Per zoom, in tile pixels of a 512 px tile: units below merge_below_px2 are merged into a neighbour, then the
# coverage is simplified with a Visvalingam-Whyatt tolerance of simplify_px (removes triangles < tolerance^2).
# z8-z9 use 2 px2 and 1.25 px: with 1 px2 and 1 px three z8-z9 tiles were 1.19-1.22 MB raw (six-source build, 2026-09-12).
GEN = {
    12: {"merge_below_px2": 1.0, "simplify_px": 0.5},
    11: {"merge_below_px2": 1.0, "simplify_px": 1.0},
    10: {"merge_below_px2": 1.0, "simplify_px": 1.0},
    9: {"merge_below_px2": 2.0, "simplify_px": 1.25},
    8: {"merge_below_px2": 2.0, "simplify_px": 1.25},
}
SIMPLIFY_BOUNDARY = True  # also simplify the outer edges of the coverage (towards gaps and the bbox)
COVERAGE_SIMPLIFY_DEG = 0.005
GAPS_OPEN_DEG = 0.0001  # gaps file: morphological opening radius (removes slivers narrower than about 2 x 8-11 m)
GAPS_SIMPLIFY_DEG = 0.0001
GAPS_MIN_PART_DEG2 = 1e-7  # gap parts smaller than about 800 m2 are not listed

POINTS = [  # diagnostic points, approximate locations (not content)
    ("Latemar", 46.367, 11.567), ("Marmolada", 46.435, 11.851), ("Tesero", 46.283, 11.517),
    ("Predazzo", 46.31, 11.60), ("Pale di San Martino", 46.25, 11.87), ("Civetta", 46.38, 12.05),
    ("Cortina", 46.54, 12.14), ("Bletterbach", 46.358, 11.434), ("Schlern", 46.515, 11.576),
    ("Sella", 46.50, 11.833), ("Bolzano", 46.498, 11.354), ("Brixen", 46.716, 11.657), ("Bruneck", 46.80, 11.94),
    ("Mayrhofen", 47.167, 11.865), ("S-charl", 46.72, 10.34),
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- tiles / projection helpers

def to_merc(coords: np.ndarray) -> np.ndarray:
    lon = np.radians(coords[:, 0])
    lat = np.radians(np.clip(coords[:, 1], -85.05, 85.05))
    return np.column_stack((lon * EARTH_R, np.log(np.tan(np.pi / 4 + lat / 2)) * EARTH_R))


def px_m(z: int) -> float:
    """One pixel of a 512 px tile at zoom z, in Web Mercator metres."""
    return 2 * ORIGIN_M / 2 ** z / TILE_PX


def tile_bounds_m(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    span = 2 * ORIGIN_M / 2 ** z
    minx = -ORIGIN_M + x * span
    maxy = ORIGIN_M - y * span
    return (minx, maxy - span, minx + span, maxy)


def tile_bounds_ll(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    n = 2 ** z
    def _lat(yy):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n))))
    return (-180.0 + x * 360.0 / n, _lat(y + 1), -180.0 + (x + 1) * 360.0 / n, _lat(y))


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    rad = math.radians(lat)
    return int((lon + 180.0) / 360.0 * n), int((1.0 - math.log(math.tan(rad) + 1.0 / math.cos(rad)) / math.pi) / 2.0 * n)


def tile_range(z: int, bbox_ll=BBOX_LL) -> tuple[int, int, int, int]:
    tx0, ty0 = lonlat_to_tile(bbox_ll[0], bbox_ll[3], z)
    tx1, ty1 = lonlat_to_tile(bbox_ll[2], bbox_ll[1], z)
    return tx0, ty0, tx1, ty1


def replace_with_retry(tmp: Path, dst: Path, tries: int = 10) -> None:
    """os.replace is atomic, but Windows refuses it while another process holds dst open."""
    for i in range(tries):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(1)


def dump_pickle(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with open(tmp, "wb") as fh:
        pickle.dump(obj, fh, protocol=5)
    replace_with_retry(tmp, path)


def load_pickle(path: Path):
    with open(path, "rb") as fh:
        return pickle.load(fh)


def polygonal(g):
    """Polygon/MultiPolygon part of a geometry (intersections and make_valid can return collections)."""
    if g is None or g.is_empty:
        return None
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    parts = []
    for p in getattr(g, "geoms", []):
        if p.geom_type == "Polygon":
            parts.append(p)
        elif p.geom_type == "MultiPolygon":
            parts.extend(p.geoms)
    return MultiPolygon(parts) if parts else None


def valid(g):
    if g is None or g.is_empty:
        return None
    if g.is_valid:
        return polygonal(g)
    return polygonal(g.buffer(0))


def repair_structure(geoms: np.ndarray) -> tuple[np.ndarray, int]:
    """make_valid(method='structure') on invalid polygons only: keeps every input vertex, so shared edges stay shared."""
    bad = np.flatnonzero(~shapely.is_valid(geoms))
    for i in bad:
        g = polygonal(shapely.make_valid(geoms[i], method="structure", keep_collapsed=False))
        geoms[i] = g if g is not None else geoms[i]
    return geoms, int(len(bad))


# ---------------------------------------------------------------- ages

def load_chart() -> tuple[str, dict[str, dict]]:
    version, chart = parse_chart()
    by_name = {iv["name"]: iv for iv in chart.values()}
    if len(by_name) != len(chart):
        sys.exit("chart.ttl has duplicate interval names")
    ics = json.loads(ICS_JSON.read_text(encoding="utf-8"))
    if ics["version"] != version:
        sys.exit(f"{ICS_JSON} is chart version {ics['version']!r}, chart.ttl is {version!r}; run build_ics_chart.py first")
    for iv in ics["intervals"]:
        c = by_name[iv["name"]]
        if (c["start_ma"], c["end_ma"], c["color"]) != (iv["start_ma"], iv["end_ma"], iv["color"]):
            sys.exit(f"ics-chart.json disagrees with chart.ttl on {iv['name']}; run build_ics_chart.py first")
    return version, by_name


def pair_table(rows: list[dict], key: str, by_name: dict) -> dict[str, dict]:
    """Rows {key, older, younger, note} -> key -> row with chart intervals attached; checks names and order."""
    table = {}
    for r in rows:
        o = by_name.get(r["older"]) if r["older"] else None
        y = by_name.get(r["younger"]) if r["younger"] else None
        if (r["older"] and o is None) or (r["younger"] and y is None):
            sys.exit(f"mapping row {r[key]!r} names an unknown ICS interval")
        if o and y and o["start_ma"] < y["start_ma"]:
            sys.exit(f"mapping row {r[key]!r}: 'older' is younger than 'younger'")
        if r[key] in table:
            sys.exit(f"duplicate mapping row {r[key]!r}")
        table[r[key]] = {**r, "o": o, "y": y}
    return table


def norm_age(s: str) -> str:
    """Whitespace/case/punctuation normalization of PAT age strings (sources.pat.normalization)."""
    s = s.strip().lower()
    s = re.sub(r"\.(?=\S)", ". ", s)
    s = re.sub(r"\bp\.\s*p\b\.?", "p.p", s)
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.rstrip(". ").strip()


BASES = ("source", "legend_join", "class_rule")


class AgeContext:
    """Chart, mapping tables and the unit ages of every source, so a row of one source can cite another's legend.

    Evidence entries of a legend_join / class_rule row:
      {"authority": "pat-unit-legend", "unit": "SIGLA|NAME"}        age statement of a PAT unit (own or parent)
      {"authority": "bz-carg-attributes", "sigla": "DCS"}            ETA_CODICE_* of every South Tyrol polygon with that SIGLA_1
      {"authority": "veneto-litologia-250k", "depositi_a": "..."}   age in the class text of a Veneto class
      {"authority": <id in mapping 'authorities'>, "age_text", "older", "younger", "where", "quote"}   any other cited document
    Only ages stated by a map itself are accepted as evidence (never another join)."""

    def __init__(self, mapping_json: dict, by_name: dict):
        self.m, self.by_name = mapping_json, by_name
        self.bz_terms = {}
        for row in mapping_json["terms"]:
            if row["interval"] is not None and row["interval"] not in by_name:
                sys.exit(f"mapping table names unknown ICS interval {row['interval']!r}")
            self.bz_terms[row["it"]] = {**row, "chart": by_name.get(row["interval"])}
        self.pat = mapping_json["sources"][PAT]
        self.pat_terms = pair_table(self.pat["terms"], "age", by_name)
        self.ven_terms = pair_table(mapping_json["sources"][VEN]["terms"], "depositi_a", by_name)
        self.authorities = mapping_json.get("authorities", {})
        self.bz_units: dict | None = None  # SIGLA_1 -> Counter[(older string, younger string)]
        self.bz_names: dict = collections.defaultdict(collections.Counter)  # SIGLA_1 -> Counter[NOME_IT_1]
        self._resolved: dict[str, tuple] = {}

    def chart(self, name: str | None, where: str):
        if name is None:
            return None
        if name not in self.by_name:
            sys.exit(f"{where}: {name!r} is not an ICS chart interval")
        return self.by_name[name]

    # South Tyrol age fields ---------------------------------------------------------------------------------
    def bz_order(self, p: dict) -> tuple:
        """-> (older chart interval, younger chart interval, older string, younger string, swapped)."""
        young_it, old_it = p.get("ETA_CODICE_MIN_IT"), p.get("ETA_CODICE_MAX_IT")
        for it, de_field in ((young_it, "ETA_CODICE_MIN_DE"), (old_it, "ETA_CODICE_MAX_DE")):
            if it is None:
                continue
            if it not in self.bz_terms:
                sys.exit(f"age string {it!r} is not in {MAPPING.name}")
            if self.bz_terms[it]["de"] != p.get(de_field):
                sys.exit(f"feature {p.get('ID')}: {de_field}={p.get(de_field)!r} but table twin of {it!r} is {self.bz_terms[it]['de']!r}")
        young = self.bz_terms[young_it]["chart"] if young_it else None
        old = self.bz_terms[old_it]["chart"] if old_it else None
        swapped = False
        if young and old and not (old["start_ma"] >= young["start_ma"] and old["end_ma"] >= young["end_ma"]):
            if not (old["start_ma"] <= young["start_ma"] and old["end_ma"] <= young["end_ma"]):
                sys.exit(f"feature {p.get('ID')}: cannot order {old_it!r} and {young_it!r} by age")
            young, old, young_it, old_it, swapped = old, young, old_it, young_it, True
        return old, young, old_it, young_it, swapped

    def ensure_bz_units(self) -> None:
        if self.bz_units is not None:
            return
        log("reading South Tyrol age fields for legend joins ...")
        units = collections.defaultdict(collections.Counter)
        for f in json.loads(BZ_SOURCE.read_text(encoding="utf-8"))["features"]:
            p = f["properties"]
            if (p.get("SIGLA_1") or "").strip():
                _, _, o_it, y_it, _ = self.bz_order(p)
                units[p["SIGLA_1"].strip()][(o_it, y_it)] += 1
                self.bz_names[p["SIGLA_1"].strip()][(p.get("NOME_IT_1") or "").strip()] += 1
        self.bz_units = units

    # evidence -------------------------------------------------------------------------------------------------
    def resolve(self, ev: dict, where: str) -> dict:
        a = ev.get("authority")
        if a == "pat-unit-legend":
            row = self.pat["unit_ages"]["units"].get(ev["unit"])
            if row is None or not row["age"]:
                sys.exit(f"{where}: PAT unit {ev['unit']!r} has no age statement")
            t = self.pat_terms.get(norm_age(row["age"]))
            if t is None or not (t["o"] and t["y"]):
                sys.exit(f"{where}: PAT age {row['age']!r} of {ev['unit']!r} is not fully mapped")
            return {"older": t["o"], "younger": t["y"], "age_text": row["age"], "ref": f"PAT unit legend {ev['unit']}"}
        if a == "bz-carg-attributes":
            self.ensure_bz_units()
            pairs = self.bz_units.get(ev["sigla"])
            if not pairs:
                sys.exit(f"{where}: no South Tyrol polygon has SIGLA_1 {ev['sigla']!r}")
            ivs = []
            for o_it, y_it in pairs:
                o = self.bz_terms[o_it]["chart"] if o_it else None
                y = self.bz_terms[y_it]["chart"] if y_it else None
                if not (o and y):
                    sys.exit(f"{where}: South Tyrol {ev['sigla']} age {o_it!r} / {y_it!r} is not fully mapped")
                ivs.append((o, y))
            o = max((iv[0] for iv in ivs), key=lambda iv: iv["start_ma"])
            y = min((iv[1] for iv in ivs), key=lambda iv: iv["end_ma"])
            text = "; ".join(f"{o_it} - {y_it}" if o_it != y_it else o_it for o_it, y_it in pairs)
            return {"older": o, "younger": y, "age_text": text, "ref": f"South Tyrol CARG SIGLA_1 {ev['sigla']}"}
        if a == VEN:
            t = self.ven_terms.get(ev["depositi_a"])
            if t is None or not (t["o"] and t["y"]) or t.get("age_basis", "source") != "source":
                sys.exit(f"{where}: Veneto class {ev['depositi_a']!r} has no age of its own")
            m = re.search(r"\(([^()]*)\)\s*$", ev["depositi_a"])
            return {"older": t["o"], "younger": t["y"], "age_text": m.group(1) if m else "", "ref": f"Veneto class {ev['depositi_a']}"}
        if a not in self.authorities:
            sys.exit(f"{where}: evidence authority {a!r} is not listed in the mapping's 'authorities'")
        o, y = self.by_name.get(ev.get("older")), self.by_name.get(ev.get("younger"))
        if not (o and y) or o["start_ma"] < y["start_ma"] or not ev.get("age_text"):
            sys.exit(f"{where}: cited evidence needs age_text and valid older/younger chart names")
        return {"older": o, "younger": y, "age_text": ev["age_text"], "ref": a}

    def row_age(self, row: dict, where: str) -> tuple:
        """-> (older interval, younger interval, age_basis) for a mapping row, checking joins against their evidence."""
        o = self.by_name.get(row["older"]) if row.get("older") else None
        y = self.by_name.get(row["younger"]) if row.get("younger") else None
        if (row.get("older") and o is None) or (row.get("younger") and y is None):
            sys.exit(f"{where}: unknown ICS interval in older/younger")
        basis = row.get("age_basis")
        if basis is None:
            if row.get("evidence"):
                sys.exit(f"{where}: evidence given but no age_basis")
            return o, y, ("source" if (o or y) else None)
        if basis not in BASES:
            sys.exit(f"{where}: unknown age_basis {basis!r}")
        if basis == "source" and not row.get("evidence"):
            return o, y, basis
        if where not in self._resolved:
            evs = row.get("evidence") or []
            if not evs or not (o and y):
                sys.exit(f"{where}: a {basis} row needs evidence and both older and younger")
            res = [self.resolve(e, where) for e in evs]
            start = max(r["older"]["start_ma"] for r in res)
            end = min(r["younger"]["end_ma"] for r in res)
            if not (math.isclose(o["start_ma"], start) and math.isclose(y["end_ma"], end)):
                sys.exit(f"{where}: older/younger {row['older']}/{row['younger']} ({o['start_ma']}-{y['end_ma']} Ma) "
                         f"differ from the envelope of the evidence ({start}-{end} Ma)")
            self._resolved[where] = tuple(res)
        return o, y, basis


class Tally:
    def __init__(self):
        self.n = collections.Counter()
        self.unmapped = collections.Counter()
        self.reasons: dict[str, str] = {}
        self.basis = collections.Counter()
        self.joined = collections.Counter()
        self.rules = collections.Counter()

    def add(self, age_min, age_max, strings: list[str], color, unmapped: dict[str, str], basis=None, joined=None, rule=None):
        bounds = (age_min is not None) + (age_max is not None)
        self.n["units"] += 1
        self.n[("units_no_bound", "units_one_bound", "units_both_bounds")[bounds]] += 1
        self.n["units_without_age_string"] += not strings
        self.n["units_with_color"] += color is not None
        self.basis[str(basis)] += 1
        if joined:
            self.joined[joined] += 1
        if rule:
            self.rules[rule] += 1
        for s, why in unmapped.items():
            self.unmapped[s] += 1
            self.reasons[s] = why

    def stats(self) -> dict:
        out = {**{k: self.n[k] for k in ("units", "units_both_bounds", "units_one_bound", "units_no_bound",
                                         "units_without_age_string", "units_with_color")},
               "age_basis_units": dict(self.basis.most_common()),
               "units_dated_by_join_or_rule": dict(self.joined.most_common()),
               "unmapped_strings": {s: {"units": c, "reason": self.reasons[s]} for s, c in self.unmapped.most_common()}}
        if self.rules:
            out["age_rule_polygons_loaded"] = dict(self.rules.most_common())
        return out


# ---------------------------------------------------------------- sources

def load_bz(ctx: AgeContext) -> tuple[list, dict]:
    print(f"[{BZ}] loading {BZ_SOURCE.name} ({BZ_SOURCE.stat().st_size/1e6:.1f} MB) ...", flush=True)
    fc = json.loads(BZ_SOURCE.read_text(encoding="utf-8"))
    feats, tally, swapped = [], Tally(), collections.Counter()
    units = collections.defaultdict(collections.Counter)
    for f in fc["features"]:
        p = f["properties"]
        geom = valid(shape(f["geometry"])) if f["geometry"] else None
        if geom is None:
            continue
        old, young, old_it, young_it, sw = ctx.bz_order(p)
        if sw:
            swapped[f"{young_it} / {old_it}"] += 1
        if (p.get("SIGLA_1") or "").strip():
            units[p["SIGLA_1"].strip()][(old_it, young_it)] += 1
            ctx.bz_names[p["SIGLA_1"].strip()][(p.get("NOME_IT_1") or "").strip()] += 1
        age_min = young["end_ma"] if young else None
        age_max = old["start_ma"] if old else None
        strings = [s for s in (old_it, young_it) if s]
        basis = "source" if (age_min is not None or age_max is not None) else None
        tally.add(age_min, age_max, strings, young["color"] if young else None,
                  {s: ctx.bz_terms[s]["note"] for s in strings if ctx.bz_terms[s]["chart"] is None}, basis)
        feats.append((geom, {
            "unit_name": (p.get("NOME_IT_1") or "").strip() or None,
            "unit_code": (p.get("SIGLA_1") or "").strip() or None,
            "age_min_ma": age_min,
            "age_max_ma": age_max,
            "age_label": " - ".join(dict.fromkeys(strings)) or None,
            "age_basis": basis,
            "lithology": (p.get("TEG_DESC_I") or "").strip() or None,
            "color": young["color"] if young else None,
            "source": BZ,
        }))
    if ctx.bz_units is None:
        ctx.bz_units = units
    stats = {"source_features": len(fc["features"]), **tally.stats(),
             "units_with_swapped_age_fields": sum(swapped.values()), "swapped_age_field_pairs": dict(swapped.most_common())}
    print(f"[{BZ}] {len(feats)} features", flush=True)
    return feats, stats


def load_pat(ctx: AgeContext) -> tuple[list, dict]:
    src = ctx.pat
    units = src["unit_ages"]["units"]
    terms = ctx.pat_terms
    joins = []
    for k, row in enumerate(src.get("unit_joins", [])):
        where = f"{PAT} unit_joins[{k}] ({row.get('label', '')})"
        o, y, basis = ctx.row_age(row, where)
        joins.append((re.compile(row["match_sigla"]), re.compile(row["match_name"]), o, y, basis, row.get("label", where)))
    lith = {}
    for layer in ("depositi_quaternari", "depositi_frana"):
        r = shapefile.Reader(glob.glob(str(PAT_RAW / layer / "*.shp"))[0], encoding="latin-1")
        fields = [f[0] for f in r.fields[1:]]
        for rec in r.iterRecords():
            lith[rec[fields.index("tipo_qu")]] = rec[fields.index("denom")]
    tr = Transformer.from_crs(25832, 4326, always_xy=True)
    feats, tally, n_source, inherited = [], Tally(), 0, 0
    for layer in ("substrato", "sintemi"):
        r = shapefile.Reader(glob.glob(str(PAT_RAW / layer / "*.shp"))[0], encoding="latin-1")
        fields = [f[0] for f in r.fields[1:]]
        i_s, i_n, i_t = fields.index("sigla_cart"), fields.index("nome"), fields.index("tipo_qu")
        geoms, recs = [], []
        for sr in r.iterShapeRecords():
            n_source += 1
            if not sr.shape.points:
                continue
            geoms.append(shape(sr.shape.__geo_interface__))
            recs.append(sr.record)
        print(f"[{PAT}] {layer}: {len(geoms)} shapes, reprojecting EPSG:25832 -> EPSG:4326 ...", flush=True)
        geoms = shapely.transform(np.array(geoms, dtype=object),
                                  lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))
        for g, rec in zip(geoms, recs):
            g = valid(g)
            if g is None:
                continue
            sigla, name = rec[i_s].strip(), rec[i_n].strip()
            row = units.get(f"{rec[i_s]}|{rec[i_n]}") if sigla else None
            age = row["age"] if row else None
            inherited += bool(row and row["resolved"].startswith("parent"))
            t = None
            if age is not None:
                t = terms.get(norm_age(age))
                if t is None:
                    sys.exit(f"PAT age string {age!r} (normalized {norm_age(age)!r}) is not in {MAPPING.name}")
            o, y = (t["o"], t["y"]) if t else (None, None)
            basis = "source" if (o or y) else None
            joined = None
            if age is None and sigla:
                for re_s, re_n, jo, jy, jb, label in joins:
                    if re_s.search(sigla) and re_n.search(name):
                        o, y, basis, joined = jo, jy, jb, label
                        break
            age_min = y["end_ma"] if y else None
            age_max = o["start_ma"] if o else None
            unmapped = {age: t.get("note", "")} if t and not (o and y) else {}
            tally.add(age_min, age_max, [age] if age else [], y["color"] if y else None, unmapped, basis, joined)
            feats.append((g, {
                "unit_name": name or None,
                "unit_code": sigla or None,
                "age_min_ma": age_min,
                "age_max_ma": age_max,
                "age_label": age,
                "age_basis": basis,
                "lithology": lith.get(rec[i_t]) if layer == "sintemi" else None,
                "color": y["color"] if y else None,
                "source": PAT,
            }))
    joined_keys = {k for k, r in units.items() if not r["age"] and r["sigla"]
                   and any(js.search(r["sigla"]) and jn.search(r["name"]) for js, jn, *_ in joins)}
    no_age = sorted(((r["sigla"], r["name"], r["polygons"], r["resolved"]) for k, r in units.items()
                     if not r["age"] and k not in joined_keys), key=lambda x: -x[2])
    stats = {"source_features": n_source, **tally.stats(), "units_age_from_parent_formation": inherited,
             "legend_units_without_age_statement_or_join": [{"unit_code": s, "unit_name": n, "polygons": c, "why": w} for s, n, c, w in no_age]}
    print(f"[{PAT}] {len(feats)} features", flush=True)
    return feats, stats


def load_veneto(ctx: AgeContext) -> tuple[list, dict]:
    terms = ctx.ven_terms
    ages = {k: ctx.row_age(row, f"{VEN} terms {k!r}") for k, row in terms.items()}
    fc = json.loads(VEN_SOURCE.read_text(encoding="utf-8"))
    bbox = box(*BBOX_LL)
    feats, tally = [], Tally()
    for f in fc["features"]:
        g = shape(f["geometry"])
        if not g.intersects(bbox):
            continue
        g = valid(g.intersection(bbox)) if g.is_valid else valid(valid(g).intersection(bbox))
        if g is None:
            continue
        p = f["properties"]
        if p["depositi_a"] not in terms:
            sys.exit(f"Veneto depositi_a {p['depositi_a']!r} is not in {MAPPING.name}")
        o, y, basis = ages[p["depositi_a"]]
        m = re.search(r"\(([^()]*)\)\s*$", p["depositi_a"])
        label = m.group(1).strip() if (m and basis == "source") else None
        age_min = y["end_ma"] if y else None
        age_max = o["start_ma"] if o else None
        unmapped = {p["depositi_a"]: terms[p["depositi_a"]].get("note", "")} if not (o and y) else {}
        joined = p["depositi_a"] if basis in ("legend_join", "class_rule") else None
        tally.add(age_min, age_max, [label] if label else [], y["color"] if y else None, unmapped, basis, joined)
        feats.append((g, {
            "unit_name": p["depositi_a"],
            "unit_code": p.get("uc_lege"),
            "age_min_ma": age_min,
            "age_max_ma": age_max,
            "age_label": label,
            "age_basis": basis,
            "lithology": p.get("materiali_"),
            "color": y["color"] if y else None,
            "source": VEN,
        }))
    stats = {"source_features": len(fc["features"]), "source_features_in_bbox": len(feats), **tally.stats()}
    print(f"[{VEN}] {len(feats)} features in bbox", flush=True)
    return feats, stats


def _text(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def load_swisstopo(ctx: AgeContext) -> tuple[list, dict]:
    cfg = ctx.m["sources"][SWISS]
    terms = {}
    for t in cfg["terms"]:
        terms[t["de"]] = ctx.chart(t["interval"], f"{SWISS} terms {t['de']!r}") if t["interval"] else None
    desc_terms = {k: ctx.chart(v, f"{SWISS} description_age_terms") for k, v in cfg["description_age_terms"].items()}
    word = re.compile(r"(" + "|".join(sorted(map(re.escape, desc_terms), key=len, reverse=True)) + r")\s+bis\s+("
                      + "|".join(sorted(map(re.escape, desc_terms), key=len, reverse=True)) + r")")
    rows = GF.read_swisstopo(BBOX_LL)
    feats, tally, reversed_pairs = [], Tally(), collections.Counter()
    contradictions = collections.Counter()
    for i, r in enumerate(rows):
        f = cfg["fields"][r["layer"]]
        top_s, base_s = _text(r.get(f["younger"])), _text(r.get(f["older"]))
        for s in (top_s, base_s):
            if s is not None and s not in terms:
                sys.exit(f"{SWISS}: chrono name {s!r} is not in the mapping terms")
        y = terms.get(top_s) if top_s else None
        o = terms.get(base_s) if base_s else None
        if o and y and o["start_ma"] < y["start_ma"] and o["end_ma"] < y["end_ma"]:
            reversed_pairs[f"{top_s}|{base_s}"] += 1
            o, y = y, o
        rule = "source"
        pair = f"{top_s}|{base_s}"
        if pair in cfg["null_pairs"]:
            o = y = None
            rule = "null_pair"
        desc = _text(r.get(f["description"])) if f["description"] else None
        if rule == "source" and desc and (o or y):
            mm = word.search(desc)
            if mm:
                a, b = desc_terms[mm.group(1)], desc_terms[mm.group(2)]
                d_start, d_end = max(a["start_ma"], b["start_ma"]), min(a["end_ma"], b["end_ma"])
                f_start = o["start_ma"] if o else math.inf
                f_end = y["end_ma"] if y else -math.inf
                if not (d_start > f_end and d_end < f_start):
                    contradictions[(mm.group(0), pair, (_text(r.get(f["name"])) or "")[:80])] += 1
                    o = y = None
                    rule = "description_contradiction"
        age_min = y["end_ma"] if y else None
        age_max = o["start_ma"] if o else None
        basis = "source" if (age_min is not None or age_max is not None) else None
        name = _text(r.get(f["name"]))
        if name is None or name.lower() in ("unbekannt", "not applicable", "nicht anwendbar"):
            name = _text(r.get(f["lithology"])) or name
        label = (base_s if base_s == top_s else " - ".join(s for s in (base_s, top_s) if s)) if basis else None
        tally.add(age_min, age_max, [s for s in (base_s, top_s) if s], y["color"] if y else None,
                  {s: "no chart unit" for s in (base_s, top_s) if s and terms.get(s) is None}, basis, rule=rule)
        feats.append((r["geom"], {
            "unit_name": name,
            "unit_code": _text(r.get(f["code"])),
            "age_min_ma": age_min,
            "age_max_ma": age_max,
            "age_label": label,
            "age_basis": basis,
            "lithology": _text(r.get(f["lithology"])),
            "color": y["color"] if y else None,
            "source": SWISS,
        }))
    geoms = [valid(g) for g, _ in feats]
    feats = [(g, p) for g, (_, p) in zip(geoms, feats)]
    feats_rules = [(g, p) for g, p in feats if g is not None]
    stats = {"source_features_in_bbox": len(rows), **tally.stats(),
             "age_pairs_reordered": dict(reversed_pairs),
             "description_contradictions": [{"description_range": k[0], "fields": k[1], "unit": k[2], "polygons": c}
                                            for k, c in contradictions.most_common()]}
    print(f"[{SWISS}] {len(feats_rules)} features", flush=True)
    return feats_rules, stats


def ispra_age_name(tail: str | None, cfg: dict) -> str | None:
    if tail is None:
        return None
    if tail in cfg["age_names"]:
        return cfg["age_names"][tail]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", tail)


def load_ispra(ctx: AgeContext) -> tuple[list, dict]:
    cfg = ctx.m["sources"][ISPRA]
    review = cfg.get("units")
    if not review:
        sys.exit(f"{ISPRA}: no per-unit review in the mapping; run review_ispra_100k_units.py first")
    d = GF.read_ispra(BBOX_LL)
    units = d["units"]
    bb = box(*BBOX_LL)
    feats, tally = [], Tally()
    ages = {}
    for f in d["features"]:
        g = f["geom"]
        if not g.intersects(bb):
            continue
        g = valid(g)
        if g is None:
            continue
        uid = f["unit"]
        u, row = units[uid], review.get(uid)
        if row is None:
            sys.exit(f"{ISPRA}: unit {uid} has no review row; re-run review_ispra_100k_units.py")
        if uid not in ages:
            where = f"{ISPRA} unit {uid}"
            if row["decision"] == "source":
                ages[uid] = (ctx.chart(row["older"], where), ctx.chart(row["younger"], where), "source")
            elif row["decision"] in ("legend_join",):
                ages[uid] = ctx.row_age(row, where)
            elif row["decision"] == "null":
                ages[uid] = (None, None, None)
            else:
                sys.exit(f"{where}: unknown decision {row['decision']!r}")
        o, y, basis = ages[uid]
        label = None
        if basis == "source":
            label = u["older_title"] if u["older_title"] == u["younger_title"] else f"{u['older_title']} - {u['younger_title']}"
        age_min = y["end_ma"] if y else None
        age_max = o["start_ma"] if o else None
        tally.add(age_min, age_max, [label] if label else [], y["color"] if y else None, {}, basis,
                  u["name"] if basis == "legend_join" else None, rule=row["rule"])
        feats.append((g, {
            "unit_name": u["name"],
            "unit_code": uid,
            "age_min_ma": age_min,
            "age_max_ma": age_max,
            "age_label": label,
            "age_basis": basis,
            "lithology": ", ".join(u["materials"]) or None,
            "color": y["color"] if y else None,
            "source": ISPRA,
        }))
    stats = {"units_in_file": len(units), "mapped_features_in_file": d["mapped_features"], "polygons_near_bbox": len(feats),
             "units_near_bbox": len({p["unit_code"] for _, p in feats}), **tally.stats(),
             "review": cfg.get("review", {}).get("counts")}
    print(f"[{ISPRA}] {len(feats)} features", flush=True)
    return feats, stats


def load_geosphere(ctx: AgeContext) -> tuple[list, dict]:
    cfg = ctx.m["sources"][GEOS]
    fl = cfg["fields"]
    rows = GF.read_geosphere(BBOX_LL)
    feats, tally = [], Tally()
    bb = box(*BBOX_LL)
    for r in rows:
        g = valid(r["geom"])
        if g is None or not g.intersects(bb):
            continue
        uid = str(r[fl["code"]])
        o_s, y_s, proc = r[fl["older"]], r[fl["younger"]], r[fl["process"]]
        for s in (o_s, y_s):
            if s not in cfg["age_names"]:
                sys.exit(f"{GEOS}: age name {s!r} is not in the mapping")
        if proc not in cfg["event_process"]:
            sys.exit(f"{GEOS}: event process {proc!r} is not in the mapping")
        where = f"{GEOS} unit {uid}"
        o, y = ctx.chart(cfg["age_names"][o_s], where), ctx.chart(cfg["age_names"][y_s], where)
        if o and y and o["start_ma"] < y["start_ma"]:
            o, y = y, o
        rule = "source"
        if uid in cfg["null_units"]:
            o = y = None
            rule = "null_unit"
        elif cfg["event_process"][proc] != "formation":
            o = y = None
            rule = "event_not_formation"
        age_min = y["end_ma"] if y else None
        age_max = o["start_ma"] if o else None
        basis = "source" if (o or y) else None
        label = (o_s if o_s == y_s else f"{o_s} - {y_s}") if basis else None
        tally.add(age_min, age_max, [label] if label else [], y["color"] if y else None, {}, basis, rule=rule)
        feats.append((g, {
            "unit_name": _text(r[fl["name"]]),
            "unit_code": uid,
            "age_min_ma": age_min,
            "age_max_ma": age_max,
            "age_label": label,
            "age_basis": basis,
            "lithology": _text(r[fl["lithology"]]),
            "color": y["color"] if y else None,
            "source": GEOS,
        }))
    stats = {"polygons_in_bbox": len(feats), **tally.stats()}
    print(f"[{GEOS}] {len(feats)} features", flush=True)
    return feats, stats


def load_sources(ctx: AgeContext) -> dict[str, tuple[list, dict]]:
    return {sid: globals()[SOURCES[sid]["loader"]](ctx) for sid in ORDER}


# ---------------------------------------------------------------- coverage

def clip_to_bbox(by_source: dict[str, list]) -> tuple[list, list, list, dict]:
    bbox_geom = box(*BBOX_LL)
    geoms, props, keys, stats = [], [], [], {}
    for sid in ORDER:
        feats = by_source[sid]
        inside = shapely.covered_by(np.array([g for g, _ in feats], dtype=object), bbox_geom) if feats else []
        outside = 0
        for i, ((g, p), ins) in enumerate(zip(feats, inside)):
            if not ins:
                g = polygonal(g.intersection(bbox_geom))
                if g is None or g.area == 0:
                    outside += 1
                    continue
            geoms.append(g)
            props.append(p)
            keys.append((sid, i))
        stats[sid] = {"features_in": len(feats), "features_outside_bbox": outside}
    return geoms, props, keys, stats


def build_coverage(geoms: list, keys: list, clip_stats: dict) -> tuple[list, dict]:
    """Node all boundaries, polygonize, give each face to the highest-priority polygon containing it.
    -> (geometry or None per input feature, stats)."""
    g = np.array(geoms, dtype=object)
    rank = np.array([ORDER.index(k[0]) for k in keys])
    src = np.array([k[0] for k in keys])
    t0 = time.time()
    log(f"noding the boundaries of {len(g)} polygons ({int(shapely.get_num_coordinates(g).sum())} vertices), grid {GRID_DEG} deg ...")
    lines = shapely.union_all(shapely.boundary(g), grid_size=GRID_DEG)
    log(f"noded in {time.time()-t0:.0f} s; polygonizing ...")
    faces = shapely.get_parts(shapely.polygonize(shapely.get_parts(lines)))
    del lines
    log(f"{len(faces)} faces ({time.time()-t0:.0f} s); assigning faces by priority ...")
    pts = shapely.point_on_surface(faces)
    fi, gi = STRtree(g).query(pts, predicate="within")
    order = np.lexsort((gi, rank[gi], fi))
    fi_s, gi_s = fi[order], gi[order]
    first = np.r_[True, fi_s[1:] != fi_s[:-1]]
    owner = np.full(len(faces), -1)
    owner[fi_s[first]] = gi_s[first]
    ncand = np.bincount(fi, minlength=len(faces))
    nsrc = np.zeros(len(faces), dtype=int)
    for f_, _s in {(int(a), s) for a, s in zip(fi, src[gi])}:
        nsrc[f_] += 1
    face_area = shapely.area(faces)
    deg2_km2 = (111.32 * 111.32 * math.cos(math.radians((BBOX_LL[1] + BBOX_LL[3]) / 2)))
    covered = np.flatnonzero(owner >= 0)
    o = owner[covered]
    srt = np.argsort(o, kind="stable")
    o_s, f_s = o[srt], covered[srt]
    cuts = np.flatnonzero(np.r_[True, o_s[1:] != o_s[:-1], True])
    out = np.empty(len(g), dtype=object)
    for a, b in zip(cuts[:-1], cuts[1:]):
        k = int(o_s[a])
        out[k] = faces[f_s[a]] if b - a == 1 else polygonal(shapely.coverage_union_all(faces[f_s[a:b]]))
    present = np.flatnonzero(np.array([x is not None for x in out]))
    fixed_geoms, n_repaired = repair_structure(out[present])
    out[present] = fixed_geoms
    log(f"faces grouped into {len(present)} features, {n_repaired} repaired with make_valid(structure) ({time.time()-t0:.0f} s)")
    area_in = shapely.area(g)
    for sid in ORDER:
        idx = np.flatnonzero(src == sid)
        removed = sum(out[i] is None for i in idx)
        cut = sum(out[i] is not None and out[i].area < area_in[i] * (1 - 1e-6) for i in idx)
        clip_stats[sid].update({"features_removed_as_covered": int(removed), "features_cut": int(cut),
                                "features_out": int(len(idx) - removed)})
    stats = {
        "method": ("union_all of all polygon boundaries with grid_size (snap-rounding noding), polygonize, face -> "
                   "polygon containing its point_on_surface with the best (priority, loader index); faces of one polygon "
                   "merged with coverage_union_all; unions that come out invalid (self-touching rings) are split with "
                   "make_valid(method='structure'), which keeps every vertex"),
        "grid_deg": GRID_DEG,
        "faces": int(len(faces)),
        "gap_faces": int((owner < 0).sum()),
        "gap_faces_area_km2": round(float(face_area[owner < 0].sum() * deg2_km2), 3),
        "faces_in_several_polygons_of_one_source": int(((ncand > 1) & (nsrc == 1)).sum()),
        "faces_in_several_polygons_of_one_source_area_km2": round(float(face_area[(ncand > 1) & (nsrc == 1)].sum() * deg2_km2), 4),
        "faces_in_several_sources": int((nsrc > 1).sum()),
        "faces_in_several_sources_area_km2": round(float(face_area[nsrc > 1].sum() * deg2_km2), 3),
        "features_repaired": n_repaired,
        "seconds": round(time.time() - t0),
    }
    return list(out), stats


def segment_adjacency(merc: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Shared edge length between the polygons of a valid coverage (identical segments), -> (a, b, length) with a < b."""
    parts, pidx = shapely.get_parts(merc, return_index=True)
    rings, ridx = shapely.get_rings(parts, return_index=True)
    coords, cidx = shapely.get_coordinates(rings, return_index=True)
    same = cidx[1:] == cidx[:-1]
    p0, p1 = coords[:-1][same], coords[1:][same]
    owner = pidx[ridx[cidx[:-1][same]]]
    del coords, cidx
    swap = (p0[:, 0] > p1[:, 0]) | ((p0[:, 0] == p1[:, 0]) & (p0[:, 1] > p1[:, 1]))
    a = np.where(swap[:, None], p1, p0)
    b = np.where(swap[:, None], p0, p1)
    del p0, p1, swap
    order = np.lexsort((b[:, 1], b[:, 0], a[:, 1], a[:, 0]))
    a, b, owner = a[order], b[order], owner[order]
    eq = np.flatnonzero((a[1:] == a[:-1]).all(axis=1) & (b[1:] == b[:-1]).all(axis=1))
    o1, o2 = owner[eq], owner[eq + 1]
    keep = o1 != o2
    eq, o1, o2 = eq[keep], o1[keep], o2[keep]
    seglen = np.hypot(b[eq, 0] - a[eq, 0], b[eq, 1] - a[eq, 1])
    lo, hi = np.minimum(o1, o2), np.maximum(o1, o2)
    n = len(merc)
    key = lo.astype(np.int64) * n + hi
    uk, inv = np.unique(key, return_inverse=True)
    return (uk // n).astype(np.int64), (uk % n).astype(np.int64), np.bincount(inv, weights=seglen)


def merge_schedule(areas: np.ndarray, pa: np.ndarray, pb: np.ndarray, plen: np.ndarray) -> dict[int, dict]:
    """Hierarchical merge of small units into the neighbour sharing the longest edge, z12 down to z8.
    -> {z: {"root": group root per feature, "rep": representative feature per feature's group, "stats"}}."""
    n = len(areas)
    adj = [dict() for _ in range(n)]
    for a, b, length in zip(pa.tolist(), pb.tolist(), plen.tolist()):
        adj[a][b] = length
        adj[b][a] = length
    parent = list(range(n))
    area = areas.tolist()
    rep = list(range(n))
    rep_area = areas.tolist()
    out = {}
    for z in sorted(GEN, reverse=True):
        limit = GEN[z]["merge_below_px2"] * px_m(z) ** 2
        heap = [(area[i], i) for i in range(n) if parent[i] == i and area[i] < limit]
        heapq.heapify(heap)
        merges = isolated = 0
        while heap:
            a, g = heapq.heappop(heap)
            if parent[g] != g or area[g] != a or a >= limit:
                continue
            nb = adj[g]
            if not nb:
                isolated += 1
                continue
            h = max(nb, key=lambda k: (nb[k], area[k]))
            big, small = (h, g) if len(adj[h]) >= len(adj[g]) else (g, h)
            total = area[g] + area[h]
            parent[small] = big
            area[big] = total
            if rep_area[small] > rep_area[big]:
                rep[big], rep_area[big] = rep[small], rep_area[small]
            ab = adj[big]
            for k, length in adj[small].items():
                if k == big:
                    continue
                ab[k] = ab.get(k, 0.0) + length
                ak = adj[k]
                del ak[small]
                ak[big] = ak.get(big, 0.0) + length
            ab.pop(small, None)
            adj[small] = {}
            merges += 1
            if total < limit:
                heapq.heappush(heap, (total, big))
        root = np.array(parent)
        while True:
            nxt = root[root]
            if np.array_equal(nxt, root):
                break
            root = nxt
        groups = int(len(np.unique(root)))
        out[z] = {"root": root, "rep": np.array(rep)[root],
                  "stats": {"merge_below_px2": GEN[z]["merge_below_px2"], "merge_below_m2_mercator": round(limit, 1),
                            "units_in": int(n), "groups_out": groups, "merges": merges,
                            "small_units_without_neighbour_kept": isolated}}
        log(f"z{z}: merge below {limit:.0f} m2 (Mercator) -> {groups} groups")
    return out


def _generalise_zoom(args: tuple) -> dict:
    z, member_file = args
    t0 = time.time()
    merc = shapely.from_wkb(load_pickle(GEN_DIR / "coverage-merc.pkl"))
    d = np.load(member_file)
    root, rep = d["root"], d["rep"]
    uniq, inv = np.unique(root, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    cuts = np.flatnonzero(np.r_[True, inv[order][1:] != inv[order][:-1], True])
    geoms, reps = [], []
    for a, b in zip(cuts[:-1], cuts[1:]):
        members = order[a:b]
        geoms.append(merc[members[0]] if b - a == 1 else polygonal(shapely.coverage_union_all(merc[members])))
        reps.append(int(rep[members[0]]))
    geoms = np.array(geoms, dtype=object)
    geoms, n_union_repaired = repair_structure(geoms)
    tol = GEN[z]["simplify_px"] * px_m(z)
    simp = shapely.coverage_simplify(geoms, tol, simplify_boundary=SIMPLIFY_BOUNDARY)
    invalid_after = int((~shapely.is_valid(simp)).sum())
    simp, n_simp_repaired = repair_structure(simp)
    stats = {"zoom": z, "simplify_px": GEN[z]["simplify_px"], "simplify_tolerance_m_mercator": round(tol, 2),
             "simplify_boundary": SIMPLIFY_BOUNDARY, "polygons": int(len(simp)),
             "vertices_before": int(shapely.get_num_coordinates(geoms).sum()),
             "vertices_after": int(shapely.get_num_coordinates(simp).sum()),
             "unions_repaired": n_union_repaired,
             "empty_after_simplify": int(shapely.is_empty(simp).sum()),
             "invalid_after_simplify": invalid_after, "repaired_after_simplify": n_simp_repaired,
             "still_invalid": int((~shapely.is_valid(simp)).sum()),
             "coverage_is_valid_after_simplify": bool(shapely.coverage_is_valid(simp))}
    dump_pickle({"z": z, "wkb": shapely.to_wkb(simp), "rep": np.array(reps)}, GEN_DIR / f"z{z}.pkl")
    stats["seconds"] = round(time.time() - t0)
    return stats


def generalise(lonlat: list) -> dict:
    t0 = time.time()
    merc = shapely.transform(np.array(lonlat, dtype=object), to_merc)
    dump_pickle(shapely.to_wkb(merc), GEN_DIR / "coverage-merc.pkl")
    dump_pickle({"z": MAX_Z, "wkb": shapely.to_wkb(merc), "rep": np.arange(len(merc))}, GEN_DIR / f"z{MAX_Z}.pkl")
    log(f"shared-edge adjacency of {len(merc)} units ...")
    pa, pb, plen = segment_adjacency(merc)
    log(f"{len(pa)} neighbour pairs ({time.time()-t0:.0f} s)")
    sched = merge_schedule(shapely.area(merc), pa, pb, plen)
    del merc
    tasks = []
    for z, s in sched.items():
        f = GEN_DIR / f"members-z{z}.npz"
        np.savez(f, root=s["root"], rep=s["rep"])
        tasks.append((z, str(f)))
    log("union + coverage_simplify per zoom (one process per zoom) ...")
    stats = {}
    with ProcessPoolExecutor(max_workers=len(tasks)) as ex:
        for st in ex.map(_generalise_zoom, tasks):
            z = st["zoom"]
            stats[str(z)] = {**sched[z]["stats"], **st}
            log(f"z{z}: {st}")
    stats[str(MAX_Z)] = {"note": "unsimplified coverage"}
    return {"per_zoom": stats, "seconds": round(time.time() - t0), "clip_buffer_tile_units": CLIP_BUFFER_UNITS}


# ---------------------------------------------------------------- tile encoding

_W: dict = {}


def _init_worker(zpkl: str) -> None:
    d = load_pickle(Path(zpkl))
    _W["geoms"] = shapely.from_wkb(d["wkb"])
    _W["rep"] = d["rep"]
    _W["props"] = load_pickle(PROPS_PKL)
    _W["tree"] = STRtree(_W["geoms"])


def _encode_task(zxy: tuple[int, int, int]) -> bytes | None:
    return encode_tile(*zxy, _W["geoms"], _W["rep"], _W["props"], _W["tree"])


def encode_tile(z: int, x: int, y: int, geoms, rep, props, tree) -> bytes | None:
    bounds = tile_bounds_m(z, x, y)
    pad = (bounds[2] - bounds[0]) * CLIP_BUFFER_UNITS / TILE_EXTENT
    clip = (bounds[0] - pad, bounds[1] - pad, bounds[2] + pad, bounds[3] + pad)
    clip_box = box(*clip)
    idx = tree.query(clip_box, predicate="intersects")
    if len(idx) == 0:
        return None
    inside = shapely.contains_properly(clip_box, geoms[idx])
    kept = []
    for i, ins in zip(idx, inside):
        g = geoms[i]
        if not ins:
            g = polygonal(shapely.clip_by_rect(g, *clip))
            if g is None:
                continue
        kept.append({"geometry": mapping(g), "properties": props[rep[i]]})
    if not kept:
        return None
    encoded = mapbox_vector_tile.encode(
        [{"name": "units", "features": kept}],
        default_options={"quantize_bounds": bounds, "extents": TILE_EXTENT, "y_coord_down": False,
                         "on_invalid_geometry": on_invalid_geometry_make_valid},
    )
    return gzip.compress(encoded, compresslevel=6)


def write_archive(chart_version: str, workers: int) -> dict:
    tmp = OUT.with_suffix(".pmtiles.part")
    if tmp.exists():
        tmp.unlink()
    written = empty = 0
    bytes_per_zoom = collections.Counter()
    max_tile = {}
    t0 = time.time()
    with open(tmp, "wb") as fh:
        w = Writer(fh)
        for z in range(MIN_Z, MAX_Z + 1):
            tx0, ty0, tx1, ty1 = tile_range(z)
            tiles = sorted((zxy_to_tileid(z, x, y), z, x, y) for x in range(tx0, tx1 + 1) for y in range(ty0, ty1 + 1))
            n_workers = max(1, min(workers, len(tiles)))
            log(f"z{z}: encoding {len(tiles)} tiles with {n_workers} workers ...")
            with ProcessPoolExecutor(max_workers=n_workers, initializer=_init_worker,
                                     initargs=(str(GEN_DIR / f"z{z}.pkl"),)) as ex:
                for (tid, _, x, y), data in zip(tiles, ex.map(_encode_task, [t[1:] for t in tiles], chunksize=2)):
                    if data is None:
                        empty += 1
                        continue
                    w.write_tile(tid, data)
                    written += 1
                    bytes_per_zoom[z] += len(data)
                    if len(data) > max_tile.get(z, (0,))[0]:
                        max_tile[z] = (len(data), f"{z}/{x}/{y}")
            log(f"z{z}: {bytes_per_zoom[z]/1e6:.2f} MB gzip, largest {max_tile.get(z)} ({time.time()-t0:.0f} s)")
        e7 = [int(v * 10_000_000) for v in BBOX_LL]
        header = HeaderDict(
            version=3, root_offset=0, root_length=0, metadata_offset=0, metadata_length=0,
            leaf_directory_offset=0, leaf_directory_length=0, tile_data_offset=0, tile_data_length=0,
            addressed_tiles_count=0, tile_entries_count=0, tile_contents_count=0, clustered=True,
            internal_compression=Compression.GZIP, tile_compression=Compression.GZIP, tile_type=TileType.MVT,
            min_zoom=MIN_Z, max_zoom=MAX_Z, min_lon_e7=e7[0], min_lat_e7=e7[1], max_lon_e7=e7[2], max_lat_e7=e7[3],
            center_zoom=10, center_lon_e7=(e7[0] + e7[2]) // 2, center_lat_e7=(e7[1] + e7[3]) // 2,
        )
        metadata = {
            "name": "Dolomites geology (merged open vector maps)",
            "description": ("Geological units merged from " + "; ".join(f"{s} ({SOURCES[s]['scale']}, {SOURCES[s]['license']})" for s in ORDER)
                            + ", in that priority, as one gap-free polygon coverage generalised per zoom. Ages and colours "
                            f"derived via the ICS chart {chart_version}; property 'source' names the dataset, 'age_basis' "
                            "how the age was obtained."),
            "attribution": " | ".join(SOURCES[s]["attribution"] for s in ORDER),
            "format": "pbf", "minzoom": MIN_Z, "maxzoom": MAX_Z, "bounds": list(BBOX_LL),
            "center": [(BBOX_LL[0] + BBOX_LL[2]) / 2, (BBOX_LL[1] + BBOX_LL[3]) / 2, 10],
            "vector_layers": [{
                "id": "units", "description": "Geological units", "minzoom": MIN_Z, "maxzoom": MAX_Z,
                "fields": {"unit_name": "String", "unit_code": "String", "age_min_ma": "Number", "age_max_ma": "Number",
                           "age_label": "String", "age_basis": "String", "lithology": "String", "color": "String",
                           "source": "String"},
            }],
            "source_datasets": ORDER,
        }
        w.finalize(header, metadata)
    replace_with_retry(tmp, OUT)
    log(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB); {written} tiles, {empty} empty, {time.time()-t0:.0f} s")
    return {"tiles_written": written, "tiles_empty": empty,
            "tile_bytes_per_zoom": {str(z): bytes_per_zoom[z] for z in sorted(bytes_per_zoom)},
            "largest_tile_gzip_per_zoom": {str(z): {"bytes": v[0], "tile": v[1]} for z, v in sorted(max_tile.items())}}


def build(workers: int, reuse: str | None) -> dict:
    chart_version, by_name = load_chart()
    ctx = AgeContext(json.loads(MAPPING.read_text(encoding="utf-8")), by_name)
    loaded = load_sources(ctx)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    prev = load_pickle(FEATURES_PKL) if (reuse and FEATURES_PKL.exists()) else None
    loader_counts = {sid: len(loaded[sid][0]) for sid in ORDER}
    if prev is not None and isinstance(prev, dict) and prev.get("loader_counts") == loader_counts and prev.get("order") == ORDER:
        log(f"reusing the coverage in {FEATURES_PKL.name}; properties refreshed from the loaders")
        keys = prev["keys"]
        props = [loaded[sid][0][i][1] for sid, i in keys]
        lonlat = list(shapely.from_wkb(prev["wkb"]))
        clip_stats, cov_stats = prev["clip_stats"], prev["coverage_stats"]
    else:
        if reuse:
            log("cannot reuse the coverage (missing, or the loaders returned different feature counts); rebuilding")
            reuse = None
        geoms, props_in, keys_in, clip_stats = clip_to_bbox({sid: loaded[sid][0] for sid in ORDER})
        out, cov_stats = build_coverage(geoms, keys_in, clip_stats)
        del geoms
        keep = [i for i, g in enumerate(out) if g is not None]
        lonlat = [out[i] for i in keep]
        props = [props_in[i] for i in keep]
        keys = [keys_in[i] for i in keep]
        t0 = time.time()
        arr = np.array(lonlat, dtype=object)
        cov_stats["coverage_is_valid"] = bool(shapely.coverage_is_valid(arr))
        cov_stats["invalid_polygons"] = int((~shapely.is_valid(arr)).sum())
        log(f"coverage_is_valid={cov_stats['coverage_is_valid']} invalid_polygons={cov_stats['invalid_polygons']} ({time.time()-t0:.0f} s)")
        dump_pickle({"wkb": shapely.to_wkb(lonlat), "keys": keys, "loader_counts": loader_counts, "order": ORDER,
                     "clip_stats": clip_stats, "coverage_stats": cov_stats}, FEATURES_PKL)
    dump_pickle(props, PROPS_PKL)
    src = np.array([k[0] for k in keys])
    extents = {}
    for sid in ORDER:
        sel = [lonlat[i] for i in np.flatnonzero(src == sid)]
        extents[sid] = polygonal(shapely.union_all(np.array(sel, dtype=object), grid_size=GRID_DEG)) if sel else None
    dump_pickle({sid: (shapely.to_wkb(g) if g is not None else None) for sid, g in extents.items()}, EXTENTS_PKL)
    write_coverage(extents)

    gen_files = [GEN_DIR / f"z{z}.pkl" for z in range(MIN_Z, MAX_Z + 1)]
    result_path = PROCESSED / "geology-dolomites-build-result.json"
    if reuse == "generalised" and all(f.exists() for f in gen_files) and result_path.exists():
        log("reusing the per-zoom coverages in " + str(GEN_DIR))
        gen_stats = json.loads(result_path.read_text(encoding="utf-8"))["generalisation"]
    else:
        gen_stats = generalise(lonlat)
    del lonlat
    arch = write_archive(chart_version, workers)
    per_source = collections.Counter(src.tolist())
    return {"chart_version": chart_version, **arch, "generalisation": gen_stats, "coverage_stats": cov_stats,
            "source_stats": {sid: loaded[sid][1] for sid in ORDER}, "clip_stats": clip_stats,
            "features_in_archive_per_source": {sid: per_source[sid] for sid in ORDER},
            "archive_units_per_source": archive_unit_stats(keys, props)}


def archive_unit_stats(keys: list, props: list) -> dict:
    """Polygons in the archive (after priority clipping) per source: dated, uncoloured, age_basis, and the ISPRA units present."""
    out = {}
    for sid in ORDER:
        sel = [p for (s, _), p in zip(keys, props) if s == sid]
        out[sid] = {"polygons": len(sel), "with_color": sum(p["color"] is not None for p in sel),
                    "age_basis": dict(collections.Counter(str(p["age_basis"]) for p in sel).most_common())}
    out[ISPRA]["units"] = dict(collections.Counter(p["unit_code"] for (s, _), p in zip(keys, props) if s == ISPRA))
    return out


def rounded_valid(g, digits: int = 5):
    """Round coordinates to `digits` decimals and repair (simplify and rounding can pinch rings)."""
    def rnd(o):
        if isinstance(o, (list, tuple)):
            return [rnd(v) for v in o]
        return round(o, digits)
    gj = mapping(g)
    r = shape({"type": gj["type"], "coordinates": rnd(gj["coordinates"])})
    for _ in range(3):
        if r.is_valid:
            break
        r = polygonal(shapely.make_valid(r))
        if r is None:
            return None
        gj = mapping(r)
        r = shape({"type": gj["type"], "coordinates": rnd(gj["coordinates"])})
    return r if r.is_valid else None


def write_geojson(path: Path, fc: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    replace_with_retry(tmp, path)
    print(f"wrote {path} ({path.stat().st_size/1e3:.0f} kB)", flush=True)


def write_coverage(extents: dict) -> None:
    features = []
    for sid in ORDER:
        g = extents.get(sid)
        if g is None:
            continue
        s = polygonal(shapely.make_valid(g.simplify(COVERAGE_SIMPLIFY_DEG, preserve_topology=True)))
        r = rounded_valid(s) if s is not None else None
        if r is None:
            sys.exit(f"coverage outline of {sid} is invalid after repair")
        features.append({"type": "Feature", "properties": {
            "source": sid, "attribution": SOURCES[sid]["attribution"], "license": SOURCES[sid]["license"],
            "scale": SOURCES[sid]["scale"], "scale_denominator": SOURCES[sid]["scale_denominator"], "label": "observed"},
            "geometry": mapping(r)})
    write_geojson(COVERAGE, {
        "type": "FeatureCollection", "name": "geology-coverage",
        "description": f"Dissolved extent of each geology source in geology-dolomites.pmtiles after priority clipping, simplified {COVERAGE_SIMPLIFY_DEG} deg. Outside these outlines there is no open vector geology in the archive (see geology-gaps.geojson).",
        "features": features})


def write_gaps(extents: dict) -> dict:
    t0 = time.time()
    tj = json.loads(ELEVATION_TILEJSON.read_text(encoding="utf-8"))
    bounds = tj["bounds"]
    dem = box(*bounds)
    cov = shapely.union_all([g for g in extents.values() if g is not None], grid_size=GRID_DEG)
    raw = polygonal(shapely.difference(dem, cov, grid_size=GRID_DEG))
    from pyproj import Geod
    geod = Geod(ellps="WGS84")
    km2 = lambda g: abs(geod.geometry_area_perimeter(g)[0]) / 1e6 if g is not None else 0.0
    stats = {"dem_bounds": bounds, "dem_bbox_area_km2": round(km2(dem), 1), "raw_gap_area_km2": round(km2(raw), 2)}
    g = None
    if raw is not None:
        g = polygonal(raw.buffer(-GAPS_OPEN_DEG, join_style="mitre").buffer(GAPS_OPEN_DEG, join_style="mitre"))
        g = polygonal(shapely.make_valid(g.simplify(GAPS_SIMPLIFY_DEG, preserve_topology=True))) if g is not None else None
    parts = [p for p in (shapely.get_parts(g) if g is not None else []) if p.area >= GAPS_MIN_PART_DEG2]
    g = rounded_valid(MultiPolygon(parts)) if parts else None
    tr = Transformer.from_crs(4326, 25832, always_xy=True)
    features, classes = [], collections.defaultdict(lambda: {"parts": 0, "area_km2": 0.0})
    for p in (shapely.get_parts(g) if g is not None else []):
        u = shapely.transform(p, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))
        width = 2 * u.area / u.length
        cls = "under_50m" if width < 50 else ("50_to_200m" if width < 200 else "200m_or_more")
        classes[cls]["parts"] += 1
        classes[cls]["area_km2"] += u.area / 1e6
        features.append((u.area, {"type": "Feature", "properties": {
            "kind": "no_open_geology", "area_km2": round(u.area / 1e6, 4), "mean_width_m": int(round(width))},
            "geometry": mapping(p)}))
    features = [f for _, f in sorted(features, key=lambda t: -t[0])]
    stats.update({"listed_gap_area_km2": round(km2(g), 2), "parts": len(features),
                  "parts_by_mean_width": {k: {"parts": v["parts"], "area_km2": round(v["area_km2"], 2)} for k, v in classes.items()},
                  "mean_width_method": "2 x area / perimeter of each part in EPSG:25832"})
    write_geojson(GAPS, {
        "type": "FeatureCollection", "name": "geology-gaps",
        "description": (f"Terrain DEM bbox {bounds} minus the union of all geology source coverage in geology-dolomites.pmtiles "
                        f"({', '.join(ORDER)}): areas with no open vector geology, one feature per part, largest first, with "
                        "area_km2 and mean_width_m (2 x area / perimeter in EPSG:25832) so a viewer can tell thin seams along sheet "
                        f"and source borders from real gaps. Display geometry: opening with radius {GAPS_OPEN_DEG} deg (drops "
                        f"slivers narrower than about 15-20 m), simplified {GAPS_SIMPLIFY_DEG} deg, parts under {GAPS_MIN_PART_DEG2} "
                        "deg2 omitted, coordinates rounded to 5 decimals and repaired. Geology is not extended into the gaps."),
        "features": features})
    stats["seconds"] = round(time.time() - t0)
    log(f"gaps: {stats}")
    return stats


# ---------------------------------------------------------------- verification

class TileProbe:
    """Decode tiles from an archive and test points against their polygons (tile-pixel space)."""

    def __init__(self, archive: Path, quantize: str):
        from pmtiles.reader import MmapSource, Reader
        self.fh = open(archive, "rb")
        self.reader = Reader(MmapSource(self.fh))
        self.quantize = quantize  # "merc" for this build, "lonlat" for geology-suedtirol.pmtiles
        self.cache: dict = {}

    def layer(self, z, x, y):
        key = (z, x, y)
        if key not in self.cache:
            data = self.reader.get(z, x, y)
            feats = []
            if data:
                for f in mapbox_vector_tile.decode(gzip.decompress(data)).get("units", {}).get("features", []):
                    g = polygonal(shapely.make_valid(shape(f["geometry"])))
                    if g is not None:
                        feats.append((g, f["properties"]))
            self.cache[key] = (feats, STRtree([g for g, _ in feats]) if feats else None)
        return self.cache[key]

    def pixel(self, z, x, y, lon, lat):
        if self.quantize == "merc":
            minx, miny, maxx, maxy = tile_bounds_m(z, x, y)
            mx, my = to_merc(np.array([[lon, lat]]))[0]
        else:
            minx, miny, maxx, maxy = tile_bounds_ll(z, x, y)
            mx, my = lon, lat
        return Point((mx - minx) / (maxx - minx) * 4096, (my - miny) / (maxy - miny) * 4096)

    def at(self, lon, lat, z):
        x, y = lonlat_to_tile(lon, lat, z)
        feats, tree = self.layer(z, x, y)
        if tree is None:
            return None
        pt = self.pixel(z, x, y, lon, lat)
        for i in tree.query(pt, predicate="intersects"):
            return feats[i][1]
        return None


def verify(result_stats: dict | None) -> dict:
    after = TileProbe(OUT, "merc")
    before = TileProbe(BEFORE, "lonlat") if BEFORE.exists() else None
    out: dict = {}

    print("\npoint coverage (z12 tiles; before = geology-suedtirol.pmtiles, after = geology-dolomites.pmtiles)")
    pts = []
    for name, lat, lon in POINTS:
        b = before.at(lon, lat, 12) if before else None
        a = after.at(lon, lat, 12)
        row = {"name": name, "lat": lat, "lon": lon, "before_covered": b is not None, "after_covered": a is not None,
               "after": {k: a.get(k) for k in ("source", "unit_code", "unit_name", "age_label", "age_basis", "age_min_ma", "age_max_ma", "color")} if a else None}
        pts.append(row)
        desc = f"{a.get('source')}: {a.get('unit_name')} [{a.get('age_label')}, {a.get('age_basis')}]" if a else "NOT COVERED"
        print(f"  {name:20s} before={'yes' if b else 'no ':3s} after={desc}")
    out["points"] = {"method": "decode the z12 tile containing the point and test point-in-polygon on its features", "results": pts}

    def grid(probe, label):
        rows = []
        lats = [BBOX_LL[3] - 0.025 - 0.05 * j for j in range(round((BBOX_LL[3] - BBOX_LL[1]) / 0.05))]
        lons = [BBOX_LL[0] + 0.025 + 0.05 * i for i in range(round((BBOX_LL[2] - BBOX_LL[0]) / 0.05))]
        counts = collections.Counter()
        for lat in lats:
            line = ""
            for lon in lons:
                p = probe.at(lon, lat, 12) if probe else None
                ch = "." if p is None else SOURCES.get(p.get("source", BZ), SOURCES[BZ])["grid"]
                counts[ch] += 1
                line += ch
            rows.append(f"{lat:6.3f} {line}")
        legend = ", ".join(f"{SOURCES[s]['grid']} {s}" for s in ORDER)
        print(f"\n{label}: 0.05 deg grid, cell centres, z12 tiles ('.' none, {legend})")
        print("\n".join(rows))
        print("  cells:", dict(counts))
        return {"rows": rows, "cells": dict(counts)}

    out["coverage_grid"] = {"method": "0.05 deg cells over the bbox; cell centre tested against decoded z12 tiles; top row is north",
                            "columns_lon_start": BBOX_LL[0] + 0.025, "before": grid(before, "BEFORE"), "after": grid(after, "AFTER")}

    print("\none decoded tile per source (z11)")
    tiles = {}
    for sid in ORDER:
        pname, lat, lon = SOURCES[sid]["tile_point"]
        x, y = lonlat_to_tile(lon, lat, 11)
        feats, _ = after.layer(11, x, y)
        mine = [p for _, p in feats if p.get("source") == sid]
        names = sorted({p.get("unit_name") for p in mine if p.get("unit_name")})
        tiles[sid] = {"tile": {"z": 11, "x": x, "y": y}, "near": pname, "features_in_tile": len(feats),
                      "features_of_source": len(mine), "distinct_unit_names": len(names), "unit_names": names[:60]}
        print(f"  {sid} z11/{x}/{y} near {pname}: {len(mine)} of {len(feats)} features, {len(names)} distinct unit_name")
    out["tiles_per_source"] = tiles
    out["borders"] = border_check()
    return out


def border_check() -> dict:
    """Overlap and gap between the clipped source extents along shared borders, in EPSG:25832 metres."""
    ext = {sid: shapely.from_wkb(w) for sid, w in load_pickle(EXTENTS_PKL).items() if w is not None}
    tr = Transformer.from_crs(4326, 25832, always_xy=True)
    utm = {sid: shapely.transform(g, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1]))) for sid, g in ext.items()}
    back = Transformer.from_crs(25832, 4326, always_xy=True)
    res = []
    print("\nborder check (extents after clipping, EPSG:25832)")
    for a, b in itertools.combinations(ORDER, 2):
        A, B = utm.get(a), utm.get(b)
        if A is None or B is None:
            continue
        region = A.envelope.buffer(200).intersection(B.envelope.buffer(200))
        if region.is_empty:
            continue
        Ar, Br = A.intersection(region), B.intersection(region)
        if Ar.is_empty or Br.is_empty or Ar.distance(Br) > 60:
            continue
        overlap = Ar.intersection(Br).area  # exact extents
        As, Bs = Ar.simplify(1.0), Br.simplify(1.0)  # 1 m simplification only to make the buffers tractable
        shared = As.boundary.intersection(Bs.buffer(1.0)).length
        near = As.buffer(50).intersection(Bs.buffer(50))
        gap = polygonal(near.difference(As.union(Bs)))
        gap_area = gap.area if gap is not None else 0.0
        wide = polygonal(gap.buffer(-25)) if gap is not None else None
        wide_parts = [p for p in (list(wide.geoms) if isinstance(wide, MultiPolygon) else ([wide] if wide is not None else []))
                      if p.area > 1.0]
        examples = []
        for p in sorted(wide_parts, key=lambda g: -g.area)[:5]:
            lon, lat = back.transform(p.centroid.x, p.centroid.y)
            examples.append({"lon": round(lon, 4), "lat": round(lat, 4), "core_area_m2": round(p.area)})
        row = {"pair": f"{a} / {b}", "shared_border_m": round(shared), "overlap_m2": round(overlap, 1),
               "gap_area_within_50m_of_both_m2": round(gap_area), "gap_parts_wider_than_50m": len(wide_parts),
               "wide_gap_core_area_m2": round(sum(p.area for p in wide_parts)), "largest_wide_gaps": examples}
        res.append(row)
        print(f"  {row}")
    return {"method": ("Source extents (after priority clipping) in EPSG:25832, simplified 1 m. overlap = area of A AND B. "
                       "gap = (A buffered 50 m AND B buffered 50 m) minus (A OR B), i.e. unmapped strips lying within 50 m of both "
                       "sources; a gap part is 'wider than 50 m' if it survives an inward buffer of 25 m. Pairs further than 60 m "
                       "apart are skipped."), "pairs": res}


def make_preview() -> None:
    """z10 mosaic decoded from the archive, units in their ICS colour (grey where null), coverage outlines on top."""
    from PIL import Image, ImageDraw
    from pmtiles.reader import MmapSource, Reader
    z, tile_px = 10, 256
    tx0, ty0, tx1, ty1 = tile_range(z)
    img = Image.new("RGB", ((tx1 - tx0 + 1) * tile_px, (ty1 - ty0 + 1) * tile_px), (240, 238, 232))
    draw = ImageDraw.Draw(img)
    rgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) if h else (190, 190, 190)
    with open(OUT, "rb") as fh:
        rd = Reader(MmapSource(fh))
        for xi, x in enumerate(range(tx0, tx1 + 1)):
            for yi, y in enumerate(range(ty0, ty1 + 1)):
                data = rd.get(z, x, y)
                if not data:
                    continue
                for f in mapbox_vector_tile.decode(gzip.decompress(data)).get("units", {}).get("features", []):
                    g = f["geometry"]
                    polys = [g["coordinates"]] if g["type"] == "Polygon" else (g["coordinates"] if g["type"] == "MultiPolygon" else [])
                    for poly in polys:
                        for k, ring in enumerate(poly):
                            pts = [(xi * tile_px + p[0] / 4096 * tile_px, yi * tile_px + (1 - p[1] / 4096) * tile_px) for p in ring]
                            if len(pts) >= 3:
                                draw.polygon(pts, fill=rgb(f["properties"].get("color")) if k == 0 else (240, 238, 232))
    minx, _, _, _ = tile_bounds_m(z, tx0, ty0)
    _, _, _, maxy = tile_bounds_m(z, tx0, ty0)
    span = 2 * ORIGIN_M / 2 ** z
    cov = json.loads(COVERAGE.read_text(encoding="utf-8"))
    for f in cov["features"]:
        g = shape(f["geometry"])
        for poly in (g.geoms if isinstance(g, MultiPolygon) else [g]):
            for ring in [poly.exterior, *poly.interiors]:
                m = to_merc(np.asarray(ring.coords))
                pts = [((mx - minx) / span * tile_px, (maxy - my) / span * tile_px) for mx, my in m]
                draw.line(pts, fill=SOURCES[f["properties"]["source"]]["outline_rgb"], width=2)
    for i, sid in enumerate(ORDER):
        draw.rectangle([10, 10 + i * 18, 24, 24 + i * 18], outline=SOURCES[sid]["outline_rgb"], width=3)
        draw.text((30, 12 + i * 18), f"{sid} ({SOURCES[sid]['scale']}; {SOURCES[sid]['license']})", fill=(0, 0, 0))
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    tmp = PREVIEW.with_name(PREVIEW.stem + ".part.png")
    img.save(tmp, optimize=True)
    replace_with_retry(tmp, PREVIEW)
    print(f"wrote {PREVIEW} ({PREVIEW.stat().st_size/1024:.0f} kB)")


def served_tile_checks() -> dict:
    """check_geology_tiles.py results on the served tiles: before (previous build) and after (this build, if newer)."""
    out = {}
    for label in ("before", "after"):
        f = CHECK_DIR / f"{label}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if label == "after" and OUT.exists() and f.stat().st_mtime < OUT.stat().st_mtime:
            out["after_note"] = f"{f.name} is older than {OUT.name}; export the tiles and re-run check_geology_tiles.py"
            continue
        out[label] = {"file": str(f.relative_to(ROOT)).replace("\\", "/"), **d}
    out["script"] = "data/scripts/terrain/check_geology_tiles.py"
    return out


def ispra_review_summary(result: dict, mapping_json: dict) -> dict:
    """ISPRA units in the archive by decision rule, and every unit with a detected contradiction that the archive shows."""
    cfg = mapping_json["sources"].get(ISPRA, {})
    units = cfg.get("units", {})
    present = result.get("archive_units_per_source", {}).get(ISPRA, {}).get("units", {})
    by_rule_units, by_rule_polys = collections.Counter(), collections.Counter()
    listed = []
    for uid, n in present.items():
        row = units.get(uid, {})
        by_rule_units[row.get("rule")] += 1
        by_rule_polys[row.get("rule")] += n
        if row.get("flags"):
            listed.append({"unit": uid, "polygons_in_archive": n, "name": row.get("name"), "description": (row.get("description") or "")[:200],
                           "event_process": row.get("event_process"), "ispra_age": f"{row.get('ispra_older')} - {row.get('ispra_younger')}",
                           "flags": row.get("flags"), "decision": row.get("decision"), "rule": row.get("rule"),
                           "applied_age": f"{row.get('older')} - {row.get('younger')}" if row.get("older") else None})
    listed.sort(key=lambda r: -r["polygons_in_archive"])
    return {"rules": cfg.get("rules"), "units_in_archive_by_rule": dict(by_rule_units.most_common()),
            "polygons_in_archive_by_rule": dict(by_rule_polys.most_common()),
            "contradictions_in_archive": listed, "review": cfg.get("review")}


def write_meta(result: dict, verification: dict, gaps_stats: dict | None) -> None:
    v = result["chart_version"]
    mapping_json = json.loads(MAPPING.read_text(encoding="utf-8"))
    sources = []
    for rank, sid in enumerate(ORDER, 1):
        s = SOURCES[sid]
        arch = result.get("archive_units_per_source", {}).get(sid, {})
        sources.append({
            "dataset_id": sid, "priority": rank, "title": s["title"], "provider": s["provider"],
            "attribution": s["attribution"], "license": s["license"], "license_url": s["license_url"],
            "manifest": s["manifest"], "scale": s["scale"], "scale_denominator": s["scale_denominator"],
            "coarser_than_1_25000": s["scale_denominator"] > DETAILED_DENOMINATOR,
            "scale_note": (f"{s['scale']}: much coarser than the 1:10,000-1:25,000 provincial maps; its polygons are not detailed "
                           "mapping at z11-13." if s["scale_denominator"] > DETAILED_DENOMINATOR else None),
            "label": "observed",
            "clipping": result["clip_stats"][sid],
            "features_in_archive": result["features_in_archive_per_source"][sid],
            "archive_polygons": {k: val for k, val in arch.items() if k != "units"},
            "ages": result["source_stats"][sid],
        })
    checks = served_tile_checks()
    served_bytes = {str(r["zoom"]): r["bytes"] for r in checks["after"]["per_zoom"]} if "after" in checks else None
    scales = "; ".join(f"{sid} {SOURCES[sid]['scale']}" for sid in ORDER)
    meta = {
        "dataset_id": "geology-dolomites",
        "label": "observed",
        "source_ref": ORDER,
        "attribution": " | ".join(SOURCES[s]["attribution"] for s in ORDER),
        "license": " + ".join(f"{SOURCES[s]['license']} ({s})" for s in ORDER),
        "generated": date.today().isoformat(),
        "script": "data/scripts/terrain/build_geology_pmtiles.py",
        "archive": OUT.name,
        "archive_bytes": OUT.stat().st_size,
        "tile_format": "mvt", "layer": "units", "crs": "EPSG:3857", "bounds_wgs84": list(BBOX_LL),
        "min_zoom": MIN_Z, "max_zoom": MAX_Z,
        "tiles_written": result["tiles_written"], "tiles_empty": result["tiles_empty"],
        "tile_bytes_per_zoom": result["tile_bytes_per_zoom"],
        "tile_bytes_per_zoom_note": "gzip-compressed bytes in the PMTiles archive; served_tile_bytes_per_zoom are the raw .pbf files",
        "served_tile_bytes_per_zoom": served_bytes,
        "generalisation": {
            "method": ("All sources form one polygon coverage (boundaries noded together on a "
                       f"{GRID_DEG} deg grid, faces given to the highest-priority polygon). Per zoom z8-z12, in Web Mercator: units "
                       "smaller than merge_below_px2 pixels (512 px tiles) are merged into the neighbour with the longest shared "
                       "edge (the merged unit keeps the attributes of its largest member; no area is dropped), then "
                       "shapely.coverage_simplify (GEOS CoverageSimplifier, Visvalingam-Whyatt, shared edges simplified once so "
                       "neighbours stay edge-matched). z13 is unsimplified. Tiles clip the zoom's coverage with a buffer of "
                       f"{CLIP_BUFFER_UNITS}/4096 tile units and quantize to 4096; shared vertices quantize identically, so no "
                       "gaps open between neighbours."),
            **result["generalisation"],
            "coverage_build": result["coverage_stats"],
        },
        "coverage": {
            "file": COVERAGE.name,
            "gaps_file": GAPS.name,
            "gaps": gaps_stats,
            "note": ("Priority " + " > ".join(ORDER) + ": a face covered by several sources belongs to the first, so no area has two "
                     "sources. Areas outside the outlines in geology-coverage.geojson (listed as polygons in geology-gaps.geojson, "
                     "kind no_open_geology) have no open vector geology here (not 'no rock'). Scales: " + scales + ". The Veneto "
                     "1:250,000 lithology map, the ISPRA 1:100,000 map (surveys 1880-1980) and the GeoSphere 1:500,000 map are much "
                     "coarser than the provincial maps and must not be read at z11-13 as detailed mapping. At z8-z12 small units "
                     "are merged into neighbours, so an area may show its neighbour's unit until z13."),
        },
        "sources": sources,
        "rejected_sources": [
            {"id": "ispra-carg-50k-vector", "sheets": ["028 La Marmolada", "029 Cortina d'Ampezzo", "044 Predazzo", "045 S. Martino di Castrozza", "046 Longarone"],
             "reason": ("CARG-Gate (progetto-carg.isprambiente.it, downloads under CC-BY 4.0) lists banca_dati 'No' (028), 'In corso di "
                        "pubblicazione' (029, 046), 'In corso di realizzazione' (044) or nothing (045), with no download link, "
                        "checked 2026-09-12. No vector database to ship.")},
            {"id": "gap-fill candidates", "reason": "see research/geology/geology-gap-fill-sources.md (GeoSphere 1:50k/1:200k/1:1M, South Tyrol 1:300k overview and INSPIRE layer, ISPRA 1:500k, EGDI 1:1M, Lombardia 1:250k, FVG 1:150k, swisstopo 1:500k)."},
        ],
        "properties_schema": {
            "unit_name": ("unit name: NOME_IT_1 (South Tyrol), nome (Trentino), depositi_a (Veneto; lists the formations of a lithological class), "
                          "LITSTRAT or RUNC_LITSTRAT, else the lithology (swisstopo), GeologicUnit name (ISPRA; see the contradictions list: "
                          "some ISPRA names do not match their description), legend description (GeoSphere)"),
            "unit_code": "map symbol: SIGLA_1 (South Tyrol), sigla_cart (Trentino), uc_lege (Veneto legend class), SYMBOL (swisstopo), GeologicUnit gml:id e.g. GU_45 (ISPRA), inspireId localId (GeoSphere)",
            "age_min_ma": f"younger bound: end_ma of the younger ICS interval (chart {v}) of the unit's age; null if absent, unmapped or withheld by a rule",
            "age_max_ma": f"older bound: start_ma of the older ICS interval (chart {v}); null if absent, unmapped or withheld. age_min_ma <= age_max_ma",
            "age_label": ("the source's own age text, only when age_basis is 'source': 'MAX - MIN' ETA_CODICE_*_IT (South Tyrol, "
                          "reordered by chart age where swapped); the 'Eta:' statement of the unit in the PAT unit legend (Trentino); "
                          "the parenthesised age in depositi_a (Veneto); 'CHRONO_BASE - CHRONO_TOP' (swisstopo, German); "
                          "'olderNamedAge - youngerNamedAge' (ISPRA, GeoSphere). null for legend_join and class_rule ages"),
            "age_basis": ("how the age was obtained: 'source' = stated by the polygon's own map (its attributes or unit legend); "
                          "'legend_join' = the map names formations without a usable age, joined by formation name to another cited legend "
                          "(PAT unit legend, South Tyrol CARG attributes, the Veneto classes' own ages, ISPRA catalogue/sheet notes), "
                          "envelope of the formations' ages; 'class_rule' = deposit-type rule with a cited basis (Quaternary deposits); "
                          "null = no age (none given, unmappable, or withheld: metamorphic or other non-formation events, "
                          "contradictory attributes). Rows and evidence: geology_age_mapping.json"),
            "lithology": ("TEG_DESC_I unit type (South Tyrol); deposit type 'denom' for Quaternary units, null for bedrock (Trentino); materiali_ "
                          "(Veneto); LITHO_MAIN / RUNC_LITHO (swisstopo, German); INSPIRE lithology terms of the unit (ISPRA); "
                          "representativeLithology (GeoSphere)"),
            "color": f"ICS chart {v} colour of the younger interval of the unit's age (stage colour for a stage, series colour for a series, ...); null if there is no younger bound (never borrowed from the older bound)",
            "source": "dataset id of the polygon: " + ", ".join(ORDER),
        },
        "ages": {
            "ics_chart_version": v,
            "mapping_table": "data/scripts/terrain/geology_age_mapping.json",
            "authorities": mapping_json.get("authorities", {}),
            "honesty_note": ("Polygons and their stratigraphic attributions are the maps' (observed). Numeric ages and colours are the ICS "
                             "chart's boundary ages and colours for the intervals named, not ages measured or published by the maps. "
                             "Qualifiers (p.p., ?, inf./sup. on a stage, Trentino substages) are resolved to full chart intervals, so the "
                             "ranges are outer envelopes. age_basis says where each age comes from. 'source': Trentino ages come from the "
                             "Servizio Geologico's unit legend (joined by map symbol; members without their own statement take the age "
                             "of their formation), South Tyrol ages from the CARG attributes, Veneto ages from the age text of its "
                             "lithological classes, swisstopo ages from CHRONO_BASE (older) and CHRONO_TOP (younger), verified against "
                             "swisstopo's data model, ISPRA and GeoSphere ages from the INSPIRE GeologicEvent. 'legend_join': Veneto classes "
                             "that list formations without an age take the envelope of those formations' ages in another cited legend (and a "
                             "few Trentino units without a statement take the age of the same formation elsewhere); classes ending in "
                             "'et al.' are dated from the named formations only. 'class_rule': Veneto Quaternary deposit classes (moraine, "
                             "alluvial, fluvioglacial, lacustrine, eluvial-colluvial, scree, landslide) take the Quaternary as a whole, from "
                             "the PAT legend's grouping of the same deposit types as 'Depositi quaternari'. Withheld (uncoloured): ISPRA units "
                             "whose event is metamorphic (the age is then the metamorphism, e.g. orthogneiss 'Cenozoic') or faulting/unknown; "
                             "ISPRA units whose name, description and age contradict each other or whose age disagrees with the detailed maps "
                             "where both exist (unless the unit name, or for a generic name the one formation its description names, is "
                             "unambiguous in the South Tyrol/Trentino legends, then legend_join); GeoSphere units dated by a subduction event, glaciers and water; swisstopo open ranges "
                             "(Proterozoic-Cenozoic, whole Phanerozoic) and rows whose description contradicts the age fields. Water, "
                             "anthropic deposits, unmappable areas and open-ended ages ('pre-Permiano') stay uncoloured. Every join, rule "
                             "and ISPRA decision is recorded in the mapping table; the build recomputes each envelope from the evidence."),
            "ispra_review": ispra_review_summary(result, mapping_json),
        },
        "verification": {**verification, "served_tiles_check": checks},
        "preview": "data/processed/terrain/preview/" + PREVIEW.name,
    }
    tmp = META.with_name(META.name + ".tmp")
    tmp.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    replace_with_retry(tmp, META)
    print(f"wrote {META}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="rebuild even if the archive exists")
    ap.add_argument("--qa-only", action="store_true", help="re-run coverage/gaps files, verification, preview and meta on the existing archive")
    ap.add_argument("--reuse", choices=["coverage", "generalised"],
                    help="with --force: reuse the noded coverage (and the per-zoom coverages) from data/processed/terrain; properties are always recomputed")
    ap.add_argument("--workers", type=int, default=max(1, min(10, (os.cpu_count() or 2) - 2)))
    args = ap.parse_args()
    result_path = PROCESSED / "geology-dolomites-build-result.json"
    if args.qa_only or (OUT.exists() and not args.force):
        if not result_path.exists():
            sys.exit(f"{OUT.name} exists but {result_path.name} is missing; run with --force")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not args.qa_only:
            print(f"{OUT} exists; pass --force to rebuild or --qa-only to re-verify")
            return 0
        extents = {sid: shapely.from_wkb(w) for sid, w in load_pickle(EXTENTS_PKL).items() if w is not None}
        write_coverage(extents)
        result["gaps"] = write_gaps(extents)
    else:
        result = build(args.workers, args.reuse)
        extents = {sid: shapely.from_wkb(w) for sid, w in load_pickle(EXTENTS_PKL).items() if w is not None}
        result["gaps"] = write_gaps(extents)
        tmp = result_path.with_name(result_path.name + ".tmp")
        tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        replace_with_retry(tmp, result_path)
    verification = verify(result)
    make_preview()
    write_meta(result, verification, result.get("gaps"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
