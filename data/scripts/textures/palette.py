"""Hypsometric-bathymetric palette used for every slice.

Design goals: professional, print-atlas quality, muted; no cartoon greens; deep
ocean dark navy; a hard transition at sea level (shelf blue to sandy lowland);
sage/olive lowlands through pale ochre to warm brown, then grey to white at
high altitude. Sea level is at exactly 0 m.

The same stops are used to render both the PaleoDEM slices and the modern
ETOPO slice so the crossfade between ages is seamless.
"""
from __future__ import annotations
import numpy as np

# (elevation_m, "#rrggbb")
# Ocean side (elevation <= 0)
OCEAN_STOPS: list[tuple[float, str]] = [
    (-8000.0, "#071527"),  # abyssal, dark navy
    (-6000.0, "#0b213f"),
    (-4000.0, "#123055"),
    (-2000.0, "#1e3e63"),
    (-1000.0, "#2b5079"),
    ( -500.0, "#456e94"),
    ( -200.0, "#6d94b8"),  # shelf, noticeably lighter
    (  -50.0, "#95b4cf"),
    (    0.0, "#b8d0e4"),  # coastal, very pale blue
]
# Land side (elevation > 0)
LAND_STOPS: list[tuple[float, str]] = [
    (    0.0, "#d6c8a3"),  # sandy warm neutral (beach), hard step from ocean
    (  100.0, "#a7b57e"),  # soft sage green (lowland)
    (  500.0, "#8ba368"),  # olive green
    ( 1000.0, "#b6b378"),  # yellow-green transition
    ( 1500.0, "#c9b483"),  # pale ochre
    ( 2000.0, "#b48d5f"),  # warm tan / light brown
    ( 3000.0, "#8f6a48"),  # warm brown (last warm stop; higher = grey/white)
    ( 3500.0, "#a09a92"),  # grey (bare rock / high plateau)
    ( 4000.0, "#c2bdb5"),  # light grey (Tibetan Plateau)
    ( 4800.0, "#eeece6"),  # near white (very high peaks, glaciated)
    ( 5000.0, "#ffffff"),  # snow / peak
    ( 6500.0, "#ffffff"),  # snow / peak (clamp)
]
SEA_LEVEL_M = 0.0
E_MIN = -11000.0
E_MAX = 8500.0


def hex2rgb(s: str) -> tuple[float, float, float]:
    s = s.lstrip("#")
    return (int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0, int(s[4:6], 16) / 255.0)


def _interp_stops(stops: list[tuple[float, str]], e_grid: np.ndarray) -> np.ndarray:
    """Linearly interpolate a set of hex-color stops onto elevations e_grid.
    Values outside the range clamp to the nearest stop."""
    xs = np.array([s[0] for s in stops], dtype=np.float64)
    cs = np.array([hex2rgb(s[1]) for s in stops], dtype=np.float64)
    out = np.empty((e_grid.size, 3), dtype=np.float64)
    for k in range(3):
        out[:, k] = np.interp(e_grid, xs, cs[:, k])
    return out


def build_lut(n: int = 32768) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build a lookup table covering [E_MIN, E_MAX].

    Returns (lut_rgb uint8[n,3], e_axis float64[n], (E_MIN, E_MAX)).
    Sea level is enforced as a hard discontinuity: index n/2 - 1 is the last
    ocean color; index n/2 is the first land color.
    """
    e_axis = np.linspace(E_MIN, E_MAX, n)
    # Split at 0 (sea level). For any elevation <= 0, use ocean palette; > 0
    # uses the land palette. The two nearest samples straddle 0 so the
    # transition is a single-cell hard step.
    ocean_mask = e_axis <= SEA_LEVEL_M
    rgb = np.empty((n, 3), dtype=np.float64)
    rgb[ocean_mask] = _interp_stops(OCEAN_STOPS, e_axis[ocean_mask])
    rgb[~ocean_mask] = _interp_stops(LAND_STOPS, e_axis[~ocean_mask])
    lut = np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)
    return lut, e_axis, (E_MIN, E_MAX)


def apply_palette(elev_m: np.ndarray, lut: np.ndarray | None = None) -> np.ndarray:
    """Map an elevation array (metres) to an (H, W, 3) uint8 RGB image.

    NaNs are treated as deepest ocean.
    """
    if lut is None:
        lut, _, _ = build_lut()
    n = lut.shape[0]
    e = np.where(np.isfinite(elev_m), elev_m, E_MIN)
    idx = (e - E_MIN) / (E_MAX - E_MIN) * (n - 1)
    idx = np.clip(np.round(idx), 0, n - 1).astype(np.int32)
    return lut[idx]


def palette_stops_for_index_json() -> list[list]:
    """Return a compact list of [elevation_m, hex] stops for index.json.

    Includes both -0 (last ocean) and +0 (first land) so the hard step is
    machine-readable.
    """
    stops: list[list] = []
    for e, h in OCEAN_STOPS:
        stops.append([e, h])
    for e, h in LAND_STOPS:
        # add "+0" marker distinct from the ocean "0" already present
        stops.append([e, h])
    return stops
