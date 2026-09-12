"""Reproject Seguinot et al. 2018 alpcyc.1km.epic.pp ice-thickness snapshots
(120 records, 1 kyr apart) onto a Web Mercator grid over the Alpine ice
window, save one colorized RGBA WebP per snapshot for the map layer and one
16-bit grayscale PNG per snapshot for numeric readouts.

Contract 2.3 (docs/04-data-contracts.md).

Idempotent - a snapshot whose target files already exist at the right size
are skipped unless FORCE=1.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image
from pyproj import Transformer
from scipy.ndimage import map_coordinates

sys.path.insert(0, str(Path(__file__).parent))
from common import BBOX_ICE, GENERATED

NC = Path('E:/Projects/Dolomites/data/raw/seguinot2018-alps-1km/alpcyc.1km.epic.pp.ex.1ka.nc')
OUT_DIR = Path('E:/Projects/Dolomites/app/public/data/terrain/ice')
THK_DIR = OUT_DIR / 'thickness'
PREVIEW_DIR = Path('E:/Projects/Dolomites/data/processed/quaternary/preview')

RGBA_W = 640                             # colorized RGBA frames at 2x native resolution
THICKNESS_W = 320                        # 16-bit thickness at native 1 km resolution
BBOX = BBOX_ICE                          # (minLon, minLat, maxLon, maxLat)

# Palette: [thickness_m, (r,g,b,a)]. Fully transparent below 10 m.
# Ramp: pale ice-blue at low thickness -> deeper blue-grey at high thickness,
# matching the contract's "subtle darker tones for thick ice".
PALETTE_STOPS = [
    (0,     (255, 255, 255,   0)),
    (10,    (240, 245, 250,  60)),
    (50,    (225, 236, 246, 130)),
    (150,   (206, 224, 240, 180)),
    (400,   (176, 205, 228, 215)),
    (1000,  (140, 178, 210, 235)),
    (2500,  (100, 148, 188, 245)),
]


def build_colormap():
    """Return uint8 LUT of shape (T, 4) where T = MAX_THICK_M+1.

    Linear interpolation between the PALETTE_STOPS.
    """
    max_t = 3000
    lut = np.zeros((max_t + 1, 4), dtype=np.uint8)
    stops = PALETTE_STOPS
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        ns = t1 - t0
        for k in range(ns + 1):
            f = k / max(ns, 1)
            rgba = tuple(int(round(c0[j] * (1 - f) + c1[j] * f)) for j in range(4))
            lut[t0 + k] = rgba
    # extend flat above the last stop
    lut[stops[-1][0]:] = stops[-1][1]
    # anything below 10 m is fully transparent
    lut[:10] = (255, 255, 255, 0)
    return lut


def target_grid_wgs_to_utm(transformer, target_w):
    """Return per-target-pixel UTM32N (x, y) arrays for the WebMerc target grid."""
    to_merc = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True)
    to_wgs  = Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True)
    minx, miny, maxx, maxy = BBOX
    mx1, my1 = to_merc.transform(minx, miny)
    mx2, my2 = to_merc.transform(maxx, maxy)
    w = target_w
    h = int(round(w * (my2 - my1) / (mx2 - mx1)))
    # pixel centres in Web Mercator
    xs = np.linspace(mx1, mx2, w, endpoint=False) + (mx2 - mx1) / w / 2.0
    ys = np.linspace(my2, my1, h, endpoint=False) - (my2 - my1) / h / 2.0
    mx, my = np.meshgrid(xs, ys)
    # Web Mercator -> WGS84 -> UTM32N
    lon, lat = to_wgs.transform(mx.ravel(), my.ravel())
    ux, uy = transformer.transform(lon, lat)
    ux = ux.reshape(h, w)
    uy = uy.reshape(h, w)
    return w, h, (mx1, my1, mx2, my2), ux, uy


def year_to_ka(year_val) -> int:
    """cftime year -> integer thousands-of-years-BP (0..119)."""
    try:
        y = int(year_val.year)
    except AttributeError:
        y = int(year_val)
    return int(round(-y / 1000))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    THK_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    force = os.environ.get('FORCE') == '1'
    lut = build_colormap()
    ds = xr.open_dataset(NC)
    xs_src = ds['x'].values         # UTM32N x, meters, len 901
    ys_src = ds['y'].values         # UTM32N y, meters, len 601
    dx = float(xs_src[1] - xs_src[0])
    dy = float(ys_src[1] - ys_src[0])
    print('source grid dx,dy:', dx, dy, 'nx,ny:', len(xs_src), len(ys_src))

    # UTM32N transformer (WGS84 -> +proj=utm +zone=32 +a=6378137 +rf=298.2572)
    utm = Transformer.from_crs('EPSG:4326', '+proj=utm +zone=32 +a=6378137 +rf=298.257223563 +towgs84=0,0,0 +units=m +no_defs', always_xy=True)

    # Create grids for both RGBA and thickness
    rgba_w, rgba_h, merc_bbox, ux_rgba, uy_rgba = target_grid_wgs_to_utm(utm, RGBA_W)
    thk_w, thk_h, _, ux_thk, uy_thk = target_grid_wgs_to_utm(utm, THICKNESS_W)
    print(f'RGBA target: {rgba_w} x {rgba_h}')
    print(f'Thickness target: {thk_w} x {thk_h}')

    # Convert UTM (m) -> source pixel indices for map_coordinates (for RGBA).
    # PISM source y axis is monotonic increasing (bottom -> top); the source
    # grid has y[0]=4820000 (south) ... y[-1]=5420000 (north).
    row_rgba = (uy_rgba - ys_src[0]) / dy
    col_rgba = (ux_rgba - xs_src[0]) / dx
    valid_rgba = (row_rgba >= 0) & (row_rgba < len(ys_src) - 1) & (col_rgba >= 0) & (col_rgba < len(xs_src) - 1)
    coords_rgba = np.stack([row_rgba.ravel(), col_rgba.ravel()], axis=0)

    # Same for thickness grid
    row_thk = (uy_thk - ys_src[0]) / dy
    col_thk = (ux_thk - xs_src[0]) / dx
    valid_thk = (row_thk >= 0) & (row_thk < len(ys_src) - 1) & (col_thk >= 0) & (col_thk < len(xs_src) - 1)
    coords_thk = np.stack([row_thk.ravel(), col_thk.ravel()], axis=0)

    times = ds['time'].values
    ka_list = [year_to_ka(t) for t in times]
    print(f'first snap ka={ka_list[0]}, last snap ka={ka_list[-1]}, n={len(ka_list)}')

    preview_targets = {120, 25, 20, 15, 10, 0}

    for t_idx, ka in enumerate(ka_list):
        rgba_path = OUT_DIR / f'{ka}.webp'
        thk_path = THK_DIR / f'{ka}.png'
        if (not force) and rgba_path.exists() and thk_path.exists():
            # cheap size check
            if rgba_path.stat().st_size > 0 and thk_path.stat().st_size > 0:
                continue

        thk_src = ds['thk'].isel(time=t_idx).values.astype(np.float32)
        # PISM `thk` may carry NaN outside its ice mask; reset to 0 so the
        # bilinear resample stays finite everywhere.
        thk_src = np.nan_to_num(thk_src, nan=0.0, posinf=0.0, neginf=0.0)

        # Render for RGBA (bilinear resampling)
        thk_rgba = map_coordinates(thk_src, coords_rgba, order=1, cval=0.0, mode='constant')
        thk_rgba = thk_rgba.reshape(rgba_h, rgba_w)
        thk_rgba = np.nan_to_num(thk_rgba, nan=0.0, posinf=0.0, neginf=0.0)
        thk_rgba[~valid_rgba] = 0.0
        # Colorize
        idx = np.clip(thk_rgba, 0, lut.shape[0] - 1).astype(np.int32)
        rgba = lut[idx]
        Image.fromarray(rgba, mode='RGBA').save(rgba_path, format='WEBP', lossless=True)

        # Render for thickness (bilinear resampling)
        thk_output = map_coordinates(thk_src, coords_thk, order=1, cval=0.0, mode='constant')
        thk_output = thk_output.reshape(thk_h, thk_w)
        thk_output = np.nan_to_num(thk_output, nan=0.0, posinf=0.0, neginf=0.0)
        thk_output[~valid_thk] = 0.0
        # 16-bit grayscale metres
        thk16 = np.clip(thk_output, 0, 65535).astype(np.uint16)
        Image.fromarray(thk16, mode='I;16').save(thk_path)

        n_ice_px = int((thk_rgba >= 10).sum())
        if ka in preview_targets:
            Image.fromarray(rgba, mode='RGBA').save(PREVIEW_DIR / f'ice-{ka:03d}ka.png')
        print(f'  {ka:>3} ka: ice px >= 10 m = {n_ice_px:>7}  max thk = {float(thk_rgba.max()):>7.1f} m')

    # index.json (contract 2.3)
    minx, miny, maxx, maxy = BBOX
    index = {
        'ages_ka': sorted(set(ka_list), reverse=True),
        'path_pattern': 'terrain/ice/{ka}.webp',
        'thickness_path_pattern': 'terrain/ice/thickness/{ka}.png',
        'bounds': [minx, miny, maxx, maxy],
        'crs': 'EPSG:3857',
        'size': [rgba_w, rgba_h],
        'thickness_size': [thk_w, thk_h],
        'encoding': 'rgba-colorized',
        'native_resolution_m': 1000,
        'render_scale': 2,
        'thickness_stops_m': [[s, list(c)] for s, c in PALETTE_STOPS],
        'run': 'alpcyc.1km.epic.pp',
        'note_step': 'One frame per 1 kyr; the file for age N contains the model state at year -N kyr (rounded).',
    }
    (OUT_DIR / 'index.json').write_text(json.dumps(index, indent=2), encoding='utf-8')

    meta = {
        'dataset_id': 'seguinot2018-alps-1km',
        'label': 'modeled',
        'source_ref': 'seguinot-2018',
        'attribution': ('Seguinot J., Ivy-Ochs S., Jouvet G., Huss M., Funk M., Preusser F. '
                        '(2018). Modelling last glacial cycle ice dynamics in the Alps. '
                        'The Cryosphere 12, 3265-3285. Continuous-variables dataset: Zenodo '
                        '1423176 (CC BY 4.0), file alpcyc.1km.epic.pp.ex.1ka.nc.'),
        'license': 'CC BY 4.0',
        'generated': GENERATED,
        'script': 'data/scripts/quaternary/build_ice_frames.py',
        'run': 'alpcyc.1km.epic.pp',
        'run_choice_rationale': ('EPICA-Dome-C temperature forcing plus palaeo-precipitation '
                                 'reduction is the reference configuration used in the paper '
                                 'figures; 1 km is the finest published resolution. Chosen over '
                                 'GRIP and MD01-2444 forcings so the temperature timing matches '
                                 'the CENOGRID / PhanDA curves the site already ships.'),
        'source_crs': 'UTM 32N (WGS84 sphere, PISM run definition)',
        'source_resolution_m': 1000,
        'time_step_kyr': 1,
        'time_range_ka': [max(ka_list), min(ka_list)],
        'target_bounds': list(BBOX),
        'rgba_size_px': [rgba_w, rgba_h],
        'thickness_size_px': [thk_w, thk_h],
        'target_crs': 'EPSG:3857',
        'transparency_below_m': 10,
        'resampling_method': 'bilinear for both RGBA and thickness',
        'caveats': ('Ice-sheet model output, not observation. The 1 km resolution captures '
                    'trunk-glacier geometry well but under-represents thin plateau ice. '
                    'Snapshots are dated by their nearest 1-kyr marker on the PISM time axis '
                    '(cftime year rounded to kyr); the model was initialised at 120 ka and '
                    'the first written snapshot is labelled 119 ka (see time_range_ka).'),
    }
    (OUT_DIR / 'meta.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print('wrote index.json and meta.json')


if __name__ == '__main__':
    main()
