"""Render globe textures from PaleoDEM and ETOPO 2022.

For each age in {0, 5, ..., 300} Ma, writes to app/public/data/globe/textures/:
  - 4k/<age>.webp        equirectangular RGB, 4096x2048
  - 2k/<age>.webp        equirectangular RGB, 2048x1024
  - 4k/<age>-normal.webp tangent-space normal map, 4096x2048

Also writes index.json and meta.json.

Sources:
  0 Ma      : NOAA ETOPO 2022 60 arc-sec ice-surface (observed)
  5..300 Ma : Scotese & Wright 2018 PaleoDEM 0.1 deg (interpreted)

Both are rendered with the same hypsometric palette and hillshade so the
crossfade to today is seamless.

Idempotent: skips outputs that already exist. Use --force to redo.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import (
    build_lut,
    apply_palette,
    palette_stops_for_index_json,
    OCEAN_STOPS,
    LAND_STOPS,
    SEA_LEVEL_M,
)

ROOT = Path(__file__).resolve().parents[3]
PALEO_DIR = ROOT / "data" / "raw" / "scotese-paleodem-2018-v2" / "nc"
ETOPO_DIR = ROOT / "data" / "raw" / "noaa-etopo2022-60s"
ETOPO_NC = ETOPO_DIR / "ETOPO_2022_v1_60s_N90W180_surface.nc"
ETOPO_BED_NC = ETOPO_DIR / "ETOPO_2022_v1_60s_N90W180_bed.nc"
OUT_DIR = ROOT / "app" / "public" / "data" / "globe" / "textures"
PROC_DIR = ROOT / "data" / "processed" / "textures"

# Ice mask thresholds (0 Ma only; PaleoDEM has no ice information).
# Cells where (surface - bedrock) exceeds this thickness are treated as ice
# sheets / ice caps and rendered with a dedicated pale blue-white tint. At
# 60 arc-second resolution 50 m safely captures the Greenland and Antarctic
# ice sheets (including ice shelves) while excluding stray snow and noise.
ICE_THICKNESS_THRESHOLD_M = 50.0

AGES = list(range(0, 305, 5))  # 0..300 in 5 Ma steps => 61 slices
SIZE_4K = (4096, 2048)
SIZE_2K = (2048, 1024)
WEBP_QUALITY = 85

# Hillshade parameters. Azimuth 315, altitude 45 (classic NW illumination).
HS_AZIMUTH_DEG = 315.0
HS_ALTITUDE_DEG = 45.0
# z_factor converts metres to pixel-width units; tuned so relief reads on the
# globe overview without looking harsh. At 4k a pixel at equator is ~9.8 km;
# z_factor here corresponds to ~6x vertical exaggeration.
HS_Z_FACTOR = 6.0 / (40_075_000.0 / SIZE_4K[0])  # ~ 6.14e-4 per metre
# Strength of the multiply-blend of hillshade onto the palette (0..1).
HS_STRENGTH = 0.6
# Polar handling. The east-west pixel spacing shrinks with cos(lat), so dz/dx
# divided by cos(lat) explodes near the poles and every column converging on
# the pole becomes a streak (a radial fan on the globe). Two guards, shared by
# the hillshade and the normal map:
#  - cos(lat) used for east-west spacing is clamped at cos(85 deg);
#  - between |lat| 80 deg and the pole the hillshade is blended linearly toward
#    its flat-ground value cos(zenith), and the normal-map relief toward the
#    flat normal (0, 0, 1), so polar pixels keep flat-terrain brightness (no
#    bright halo) without the streaks.
# Neither changes anything equatorward of 80 deg.
HS_COS_LAT_MIN_DEG = 85.0
HS_COS_LAT_MIN = math.cos(math.radians(HS_COS_LAT_MIN_DEG))  # ~0.0872
POLAR_TAPER_START_DEG = 80.0
# Hillshade of flat ground (slope 0): cos(zenith) = sin(altitude), ~0.7071.
HS_FLAT = math.cos(math.radians(90.0 - HS_ALTITUDE_DEG))

# Normal-map height scale: 1 pixel-width unit = NORMAL_HEIGHT_SCALE_M metres.
# A larger value flattens the normal map (subtler globe lighting).
NORMAL_HEIGHT_SCALE_M = 12_000.0


def find_paleo_file(age: int) -> Path | None:
    """Return the PaleoDEM file matching this age (Ma), or None if missing.
    Ignore macOS AppleDouble metadata files that start with '._'."""
    def real(p: Path) -> bool:
        return not p.name.startswith("._")
    for p in sorted(filter(real, PALEO_DIR.glob(f"*_{age}Ma.nc"))):
        return p
    for p in sorted(filter(real, PALEO_DIR.glob(f"*{age}Ma.nc"))):
        return p
    return None


def load_paleo(age: int) -> np.ndarray:
    """Load a PaleoDEM slice as elevation array shaped (H, W) with lat[0]=90N,
    lat[-1]=90S, lon[0]=-180, lon[-1]=180. The source is already in this
    convention (verified in inspect_nc.py); we strip the duplicated 180 column
    and southern edge so H, W = 1800, 3600."""
    p = find_paleo_file(age)
    if p is None:
        raise FileNotFoundError(f"no PaleoDEM file for age {age} Ma in {PALEO_DIR}")
    with xr.open_dataset(p, engine="netcdf4") as ds:
        z = ds["z"].values.astype(np.float32)  # (1801, 3601)
        lat = ds["latitude"].values
        lon = ds["longitude"].values
    # north-first?
    if lat[0] < lat[-1]:
        z = z[::-1, :]
    # -180..180 already; drop the duplicated final column to give 3600
    if abs(lon[0] + 180) < 1e-3 and abs(lon[-1] - 180) < 1e-3 and z.shape[1] == 3601:
        z = z[:, :-1]
    if z.shape[0] == 1801:
        # drop the north pole ROW so we align with a cell-centered 1800-row grid
        z = z[:-1, :]
    return z  # (1800, 3600) north-up, -180..180


def load_etopo() -> np.ndarray:
    """Load ETOPO 2022 60s ice-surface as (10800, 21600) north-up, -180..180."""
    with xr.open_dataset(ETOPO_NC, engine="netcdf4") as ds:
        z = ds["z"].values.astype(np.float32)  # (10800, 21600)
        lat = ds["lat"].values
    if lat[0] < lat[-1]:
        z = z[::-1, :]
    return z


def load_etopo_bed() -> np.ndarray:
    """Load ETOPO 2022 60s bedrock as (10800, 21600) north-up, -180..180."""
    with xr.open_dataset(ETOPO_BED_NC, engine="netcdf4") as ds:
        z = ds["z"].values.astype(np.float32)
        lat = ds["lat"].values
    if lat[0] < lat[-1]:
        z = z[::-1, :]
    return z


# ---------------------------------------------------------------------------
# Ice mask + ice tint (0 Ma only)
# ---------------------------------------------------------------------------

# Pale blue-white gradient by ice-surface elevation. Ice shelves near sea level
# render as the low stop; the interiors of Greenland (~3000 m) and Antarctica
# (~4000 m) render as the high stop. Linearly interpolated in [ICE_E_MIN, ICE_E_MAX].
ICE_STOPS: list[tuple[float, str]] = [
    (   0.0, "#dfe9f1"),  # ice shelf / low margin
    (1500.0, "#e7eef4"),
    (3000.0, "#f0f5f9"),
    (4500.0, "#f7fafc"),  # interior high plateau (Antarctic dome)
]
ICE_E_MIN = ICE_STOPS[0][0]
ICE_E_MAX = ICE_STOPS[-1][0]


def _hex2rgb(s: str) -> tuple[float, float, float]:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def build_ice_lut(n: int = 4096) -> np.ndarray:
    xs = np.array([s[0] for s in ICE_STOPS], dtype=np.float64)
    cs = np.array([_hex2rgb(s[1]) for s in ICE_STOPS], dtype=np.float64)
    e_axis = np.linspace(ICE_E_MIN, ICE_E_MAX, n)
    out = np.empty((n, 3), dtype=np.float64)
    for k in range(3):
        out[:, k] = np.interp(e_axis, xs, cs[:, k])
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def apply_ice_tint(surface_m: np.ndarray, ice_lut: np.ndarray | None = None) -> np.ndarray:
    """Map an ice-surface elevation array to an (H, W, 3) uint8 RGB image
    using the pale blue-white ice gradient. Values are clamped to the LUT."""
    if ice_lut is None:
        ice_lut = build_ice_lut()
    n = ice_lut.shape[0]
    e = np.where(np.isfinite(surface_m), surface_m, ICE_E_MIN)
    idx = (e - ICE_E_MIN) / (ICE_E_MAX - ICE_E_MIN) * (n - 1)
    idx = np.clip(np.round(idx), 0, n - 1).astype(np.int32)
    return ice_lut[idx]


def cos_lat_weights(H: int) -> np.ndarray:
    """cos(lat) weights for a cell-centered equirectangular grid with H rows,
    north-first. Used to weight per-cell fractions by true surface area."""
    lat_edges = np.linspace(np.pi / 2, -np.pi / 2, H + 1)
    # area of a latitude band on the sphere is proportional to (sin(lat_top) - sin(lat_bot)).
    return np.sin(lat_edges[:-1]) - np.sin(lat_edges[1:])


def resample(z: np.ndarray, size_wh: tuple[int, int], mode: str = "cubic") -> np.ndarray:
    """Resample a 2D float array to (W, H) using PIL Lanczos/bicubic."""
    W, H = size_wh
    if z.shape[1] == W and z.shape[0] == H:
        return z
    # PIL takes (W, H). Use "F" mode for float32.
    img = Image.fromarray(z.astype(np.float32), mode="F")
    resample_flag = Image.LANCZOS if mode == "lanczos" else Image.BICUBIC
    out = img.resize((W, H), resample=resample_flag)
    return np.asarray(out, dtype=np.float32)


def resample_mask(mask: np.ndarray, size_wh: tuple[int, int]) -> np.ndarray:
    """Downsample a boolean mask to (W, H) via bilinear coverage; threshold at 0.5.
    Preserves ice-sheet edges more faithfully than nearest-neighbor."""
    W, H = size_wh
    if mask.shape[1] == W and mask.shape[0] == H:
        return mask.astype(bool)
    img = Image.fromarray(mask.astype(np.float32), mode="F")
    out = img.resize((W, H), resample=Image.BILINEAR)
    return np.asarray(out) > 0.5


def polar_taper(H: int, start_deg: float = POLAR_TAPER_START_DEG) -> np.ndarray:
    """Per-row weight (H,) for a north-first equirectangular grid: 1 where the
    cell-centre |lat| <= start_deg, falling linearly to 0 at |lat| = 90."""
    lat_c = 90.0 - (np.arange(H, dtype=np.float64) + 0.5) * 180.0 / H
    t = (90.0 - np.abs(lat_c)) / (90.0 - start_deg)
    return np.clip(t, 0.0, 1.0).astype(np.float32)


def hillshade(z: np.ndarray, z_factor: float = HS_Z_FACTOR,
              az_deg: float = HS_AZIMUTH_DEG, alt_deg: float = HS_ALTITUDE_DEG,
              cos_lat_min: float = HS_COS_LAT_MIN) -> np.ndarray:
    """Horn hillshade in pixel space with z-factor.
    Returns float32 in [0, 1] with shape z.shape.

    dz/dx and dz/dy are in 3x3 Horn weighting (Sobel-like). Result is
    cos(zenith)*cos(slope) + sin(zenith)*sin(slope)*cos(azimuth - aspect).
    Latitude scaling: divide dz/dx by cos(lat) so slopes at high latitudes are
    not compressed by the equirectangular grid; cos(lat) is floored at
    cos_lat_min (cos 85 deg) so east-west gradients stay bounded at the poles.
    """
    H, W = z.shape
    # 3x3 Horn kernel
    zx = np.zeros_like(z, dtype=np.float32)
    zy = np.zeros_like(z, dtype=np.float32)
    # Interior cells
    a = z[:-2, :-2]; b = z[:-2, 1:-1]; c = z[:-2, 2:]
    d = z[1:-1, :-2];              f = z[1:-1, 2:]
    g = z[2:, :-2]; h = z[2:, 1:-1]; i = z[2:, 2:]
    zx[1:-1, 1:-1] = ((c + 2*f + i) - (a + 2*d + g)) / 8.0
    zy[1:-1, 1:-1] = ((g + 2*h + i) - (a + 2*b + c)) / 8.0
    # Edges: use one-sided diff
    zx[:, 0] = z[:, 1] - z[:, 0]
    zx[:, -1] = z[:, -1] - z[:, -2]
    zx[0, :] = zx[1, :]
    zx[-1, :] = zx[-2, :]
    zy[0, :] = z[1, :] - z[0, :]
    zy[-1, :] = z[-1, :] - z[-2, :]
    zy[:, 0] = zy[:, 1]
    zy[:, -1] = zy[:, -2]

    # Scale by z_factor to convert metres to pixel-width units
    zx *= z_factor
    zy *= z_factor

    # Latitude compression correction on dz/dx (grid runs from +90 at row 0)
    lat = np.linspace(np.pi/2, -np.pi/2, H, endpoint=False, dtype=np.float32)
    cos_lat = np.maximum(np.cos(lat), cos_lat_min).astype(np.float32)
    zx = zx / cos_lat[:, None]

    slope = np.arctan(np.sqrt(zx * zx + zy * zy))
    # ArcGIS convention: aspect = atan2(dz/dy, -dz/dx), clockwise from N
    aspect = np.arctan2(zy, -zx)
    zenith = math.radians(90.0 - alt_deg)
    azimuth = math.radians(360.0 - az_deg + 90.0)  # to math convention
    hs = (np.cos(zenith) * np.cos(slope)
          + np.sin(zenith) * np.sin(slope) * np.cos(azimuth - aspect))
    return np.clip(hs, 0.0, 1.0).astype(np.float32)


def blend_hillshade(rgb: np.ndarray, hs: np.ndarray, strength: float = HS_STRENGTH,
                    taper: bool = True) -> np.ndarray:
    """Multiply-blend hillshade (float [0,1]) onto RGB uint8. Strength 0 leaves
    the palette untouched; strength 1 uses pure hillshade. With taper, the
    hillshade is blended toward its flat-ground value HS_FLAT between |lat|
    80 deg and the poles; rows equatorward of 80 deg use hs unchanged, so the
    result there is bit-identical to the untapered blend."""
    if taper:
        t = polar_taper(hs.shape[0])[:, None]  # (H, 1), 1 equatorward of 80 deg
        hs = np.where(t >= 1.0, hs, np.float32(HS_FLAT) + t * (hs - np.float32(HS_FLAT))).astype(np.float32)
    factor = (1.0 - strength) + strength * hs  # (H, W) in [1-strength, 1]
    out = rgb.astype(np.float32) * factor[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def normal_map(z: np.ndarray, height_scale_m: float = NORMAL_HEIGHT_SCALE_M,
               cos_lat_min: float = HS_COS_LAT_MIN, taper: bool = True) -> np.ndarray:
    """Build a tangent-space normal map (uint8 RGB) from an elevation grid.
    dz/dx corrected for latitude (equirectangular), with the same cos(lat)
    clamp and polar taper as the hillshade (normals flatten towards the pole).
    nz is fixed positive."""
    H, W = z.shape
    # Central differences
    zx = np.zeros_like(z, dtype=np.float32)
    zy = np.zeros_like(z, dtype=np.float32)
    zx[:, 1:-1] = (z[:, 2:] - z[:, :-2]) * 0.5
    zx[:, 0] = z[:, 1] - z[:, 0]
    zx[:, -1] = z[:, -1] - z[:, -2]
    zy[1:-1, :] = (z[2:, :] - z[:-2, :]) * 0.5
    zy[0, :] = z[1, :] - z[0, :]
    zy[-1, :] = z[-1, :] - z[-2, :]

    lat = np.linspace(np.pi/2, -np.pi/2, H, endpoint=False, dtype=np.float32)
    cos_lat = np.maximum(np.cos(lat), cos_lat_min).astype(np.float32)
    zx = zx / cos_lat[:, None]
    if taper:
        t = polar_taper(H)[:, None]
        zx = zx * t
        zy = zy * t

    # Convert to normalized surface normals with height_scale_m defining what
    # counts as "unit" elevation per pixel width.
    inv = 1.0 / height_scale_m
    nx = -zx * inv
    ny = -zy * inv
    nz = np.ones_like(nx, dtype=np.float32)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= n; ny /= n; nz /= n
    # Encode to 8-bit
    r = np.round((nx + 1.0) * 127.5)
    g = np.round((ny + 1.0) * 127.5)
    b = np.round((nz + 1.0) * 127.5)
    return np.clip(np.stack([r, g, b], axis=-1), 0, 255).astype(np.uint8)


def _atomic_replace(tmp: Path, path: Path) -> None:
    """os.replace with a few retries (Windows refuses while a reader holds the file)."""
    for attempt in range(10):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.5 * (attempt + 1))
    os.replace(tmp, path)


def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    _atomic_replace(tmp, path)


def save_webp(arr_rgb: np.ndarray, path: Path, quality: int = WEBP_QUALITY) -> None:
    """Write to <name>.tmp then rename over the target, so readers never see a
    half-written texture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(arr_rgb, mode="RGB")
    tmp = path.with_name(path.name + ".tmp")
    img.save(tmp, format="WEBP", quality=quality, method=6)
    _atomic_replace(tmp, path)


def render_slice(age: int, lut: np.ndarray, force: bool = False,
                 ice_lut: np.ndarray | None = None) -> dict:
    out4 = OUT_DIR / "4k" / f"{age}.webp"
    out2 = OUT_DIR / "2k" / f"{age}.webp"
    outn = OUT_DIR / "4k" / f"{age}-normal.webp"

    if not force and out4.exists() and out2.exists() and outn.exists():
        return {"age_ma": age, "skipped": True,
                "sizes": {"4k": out4.stat().st_size,
                          "2k": out2.stat().st_size,
                          "normal": outn.stat().st_size}}

    t0 = time.time()
    ice_info: dict | None = None
    if age == 0:
        z_native = load_etopo()          # (10800, 21600) ice-surface
        bed_native = load_etopo_bed()    # (10800, 21600) bedrock
        source = "noaa-etopo2022-60s"
        resample_mode = "lanczos"        # downsample uses Lanczos
        # Ice mask at native ETOPO resolution: thickness > threshold.
        ice_native = (z_native - bed_native) > ICE_THICKNESS_THRESHOLD_M
        # True surface-area fraction (equirectangular is area-distorted by cos(lat)).
        w = cos_lat_weights(z_native.shape[0])
        row_frac = ice_native.mean(axis=1).astype(np.float64)
        ice_area_frac = float((row_frac * w).sum() / w.sum())
        # Save a small PNG of the mask for inspection.
        PROC_DIR.mkdir(parents=True, exist_ok=True)
        Image.fromarray((ice_native.astype(np.uint8) * 255), mode="L") \
            .resize((2048, 1024), resample=Image.BILINEAR) \
            .save(PROC_DIR / "ice_mask.png", optimize=True)
        ice_info = {
            "threshold_m": ICE_THICKNESS_THRESHOLD_M,
            "area_fraction": round(ice_area_frac, 6),
            "mask_native_shape": list(ice_native.shape),
        }
        if ice_lut is None:
            ice_lut = build_ice_lut()
    else:
        z_native = load_paleo(age)       # (1800, 3600)
        source = "scotese-paleodem-2018-v2"
        resample_mode = "cubic"          # upsample uses bicubic
    tload = time.time() - t0

    # Resample once each at 4k and 2k
    z4 = resample(z_native, (SIZE_4K[0], SIZE_4K[1]), mode=resample_mode)
    z2 = resample(z_native, (SIZE_2K[0], SIZE_2K[1]), mode=resample_mode)

    # Apply palette
    rgb4 = apply_palette(z4, lut)
    rgb2 = apply_palette(z2, lut)

    # Ice tint override (0 Ma only): replace masked cells with pale blue-white.
    if age == 0:
        mask4 = resample_mask(ice_native, (SIZE_4K[0], SIZE_4K[1]))
        mask2 = resample_mask(ice_native, (SIZE_2K[0], SIZE_2K[1]))
        rgb4[mask4] = apply_ice_tint(z4, ice_lut)[mask4]
        rgb2[mask2] = apply_ice_tint(z2, ice_lut)[mask2]

    # Hillshade at each resolution (matched to grid so relief is sharp at that scale)
    hs4 = hillshade(z4)
    hs2 = hillshade(z2)

    # Multiply-blend
    blended4 = blend_hillshade(rgb4, hs4)
    blended2 = blend_hillshade(rgb2, hs2)

    # Save colour rasters
    save_webp(blended4, out4)
    save_webp(blended2, out2)

    # Normal map at 4k
    nm4 = normal_map(z4)
    save_webp(nm4, outn)

    dt = time.time() - t0
    result = {
        "age_ma": age,
        "source_dataset": source,
        "label": "observed" if age == 0 else "interpreted",
        "seconds": round(dt, 1),
        "sizes": {
            "4k": out4.stat().st_size,
            "2k": out2.stat().st_size,
            "normal": outn.stat().st_size,
        },
    }
    if ice_info is not None:
        result["ice"] = ice_info
    return result


def write_index(entries: list[dict]) -> None:
    stops = [[e, h] for (e, h) in OCEAN_STOPS] + [[e, h] for (e, h) in LAND_STOPS]
    index = {
        "ages_ma": [e["age_ma"] for e in entries],
        "sizes": {"4k": [SIZE_4K[0], SIZE_4K[1]], "2k": [SIZE_2K[0], SIZE_2K[1]]},
        "format": "webp",
        "path_pattern": "globe/textures/{size}/{age}.webp",
        "normal_path_pattern": "globe/textures/4k/{age}-normal.webp",
        "modern": {
            "age_ma": 0,
            "dataset_id": "noaa-etopo2022-60s",
            "label": "observed",
            "ice_mask": "etopo2022 surface minus bedrock > 50 m",
        },
        "paleo": {
            "dataset_id": "scotese-paleodem-2018-v2",
            "label": "interpreted",
        },
        "palette": {
            "sea_level_m": SEA_LEVEL_M,
            "note": "hard step at 0 m: last ocean stop and first land stop coincide in x",
            "ocean_stops": [[e, h] for e, h in OCEAN_STOPS],
            "land_stops": [[e, h] for e, h in LAND_STOPS],
            "stops": stops,
        },
        "hillshade": {
            "azimuth_deg": HS_AZIMUTH_DEG,
            "altitude_deg": HS_ALTITUDE_DEG,
            "z_factor_per_m": HS_Z_FACTOR,
            "strength": HS_STRENGTH,
            "cos_lat_min_deg": HS_COS_LAT_MIN_DEG,
            "polar_taper_deg": [POLAR_TAPER_START_DEG, 90.0],
            "polar_taper_target": "flat-ground hillshade (cos zenith); normal map toward flat normal",
        },
        "normal_map_height_scale_m": NORMAL_HEIGHT_SCALE_M,
    }
    write_text_atomic(OUT_DIR / "index.json", json.dumps(index, indent=2))


def write_meta() -> None:
    now = datetime.now(timezone.utc).date().isoformat()
    meta = {
        # This directory bundles two datasets. dataset_id is a mapping of
        # texture family -> manifest id under data/manifests/.
        "dataset_id": {
            "0Ma": "noaa-etopo2022-60s",
            "5..300Ma": "scotese-paleodem-2018-v2",
        },
        "label": {
            "0Ma": "observed",
            "5..300Ma": "interpreted",
        },
        "source_ref": ["noaa-etopo2022", "scotese-2018"],
        "attribution": {
            "0Ma": (
                "NOAA National Centers for Environmental Information (2022), "
                "ETOPO 2022 Global Relief Model (60 arc-second, ice-surface and bedrock), "
                "doi:10.25921/fd45-gt74. Public domain (US Government work)."
            ),
            "5..300Ma": (
                "Scotese, C. R. and Wright, N. M. (2018), PALEOMAP Paleodigital "
                "Elevation Models (PaleoDEMS) for the Phanerozoic, 0.1 deg, Zenodo, "
                "doi:10.5281/zenodo.5460860. CC BY 4.0."
            ),
        },
        "license": {
            "noaa-etopo2022-60s": "public domain (US Government work)",
            "scotese-paleodem-2018-v2": "CC BY 4.0",
        },
        "generated": now,
        "script": "data/scripts/textures/render.py",
        "caveats": (
            "PaleoDEM (5-300 Ma) is an interpretive paleogeography model at "
            "0.1 deg (~11 km at equator); the authors describe outputs as "
            "estimates and no per-cell uncertainty is provided. Some pre-Cretaceous "
            "slices show polygon-shaped patches in the paleo-ocean floor - this is "
            "the author's block-by-block reconstruction methodology, not a pipeline "
            "artifact. Do not read morphology finer than ~11 km on paleo slices or "
            "~2 km on the modern (ETOPO) slice. "
            "The 0 Ma slice reports ice-surface (Greenland and Antarctica are the "
            "top of the ice sheet, not bedrock); Pliocene (5 Ma) and older slices "
            "from PaleoDEM show land-surface elevation and do not depict ice cover, "
            "so the polar ice caps disappear between 0 and 5 Ma - this is a genuine "
            "difference in what the two data products represent, not a rendering "
            "inconsistency. "
            "The ice mask on the 0 Ma slice is derived at render time as "
            "(ETOPO 2022 60s ice-surface) - (ETOPO 2022 60s bedrock) > 50 m, "
            "and only masked cells receive the pale blue-white ice tint. The "
            "PaleoDEM has no ice-surface / bedrock split, so no ice tint is "
            "applied to paleo slices; polar cover before 0 Ma is not depicted. "
            "The PaleoDEM's own rows nearest the poles show longitudinal banding "
            "(elevation varying by hundreds of metres along rows that converge on "
            "the pole), which appears as a faint radial fan around the pole on some "
            "paleo slices such as the 240 Ma south pole; it is left as in the source."
        ),
    }
    write_text_atomic(OUT_DIR / "meta.json", json.dumps(meta, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerate outputs even if present")
    ap.add_argument("--only", type=str, default="", help="comma-separated ages to render (else all)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "4k").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "2k").mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    if args.only:
        ages = [int(x) for x in args.only.split(",")]
    else:
        ages = AGES

    lut, _, _ = build_lut()
    ice_lut = build_ice_lut()

    # Write index.json early so partial progress is visible; update as we go.
    entries: list[dict] = []
    for a in AGES:
        entries.append({"age_ma": a})
    write_index(entries)
    write_meta()

    results: list[dict] = []
    for age in ages:
        try:
            r = render_slice(age, lut, force=args.force, ice_lut=ice_lut)
        except Exception as e:
            print(f"[fail] age={age} {e}")
            continue
        results.append(r)
        tag = "(skipped)" if r.get("skipped") else f"{r['seconds']}s"
        print(f"[done] {age:>3} Ma  4k={r['sizes']['4k']/1e6:5.2f} MB"
              f"  2k={r['sizes']['2k']/1e6:5.2f} MB"
              f"  normal={r['sizes']['normal']/1e6:5.2f} MB  {tag}")

    # Refresh index with the ages we actually shipped
    have = sorted({e for e in AGES
                   if (OUT_DIR / "4k" / f"{e}.webp").exists()
                   and (OUT_DIR / "2k" / f"{e}.webp").exists()})
    write_index([{"age_ma": a} for a in have])

    # Save render log for provenance
    log = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "ages_written": have,
        "results": results,
    }
    (PROC_DIR / "render-log.json").write_text(json.dumps(log, indent=2))
    print(f"[index] ages_ma={have[:5]}...{have[-3:]} n={len(have)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
