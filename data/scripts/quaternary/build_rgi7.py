"""Build app/public/data/terrain/glaciers-rgi7.geojson from the RGI 7.0
region 11 (Central Europe) shapefile.
"""
import json
import sys
from pathlib import Path

import shapefile  # pyshp

sys.path.insert(0, str(Path(__file__).parent))
from common import BBOX_TERRAIN, GENERATED, round_coords, _geom_bbox

SHP = Path('E:/Projects/Dolomites/data/raw/rgi7-region11/RGI2000-v7.0-G-11_central_europe/RGI2000-v7.0-G-11_central_europe.shp')
OUT = Path('E:/Projects/Dolomites/app/public/data/terrain/glaciers-rgi7.geojson')
META = Path('E:/Projects/Dolomites/app/public/data/terrain/glaciers-rgi7.meta.json')


def to_multipoly(pts, parts, shape_type):
    """Convert pyshp POLYGON parts into GeoJSON Polygon/MultiPolygon."""
    rings = []
    for i, s in enumerate(parts):
        e = parts[i + 1] if i + 1 < len(parts) else len(pts)
        ring = [[float(p[0]), float(p[1])] for p in pts[s:e]]
        rings.append(ring)
    if not rings:
        return None
    # RGI ships one polygon (possibly multi-ring) per feature; keep as-is
    return {'type': 'Polygon', 'coordinates': rings}


def main():
    r = shapefile.Reader(str(SHP))
    fields = [f[0] for f in r.fields[1:]]
    minx, miny, maxx, maxy = BBOX_TERRAIN
    features = []
    total = 0
    for rec in r.iterShapeRecords():
        total += 1
        shp = rec.shape
        rd = dict(zip(fields, rec.record))
        # cheap prefilter using record centroid lon/lat
        clon = rd.get('cenlon')
        clat = rd.get('cenlat')
        if clon is None or clat is None:
            continue
        # Skip early with a generous 0.3 deg buffer
        if not (minx - 0.3 <= clon <= maxx + 0.3 and miny - 0.3 <= clat <= maxy + 0.3):
            continue
        geom = to_multipoly(shp.points, shp.parts, shp.shapeType)
        if geom is None:
            continue
        b = _geom_bbox(geom)
        if b is None or b[2] < minx or b[0] > maxx or b[3] < miny or b[1] > maxy:
            continue
        round_coords(geom, 5)
        # Compact properties for the app
        name = rd.get('glac_name') or ''
        props = {
            'rgi_id': rd.get('rgi_id'),
            'name': name if name and name != 'None' else None,
            'area_km2': rd.get('area_km2'),
            'primeclass': rd.get('primeclass'),
            'zmin_m': rd.get('zmin_m'),
            'zmax_m': rd.get('zmax_m'),
            'zmed_m': rd.get('zmed_m'),
        }
        features.append({'type': 'Feature', 'geometry': geom, 'properties': props})
    print(f'scanned={total} kept={len(features)}')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, separators=(',', ':')), encoding='utf-8')
    META.write_text(json.dumps({
        'dataset_id': 'rgi7-region11',
        'label': 'observed',
        'source_ref': 'rgi7-2023',
        'attribution': 'RGI Consortium (2023), Randolph Glacier Inventory 7.0, doi:10.5067/F6JMOVY5NAVZ.',
        'license': 'CC BY 4.0',
        'generated': GENERATED,
        'script': 'data/scripts/quaternary/build_rgi7.py',
        'region': '11 Central Europe',
        'source_note': 'Downloaded from the open Bremen mirror (cluster.klima.uni-bremen.de/~fmaussion) of the NSIDC-0770 v7 release; identical content to the login-gated NSIDC copy.',
        'clip_bbox': list(BBOX_TERRAIN),
    }, indent=2), encoding='utf-8')
    print('wrote', OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
