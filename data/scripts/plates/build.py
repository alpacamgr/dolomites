"""Build per-age reconstructed geometry JSONs for the globe view.

For every integer age t in 0..300 Ma writes
``app/public/data/globe/plates/{t}.json`` matching data contract 1.2, plus
``index.json`` (contract 1.2), ``meta.json`` (the "Every dataset directory"
rule), and ``app/public/data/globe/dolomites-path.json`` (contract 1.3).

Single model for all ages (ADR 0005): Scotese and Wright 2018 / PALEOMAP
(gplately PlateModelManager name ``scotese_and_wright2018``), the frame in
which the PaleoDEM textures were built.

Each feature in the FeatureCollection has ``properties.kind`` in
``{continent, landmass, boundary, dolomites}``. ``landmass`` is one
MultiPolygon per age: the union of all continent polygons, the clean outer
outline the globe draws by default. No ``coastline`` features are emitted:
the model has no Coastlines layer and its COBs layer is byte-identical to
ContinentalPolygons. Boundaries carry ``type`` (subduction | ridge |
transform | other) and, for subductions, ``polarity`` (left | right |
unknown; the model carries no polarity property, so it is always unknown).
The model's topologies only cover 0-100 Ma (no topology feature exists
before 100 Ma), so files for 101-300 Ma carry no boundary features.

Every JSON is written to a ``.tmp`` file and renamed into place, because the
app may be reading these files while the build runs. The script skips
``{t}.json`` files that already exist unless ``FORCE_REBUILD=1``.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date
from pathlib import Path

import pygplates
import shapely
from shapely.geometry import (LineString, MultiLineString, MultiPolygon,
                              Polygon, box)
from shapely.ops import unary_union

from gplately import PlateModelManager

REPO = Path(__file__).resolve().parents[3]
RAW = REPO / "data" / "raw"
OUT_DIR = REPO / "app" / "public" / "data" / "globe" / "plates"
OUT_DOL = REPO / "app" / "public" / "data" / "globe" / "dolomites-path.json"

DATASET_ID = "scotese-wright-2018-model"
PMM_NAME = "scotese_and_wright2018"
MODEL_LABEL = "scotese_and_wright2018 (PALEOMAP frame)"

MAX_AGE = 300

DOLOMITES_LAT = 46.5
DOLOMITES_LON = 11.8
PALEOLAT_TABLE_AGES = (0, 50, 100, 150, 200, 240, 250, 300)

# Simplification tolerances (deg). Contract 1.2 names 0.25 deg; polygons use
# 0.4 deg to fit the 200 kB per-file budget, boundary lines 0.1 deg. Polygons
# under 2 deg^2 after wrapping are dropped (tiny islands and fragments).
TOL_CONTINENT = 0.4
TOL_BOUNDARY = 0.1
TOL_LANDMASS = 0.1
MIN_HOLE_AREA_LANDMASS = 0.5   # deg^2; smaller interior holes are filled
CLOSE_DEG_LANDMASS = 0.5       # closing distance; fills block gaps < ~1 deg
WORLD_BOX = box(-180, -90, 180, 90)
MIN_AREA_CONTINENT = 2.0
MIN_POLY_AREA_DEG2 = 0.05      # baseline used in generic wrap helper
COORD_DECIMALS = 3

# GPML feature type name -> contract 1.2 boundary type. Anything else: other.
BOUNDARY_TYPES = {
    "SubductionZone": "subduction",
    "MidOceanRidge": "ridge",
    "Transform": "transform",
    "FractureZone": "transform",
}


def load_model():
    pm = PlateModelManager()
    return pm.get_model(PMM_NAME, data_dir=str(RAW / DATASET_ID))


def atomic_write(path: Path, text: str):
    """Write to a temp file then rename; retry while a reader holds the file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    for _ in range(40):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            time.sleep(0.25)
    tmp.replace(path)


def round_coord(x: float) -> float:
    return round(float(x), COORD_DECIMALS)


def _coords(seq):
    # Deduplicate consecutive identical vertices after rounding.
    out = []
    for lon, lat in seq:
        p = [round_coord(lon), round_coord(lat)]
        if not out or out[-1] != p:
            out.append(p)
    return out


def wrap_polygon(polygon_on_sphere):
    """pygplates PolygonOnSphere -> list of shapely Polygon(s) in lon/lat.

    Splits at the antimeridian and drops rings smaller than
    MIN_POLY_AREA_DEG2 (in degrees^2).
    """
    wrapper = pygplates.DateLineWrapper()
    wrapped = wrapper.wrap(polygon_on_sphere)
    out = []
    for w in wrapped:
        pts = [(p.get_longitude(), p.get_latitude()) for p in w.get_exterior_points()]
        if len(pts) < 3:
            continue
        try:
            poly = Polygon(pts)
        except Exception:
            continue
        if not poly.is_valid:
            poly = poly.buffer(0)
            if poly.is_empty:
                continue
            if isinstance(poly, MultiPolygon):
                for p in poly.geoms:
                    if p.area >= MIN_POLY_AREA_DEG2:
                        out.append(p)
                continue
        if poly.area < MIN_POLY_AREA_DEG2:
            continue
        out.append(poly)
    return out


def wrap_polyline(polyline_on_sphere):
    """pygplates PolylineOnSphere -> list of shapely LineString(s)."""
    wrapper = pygplates.DateLineWrapper()
    wrapped = wrapper.wrap(polyline_on_sphere)
    out = []
    for w in wrapped:
        pts = [(p.get_longitude(), p.get_latitude()) for p in w.get_points()]
        if len(pts) < 2:
            continue
        out.append(LineString(pts))
    return out


def simplify_and_emit_polygon(poly: Polygon, tol: float,
                              min_area: float = MIN_POLY_AREA_DEG2):
    simp = poly.simplify(tol, preserve_topology=True)
    if simp.is_empty:
        return None
    if isinstance(simp, MultiPolygon):
        rings = []
        for g in simp.geoms:
            if g.area < min_area:
                continue
            c = polygon_to_coords(g)
            if c is not None:
                rings.append(c)
        if not rings:
            return None
        return {"type": "MultiPolygon", "coordinates": rings}
    if isinstance(simp, Polygon):
        if simp.area < min_area:
            return None
        c = polygon_to_coords(simp)
        if c is None:
            return None
        return {"type": "Polygon", "coordinates": c}
    return None


def polygon_to_coords(poly: Polygon):
    ext = _coords(poly.exterior.coords)
    if len(ext) < 4:
        return None
    rings = [ext]
    for interior in poly.interiors:
        ring = _coords(interior.coords)
        if len(ring) >= 4:
            rings.append(ring)
    return rings


def emit_line(line: LineString, tol: float):
    simp = line.simplify(tol, preserve_topology=False)
    if simp.is_empty:
        return None
    if isinstance(simp, LineString):
        coords = _coords(simp.coords)
        if len(coords) < 2:
            return None
        return {"type": "LineString", "coordinates": coords}
    if isinstance(simp, MultiLineString):
        parts = []
        for g in simp.geoms:
            coords = _coords(g.coords)
            if len(coords) >= 2:
                parts.append(coords)
        if not parts:
            return None
        return {"type": "MultiLineString", "coordinates": parts}
    return None


def _dissolve_by_plate(polys_by_plate):
    """Union many small polygons per plate id into one MultiPolygon."""
    out = {}
    for pid, polys in polys_by_plate.items():
        if not polys:
            continue
        try:
            merged = unary_union(polys)
        except Exception:
            merged = MultiPolygon([p for p in polys if p.is_valid])
        if merged.is_empty:
            continue
        if isinstance(merged, Polygon):
            merged = MultiPolygon([merged])
        elif not isinstance(merged, MultiPolygon):
            continue
        out[pid] = merged
    return out


def continent_features(rot_model, continents, age: int):
    """Reconstruct continental polygons to `age` and return GeoJSON features."""
    tmp = []
    pygplates.reconstruct(continents, rot_model, tmp, float(age))
    by_plate = {}
    names = {}
    for rfg in tmp:
        f = rfg.get_feature()
        geom = rfg.get_reconstructed_geometry()
        if not isinstance(geom, pygplates.PolygonOnSphere):
            continue
        pid = f.get_reconstruction_plate_id()
        for p in wrap_polygon(geom):
            if p.area < MIN_AREA_CONTINENT:
                continue
            by_plate.setdefault(pid, []).append(p)
        if f.get_name() and pid not in names:
            names[pid] = f.get_name()

    features = []
    for pid, merged in _dissolve_by_plate(by_plate).items():
        g = simplify_and_emit_polygon(merged, TOL_CONTINENT,
                                      MIN_AREA_CONTINENT)
        if g is None:
            continue
        props = {"kind": "continent", "plate_id": pid}
        if pid in names:
            props["name"] = names[pid]
        features.append({"type": "Feature", "properties": props,
                         "geometry": g})
    return features


def landmass_feature(rot_model, continents, age: int):
    """Union of all reconstructed continent polygons as one MultiPolygon.

    Pieces are unioned after the antimeridian split (pieces on either side of
    lon 180 never overlap). The union is closed (buffer out and back in by
    CLOSE_DEG_LANDMASS) to fill the thin gaps the model leaves between
    blocks, holes under MIN_HOLE_AREA_LANDMASS are filled, and the result is
    simplified and snapped to the output coordinate grid so it stays valid
    after rounding. Parts under MIN_AREA_CONTINENT are dropped unless they
    touch lon +-180, so both sides of an antimeridian cut survive.
    """
    tmp = []
    pygplates.reconstruct(continents, rot_model, tmp, float(age))
    pieces = []
    for rfg in tmp:
        geom = rfg.get_reconstructed_geometry()
        if isinstance(geom, pygplates.PolygonOnSphere):
            pieces.extend(wrap_polygon(geom))
    if not pieces:
        return None
    merged = (unary_union(pieces)
              .buffer(CLOSE_DEG_LANDMASS, join_style=2)
              .buffer(-CLOSE_DEG_LANDMASS, join_style=2)
              .intersection(WORLD_BOX))
    parts = []
    for geom in getattr(merged, "geoms", [merged]):
        if isinstance(geom, Polygon):
            parts.append(geom)
        elif isinstance(geom, MultiPolygon):
            parts.extend(geom.geoms)
    cleaned = [Polygon(p.exterior,
                       [r for r in p.interiors
                        if Polygon(r).area >= MIN_HOLE_AREA_LANDMASS])
               for p in parts]
    cleaned = [p for p in cleaned
               if p.area >= MIN_AREA_CONTINENT
               or p.bounds[0] <= -179.999 or p.bounds[2] >= 179.999]
    if not cleaned:
        return None
    simp = MultiPolygon(cleaned).simplify(TOL_LANDMASS, preserve_topology=True)
    snapped = shapely.set_precision(simp, 10 ** -COORD_DECIMALS)
    coords = []
    for poly in getattr(snapped, "geoms", [snapped]):
        if isinstance(poly, Polygon) and poly.area >= MIN_POLY_AREA_DEG2:
            c = polygon_to_coords(poly)
            if c is not None:
                coords.append(c)
    if not coords:
        return None
    return {"type": "Feature", "properties": {"kind": "landmass"},
            "geometry": {"type": "MultiPolygon", "coordinates": coords}}


def boundary_features(rot_model, topologies, age: int):
    """Shared sub-segments of the model's topologies resolved at `age`."""
    resolved, sections = [], []
    pygplates.resolve_topologies(topologies, rot_model, resolved, float(age),
                                 sections)
    features = []
    for sec in sections:
        f = sec.get_feature()
        btype = BOUNDARY_TYPES.get(f.get_feature_type().get_name(), "other")
        props = {"kind": "boundary", "type": btype}
        if btype == "subduction":
            pol = str(f.get_enumeration(
                pygplates.PropertyName.gpml_subduction_polarity,
                "Unknown")).lower()
            props["polarity"] = pol if pol in ("left", "right") else "unknown"
        for sub in sec.get_shared_sub_segments():
            for ln in wrap_polyline(sub.get_resolved_geometry()):
                g = emit_line(ln, TOL_BOUNDARY)
                if g is None:
                    continue
                features.append({"type": "Feature", "properties": dict(props),
                                 "geometry": g})
    return features


def reconstruct_point(rot_model, lat, lon, plate_id, age):
    """Return (lat, lon) of a present-day point on `plate_id` at `age`."""
    if age == 0:
        return lat, lon
    pt = pygplates.PointOnSphere(lat, lon)
    finite = rot_model.get_rotation(float(age), int(plate_id), 0)
    return (finite * pt).to_lat_lon()


def assign_plate_id(static_polys, rot_model, lat, lon) -> int:
    partition = pygplates.PlatePartitioner(static_polys, rot_model)
    rfg = partition.partition_point(pygplates.PointOnSphere(lat, lon))
    if rfg is None:
        return 0
    return rfg.get_feature().get_reconstruction_plate_id()


def build_age(age: int, ctx, force: bool):
    out_path = OUT_DIR / f"{age}.json"
    if out_path.exists() and not force:
        return out_path.stat().st_size

    rot = ctx["rot"]
    feats = []
    feats.extend(continent_features(rot, ctx["continents"], age))
    landmass = landmass_feature(rot, ctx["continents"], age)
    if landmass is not None:
        feats.append(landmass)
    feats.extend(boundary_features(rot, ctx["topologies"], age))

    lat, lon = reconstruct_point(rot, DOLOMITES_LAT, DOLOMITES_LON,
                                 ctx["dolomites_plate_id"], age)
    feats.append({
        "type": "Feature",
        "properties": {
            "kind": "dolomites",
            "lat": DOLOMITES_LAT,
            "lon": DOLOMITES_LON,
            "paleolat": round(float(lat), 3),
        },
        "geometry": {"type": "Point",
                     "coordinates": [round(float(lon), 3),
                                     round(float(lat), 3)]},
    })

    payload = {
        "type": "FeatureCollection",
        "properties": {
            "age_ma": age,
            "model": PMM_NAME,
            "reference_point": {"lat": DOLOMITES_LAT, "lon": DOLOMITES_LON},
        },
        "features": feats,
    }
    atomic_write(out_path, json.dumps(payload, separators=(",", ":")))
    return out_path.stat().st_size


def build_dolomites_path(ctx):
    samples = []
    for age in range(0, MAX_AGE + 1):
        lat, lon = reconstruct_point(ctx["rot"], DOLOMITES_LAT, DOLOMITES_LON,
                                     ctx["dolomites_plate_id"], age)
        samples.append({"ma": age,
                        "lat": round(float(lat), 3),
                        "lon": round(float(lon), 3)})
    payload = {
        "reference_point": {"lat": DOLOMITES_LAT, "lon": DOLOMITES_LON},
        "plate_id": ctx["dolomites_plate_id"],
        "model": MODEL_LABEL,
        "samples": samples,
    }
    atomic_write(OUT_DOL, json.dumps(payload, separators=(",", ":")))
    return samples


def write_index_and_meta(plate_id: int):
    ages = list(range(0, MAX_AGE + 1))
    index = {
        "ages_ma": ages,
        "path_pattern": "globe/plates/{age}.json",
        "model": MODEL_LABEL,
        "simplify_deg": TOL_CONTINENT,
    }
    atomic_write(OUT_DIR / "index.json",
                 json.dumps(index, separators=(",", ":")))

    meta = {
        "dataset_id": DATASET_ID,
        "label": "modeled",
        "source_ref": "scotese-2018",
        "attribution": (
            "Plate reconstruction: PALEOMAP plate model (C. R. Scotese), as "
            "used for Scotese and Wright (2018), PALEOMAP Paleodigital "
            "Elevation Models (PaleoDEMS) for the Phanerozoic, Zenodo, "
            "doi:10.5281/zenodo.5460860, CC BY 4.0. Model files via the "
            "GPlates PlateModelManager (scotese_and_wright2018)."
        ),
        "citation": [
            "Scotese, C. R. and Wright, N. M. (2018). PALEOMAP Paleodigital "
            "Elevation Models (PaleoDEMS) for the Phanerozoic. Zenodo. "
            "doi:10.5281/zenodo.5460860.",
            "Scotese, C. R. PALEOMAP Plate Model m15g60_v2d3 (rotation file "
            "Scotese_Wright_PlateModel.rot, header dated 2016-02-01), "
            "distributed as 'scotese_and_wright2018' by the GPlates "
            "PlateModelManager (https://repo.gplates.org/webdav/pmm/"
            "config/models_v2.json).",
        ],
        "license": "CC BY 4.0",
        "generated": date.today().isoformat(),
        "script": "data/scripts/plates/build.py",
        "caveats": [
            "Single model for 0-300 Ma: Scotese and Wright 2018 / PALEOMAP. "
            "There is no model switch and no jump in the time series.",
            "The reference frame is the PALEOMAP frame, identical to the "
            "frame of the PaleoDEM textures (scotese-paleodem-2018-v2), so "
            "outlines and raster agree by construction. Checked visually "
            "against the 2k textures at 20, 100 and 240 Ma.",
            "Paleolatitude is model-dependent. For the Dolomites reference "
            "point at 240 Ma this model gives 7.3 N; Muller et al. 2019 gives "
            "1.4 N, Muller et al. 2022 8.6 N and Merdith et al. 2021 11.8 N "
            "(ADR 0005). Paleomagnetic measurements on Dolomites rocks give "
            "about 16-18 N (Muttoni et al. 1997, pending first-hand "
            "verification).",
            f"The Dolomites reference point (46.5 N, 11.8 E) is assigned to "
            f"plate id {plate_id} by partitioning against the model's static "
            f"polygons at 0 Ma (rotation file label 'ITL-AFR') and rides "
            f"passively with that plate. No global model resolves the "
            f"Dolomites as an independent block.",
            "No coastline features: the model has no Coastlines layer and its "
            "COBs and StaticPolygons layers are the same file as "
            "ContinentalPolygons. The continent outlines follow the painted "
            "land and shelf edges of the PaleoDEM texture.",
            "Boundaries are the shared sub-segments of the model's topologies "
            "resolved at each age. 'type' comes from the GPML feature type: "
            "SubductionZone -> subduction, MidOceanRidge -> ridge, Transform "
            "and FractureZone -> transform, everything else (ContinentalRift, "
            "Suture, InferredPaleoBoundary, unclassified) -> other. The model "
            "carries no subduction polarity, so polarity is always 'unknown'. "
            "The model's topologies only cover 0-100 Ma (no topology feature "
            "exists before 100 Ma), so ages 101-300 Ma have no boundary "
            "features. Boundaries are much less detailed than Muller et al. "
            "2019, especially in the Alpine sector.",
            "Landmass is one MultiPolygon per age: the union of all "
            "reconstructed continental polygons (shapely unary_union after "
            "the antimeridian split), closed by 0.5 deg (buffer out and back "
            "in, which fills gaps between blocks narrower than about 1 deg), "
            "interior holes under 0.5 deg^2 filled, simplified at 0.1 deg and "
            "snapped to a 0.001 deg grid so it stays valid after rounding; "
            "parts under 2 deg^2 are dropped unless they touch lon +-180. The "
            "model's blocks do not tile, so wider gaps between them remain as "
            "interior loops or notches (for example inside Pangea at 240 Ma "
            "and in Tibet at 20 Ma), sometimes where the PaleoDEM paints land. "
            "Rings contain cut edges along lon +-180 (land crossing the "
            "antimeridian) and lat +-90 (land covering a pole); these are not "
            "coastline.",
            "Continent polygons are dissolved per plate id, simplified to 0.4 "
            "deg tolerance, and dropped below 2 deg^2; boundary lines are "
            "simplified to 0.1 deg. Antimeridian split with "
            "pygplates.DateLineWrapper; coordinates rounded to 3 decimals.",
        ],
    }
    atomic_write(OUT_DIR / "meta.json", json.dumps(meta, indent=2))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    force = os.environ.get("FORCE_REBUILD") == "1"

    model = load_model()
    rot = pygplates.RotationModel(model.get_rotation_model())

    def load(layer):
        return [pygplates.FeatureCollection(f) for f in model.get_layer(layer)]

    static = load("StaticPolygons")
    plate_id = int(assign_plate_id(static, rot, DOLOMITES_LAT, DOLOMITES_LON))
    print(f"Dolomites plate id ({PMM_NAME} static polygons): {plate_id}")

    ctx = {
        "rot": rot,
        "continents": load("ContinentalPolygons"),
        "topologies": load("Topologies"),
        "dolomites_plate_id": plate_id,
    }

    sizes = []
    t0 = time.time()
    for age in range(0, MAX_AGE + 1):
        size = build_age(age, ctx, force)
        sizes.append(size)
        if age % 10 == 0 or age == MAX_AGE:
            print(f"[age={age:>3d} Ma] size={size/1024:6.1f} KB  "
                  f"elapsed={time.time() - t0:7.1f} s", flush=True)

    write_index_and_meta(plate_id)
    samples = build_dolomites_path(ctx)

    print(f"\nWrote {MAX_AGE + 1} per-age files.")
    print(f"file size KB: min={min(sizes)/1024:.1f}  "
          f"max={max(sizes)/1024:.1f}  "
          f"mean={sum(sizes)/len(sizes)/1024:.1f}")
    print("index.json, meta.json, dolomites-path.json written.")
    print("\nDolomites paleoposition (PALEOMAP):")
    print("   Ma     lat     lon")
    for age in PALEOLAT_TABLE_AGES:
        s = samples[age]
        print(f"  {age:>3d}  {s['lat']:6.2f}  {s['lon']:6.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
