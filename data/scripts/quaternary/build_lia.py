"""Reinthaler & Paul (2025) Little Ice Age glacier outlines -> GeoJSON WGS84,
clipped to the terrain bbox. Zenodo record 14336826 (release 14336827).
"""
import json
import sys
from pathlib import Path

import shapefile
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).parent))
from common import BBOX_TERRAIN, GENERATED, round_coords, _geom_bbox

SHP = Path('E:/Projects/Dolomites/data/raw/reinthaler-paul-2025-lia/LIA_Alps_Reinthaler_Paul_2024.shp')
OUT = Path('E:/Projects/Dolomites/app/public/data/terrain/glaciers-lia.geojson')
META = Path('E:/Projects/Dolomites/app/public/data/terrain/glaciers-lia.meta.json')


def main():
    r = shapefile.Reader(str(SHP))
    fields = [f[0] for f in r.fields[1:]]
    # UTM 32N -> WGS84
    t = Transformer.from_crs('EPSG:32632', 'EPSG:4326', always_xy=True)
    minx, miny, maxx, maxy = BBOX_TERRAIN
    # Pre-clip in UTM to save transform cost
    utm_min = t.transform(minx, miny, direction='INVERSE')
    utm_max = t.transform(maxx, maxy, direction='INVERSE')
    umin_x, umax_x = min(utm_min[0], utm_max[0]) - 1000, max(utm_min[0], utm_max[0]) + 1000
    umin_y, umax_y = min(utm_min[1], utm_max[1]) - 1000, max(utm_min[1], utm_max[1]) + 1000
    features = []
    total = 0
    kept = 0
    for rec in r.iterShapeRecords():
        total += 1
        shp = rec.shape
        # bbox filter (UTM)
        if hasattr(shp, 'bbox') and shp.bbox:
            bx = shp.bbox
            if bx[2] < umin_x or bx[0] > umax_x or bx[3] < umin_y or bx[1] > umax_y:
                continue
        rd = dict(zip(fields, rec.record))
        # Reproject all rings
        rings = []
        for i, s in enumerate(shp.parts):
            e = shp.parts[i + 1] if i + 1 < len(shp.parts) else len(shp.points)
            pts = shp.points[s:e]
            if not pts:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            lons, lats = t.transform(xs, ys)
            ring = [[lo, la] for lo, la in zip(lons, lats)]
            rings.append(ring)
        if not rings:
            continue
        geom = {'type': 'Polygon', 'coordinates': rings}
        b = _geom_bbox(geom)
        if b is None or b[2] < minx or b[0] > maxx or b[3] < miny or b[1] > maxy:
            continue
        round_coords(geom, 5)
        props = {
            'lia_id': rd.get('LIA_ID'),
            'reg_id': rd.get('reg_ID'),
            'area_km2_lia': rd.get('Area_LIA'),
            'z_min_m': rd.get('MIN'),
            'z_max_m': rd.get('MAX'),
            'z_mean_m': rd.get('MEAN'),
            'mean_thk_m': rd.get('Mean_thk'),
            'source_citation': rd.get('Citation'),
            'source_doi': rd.get('doi'),
            'year_ref': 1850,  # LIA reference year (Reinthaler & Paul 2025)
        }
        features.append({'type': 'Feature', 'geometry': geom, 'properties': props})
        kept += 1
    print(f'scanned={total} kept={kept}')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, separators=(',', ':')), encoding='utf-8')
    META.write_text(json.dumps({
        'dataset_id': 'reinthaler-paul-2025-lia',
        'label': 'interpreted',
        'source_ref': 'reinthaler-paul-2025',
        'attribution': 'Reinthaler J. and Paul F. (2025). The Cryosphere 19, 753-777. doi:10.5194/tc-19-753-2025. Outlines: doi:10.5281/zenodo.14336826.',
        'license': 'CC BY 4.0',
        'generated': GENERATED,
        'script': 'data/scripts/quaternary/build_lia.py',
        'clip_bbox': list(BBOX_TERRAIN),
        'notes': ('LIA glacier outlines for the European Alps circa 1850, reconstructed '
                  'in 14 sub-regions. Per-feature source citations are preserved '
                  'in properties.source_citation and source_doi. The reference year '
                  'is a nominal 1850 for the "LIA maximum" family of maps; actual '
                  'extents were mapped from different sources at slightly different '
                  'nineteenth-century dates.'),
    }, indent=2), encoding='utf-8')
    print('wrote', OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
