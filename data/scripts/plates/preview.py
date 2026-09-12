"""Render matplotlib preview PNGs for a handful of ages.

Reads the JSON files under ``app/public/data/globe/plates/`` and produces
Mollweide-projection PNGs into ``data/processed/plates/preview/``, plus
frame-check overlays ``overlay_{age}.png``: landmass outline (thick magenta),
continent block edges (faint red) and the Dolomites marker drawn on the
matching 2k PaleoDEM texture (equirectangular,
lon -180..180, lat 90..-90). Purely diagnostic - the app never reads these.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Polygon as MplPolygon
from PIL import Image

REPO = Path(__file__).resolve().parents[3]
IN_DIR = REPO / "app" / "public" / "data" / "globe" / "plates"
OUT_DIR = REPO / "data" / "processed" / "plates" / "preview"
TEXTURE_DIR = REPO / "app" / "public" / "data" / "globe" / "textures" / "2k"

AGES = [0, 50, 100, 150, 200, 240, 280, 300]
OVERLAY_AGES = [240, 100, 20]

# Mollweide projection: forward map (lon in radians, lat in radians) -> (x, y)
def mollweide(lon_deg, lat_deg):
    lam = math.radians(lon_deg)
    phi = math.radians(max(min(lat_deg, 89.999), -89.999))
    if abs(lat_deg) >= 89.999:
        theta = math.copysign(math.pi / 2, lat_deg)
    else:
        theta = phi
        for _ in range(8):
            denom = 2 + 2 * math.cos(2 * theta)
            if denom == 0:
                break
            theta -= (2 * theta + math.sin(2 * theta)
                      - math.pi * math.sin(phi)) / denom
    x = 2 * math.sqrt(2) / math.pi * lam * math.cos(theta)
    y = math.sqrt(2) * math.sin(theta)
    return x, y


def project_ring(ring):
    return [mollweide(lo, la) for lo, la in ring]


def draw_age(age: int):
    src = IN_DIR / f"{age}.json"
    if not src.exists():
        print(f"skip {age}: {src} not found")
        return
    data = json.loads(src.read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=140)
    ax.set_aspect("equal")
    ax.axis("off")
    # graticule
    for lo in range(-180, 181, 30):
        pts = [mollweide(lo, la) for la in range(-90, 91, 2)]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color="#dddddd", lw=0.3)
    for la in range(-90, 91, 30):
        pts = [mollweide(lo, la) for lo in range(-180, 181, 2)]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color="#dddddd", lw=0.3)

    continent_patches = []
    coastline_patches = []
    ridges, transforms, subductions, others = [], [], [], []
    dolomites = None

    for feat in data["features"]:
        kind = feat["properties"].get("kind")
        geom = feat["geometry"]
        gt = geom["type"]
        if kind == "continent":
            rings = geom["coordinates"]
            polys = [rings] if gt == "Polygon" else rings
            for p in polys:
                if not p:
                    continue
                pts = project_ring(p[0])
                continent_patches.append(MplPolygon(pts, closed=True))
        elif kind == "coastline":
            if gt in ("Polygon", "MultiPolygon"):
                polys = [geom["coordinates"]] if gt == "Polygon" else geom["coordinates"]
                for p in polys:
                    if not p:
                        continue
                    pts = project_ring(p[0])
                    coastline_patches.append(MplPolygon(pts, closed=True))
            elif gt == "LineString":
                pts = project_ring(geom["coordinates"])
                ridges.append(pts)  # treat as thin outline
            elif gt == "MultiLineString":
                for ln in geom["coordinates"]:
                    ridges.append(project_ring(ln))
        elif kind == "boundary":
            btype = feat["properties"].get("type")
            lines = ([geom["coordinates"]]
                     if gt == "LineString" else geom["coordinates"])
            for ln in lines:
                pts = project_ring(ln)
                if btype == "ridge":
                    ridges.append(pts)
                elif btype == "transform":
                    transforms.append(pts)
                elif btype == "subduction":
                    subductions.append(pts)
                else:
                    others.append(pts)
        elif kind == "dolomites":
            # geometry.coordinates carries the reconstructed [lon, lat];
            # properties.lat/lon are the present-day reference point.
            lon_p, lat_p = geom["coordinates"]
            dolomites = (lon_p, lat_p,
                         feat["properties"].get("paleolat"))

    ax.add_collection(PatchCollection(continent_patches,
                                       facecolor="#d4c39b",
                                       edgecolor="#7f6b3f",
                                       lw=0.2, alpha=0.9))
    ax.add_collection(PatchCollection(coastline_patches,
                                       facecolor="none",
                                       edgecolor="#3d2f11",
                                       lw=0.35))
    if ridges:
        ax.add_collection(LineCollection(ridges, colors="#d63a3a", lw=0.6))
    if transforms:
        ax.add_collection(LineCollection(transforms, colors="#2f9c4a", lw=0.5))
    if subductions:
        ax.add_collection(LineCollection(subductions, colors="#1f4faa", lw=0.7))
    if others:
        ax.add_collection(LineCollection(others, colors="#888888", lw=0.4))

    if dolomites is not None:
        lon, lat, paleolat = dolomites
        x, y = mollweide(lon, lat)
        ax.plot(x, y, marker="o", color="#e63946", markersize=6,
                markeredgecolor="white", markeredgewidth=1.0, zorder=5)
        ax.annotate(f"Dolomites  ({paleolat:.1f} lat)", (x, y),
                    xytext=(10, 6), textcoords="offset points",
                    color="#e63946", fontsize=8)

    ax.set_title(f"{age} Ma  (Scotese and Wright 2018 / PALEOMAP)",
                 fontsize=11)

    ax.set_xlim(-3.2, 3.2)
    ax.set_ylim(-1.55, 1.55)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f"{age:03d}Ma.png"
    fig.savefig(dst, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print(f"[{age:>3d} Ma] wrote {dst.name}")


def open_texture(path: Path):
    # The texture pipeline may be rewriting the file; retry briefly.
    for attempt in range(20):
        try:
            with Image.open(path) as im:
                return im.convert("RGB")
        except (OSError, ValueError):
            time.sleep(0.5)
    with Image.open(path) as im:
        return im.convert("RGB")


def draw_overlay(age: int):
    """Landmass + faint continent edges + Dolomites marker on the 2k texture."""
    src = IN_DIR / f"{age}.json"
    tex = TEXTURE_DIR / f"{age}.webp"
    if not src.exists() or not tex.exists():
        print(f"skip overlay {age}: missing {src.name} or {tex.name}")
        return
    data = json.loads(src.read_text(encoding="utf-8"))
    img = open_texture(tex)
    fig, ax = plt.subplots(figsize=(20.48, 10.24), dpi=100)
    ax.imshow(img, extent=(-180, 180, -90, 90), interpolation="nearest")
    outlines, landmass = [], []
    for feat in data["features"]:
        props, geom = feat["properties"], feat["geometry"]
        if props.get("kind") in ("continent", "landmass"):
            polys = ([geom["coordinates"]] if geom["type"] == "Polygon"
                     else geom["coordinates"])
            target = outlines if props["kind"] == "continent" else landmass
            for p in polys:
                target.extend(p)
        elif props.get("kind") == "dolomites":
            lon, lat = geom["coordinates"]
            ax.plot(lon, lat, marker="o", color="#ffd400", markersize=9,
                    markeredgecolor="black", markeredgewidth=1.2, zorder=5)
            ax.annotate(f"Dolomites {props['paleolat']:.1f} lat", (lon, lat),
                        xytext=(8, 6), textcoords="offset points",
                        color="#ffd400", fontsize=11, weight="bold")
    ax.add_collection(LineCollection(outlines, colors="#ff2a2a", lw=0.4,
                                     alpha=0.35))
    ax.add_collection(LineCollection(landmass, colors="#ff00ff", lw=2.0))
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xticks(range(-180, 181, 30))
    ax.set_yticks(range(-90, 91, 30))
    ax.grid(color="white", lw=0.3, alpha=0.4)
    ax.set_title(f"{age} Ma  landmass (magenta), continent blocks (faint red) "
                 f"on PaleoDEM texture "
                 f"2k/{age}.webp  (Scotese and Wright 2018 / PALEOMAP)")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f"overlay_{age}.png"
    fig.savefig(dst, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print(f"[{age:>3d} Ma] wrote {dst.name}")


def main() -> int:
    for age in AGES:
        draw_age(age)
    for age in OVERLAY_AGES:
        draw_overlay(age)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
