"""GLACIMONTIS (Flantua et al. 2026) LGM glacier polygons -> app/public/data/terrain/lgm-extent.geojson.

Uses the 'EmpiricallyReconstructedPaleoglaciers' layer (760 polygons compiled
from 209 published reconstructions), clipped by whole-polygon bbox to the
wider Alpine ice window (BBOX_ICE).
"""
import json
import sys
from pathlib import Path

import shapefile
from pyproj import Transformer
from shapely.geometry import shape, mapping, box as shp_box

sys.path.insert(0, str(Path(__file__).parent))
from common import BBOX_ICE, GENERATED, round_coords, _geom_bbox

SHP = Path('E:/Projects/Dolomites/data/raw/glacimontis-2026/shp/Shapefiles/EmpiricallyReconstructedPaleoglaciers.shp')
OUT = Path('E:/Projects/Dolomites/app/public/data/terrain/lgm-extent.geojson')
META = Path('E:/Projects/Dolomites/app/public/data/terrain/lgm-extent.meta.json')


def main():
    r = shapefile.Reader(str(SHP))
    fields = [f[0] for f in r.fields[1:]]
    to_wgs = Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True)
    to_merc = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True)
    minx, miny, maxx, maxy = BBOX_ICE
    mx1, my1 = to_merc.transform(minx, miny)
    mx2, my2 = to_merc.transform(maxx, maxy)
    mmin_x, mmax_x = min(mx1, mx2), max(mx1, mx2)
    mmin_y, mmax_y = min(my1, my2), max(my1, my2)
    features = []
    total = 0
    for rec in r.iterShapeRecords():
        total += 1
        shp = rec.shape
        if hasattr(shp, 'bbox') and shp.bbox:
            bx = shp.bbox
            if bx[2] < mmin_x or bx[0] > mmax_x or bx[3] < mmin_y or bx[1] > mmax_y:
                continue
        rd = dict(zip(fields, rec.record))
        # Convert Web-Mercator shapefile geometry to WGS84 GeoJSON. Use
        # pyshp's __geo_interface__ so multi-part polygons stay separate.
        gi = shp.__geo_interface__

        def reproject_ring(ring):
            if not ring:
                return ring
            xs = [pt[0] for pt in ring]
            ys = [pt[1] for pt in ring]
            lons, lats = to_wgs.transform(xs, ys)
            return [[lo, la] for lo, la in zip(lons, lats)]

        if gi['type'] == 'Polygon':
            coords = [reproject_ring(r) for r in gi['coordinates']]
            geom = {'type': 'Polygon', 'coordinates': coords}
        elif gi['type'] == 'MultiPolygon':
            polys = [[reproject_ring(r) for r in poly] for poly in gi['coordinates']]
            geom = {'type': 'MultiPolygon', 'coordinates': polys}
        else:
            continue
        b = _geom_bbox(geom)
        if b is None or b[2] < minx or b[0] > maxx or b[3] < miny or b[1] > maxy:
            continue
        # Clip to the ice window and simplify. Some source polygons cover the
        # whole Alpine arc; clipping brings them down from hundreds of
        # thousands of vertices to a manageable few thousand per feature.
        try:
            g = shape(geom).buffer(0)
            clip = shp_box(minx, miny, maxx, maxy)
            clipped = g.intersection(clip)
            if clipped.is_empty:
                continue
            simplified = clipped.simplify(0.0005, preserve_topology=True)
            geom = mapping(simplified)
        except Exception as ex:
            print('WARN simplify failed', ex)
        round_coords(geom, 5)
        props = {
            'mid': rd.get('mid'),
            'pid': rd.get('pid'),
            'source_citation': rd.get('scitation'),
            'source_reference': rd.get('reference'),
            'source_doi': rd.get('doi'),
            'source_year': rd.get('yrpubli'),
            'range': rd.get('mrange3') or rd.get('mrange2'),
            'sub_range': rd.get('mrange5') or rd.get('mrange4'),
            'deglaciation_upper_yr': rd.get('deglaupp'),
            'deglaciation_lower_yr': rd.get('deglalow'),
            'area_km2': rd.get('area'),
            'paleo_ela_m': rd.get('paleoela'),
        }
        features.append({'type': 'Feature', 'geometry': geom, 'properties': props})
    print(f'scanned={total} kept={len(features)}')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, separators=(',', ':')), encoding='utf-8')
    META.write_text(json.dumps({
        'dataset_id': 'glacimontis-2026',
        'label': 'interpreted',
        'source_ref': 'flantua-2026',
        'attribution': ('Lima A.C., Dulfer H.E., Hughes A.L.C., Margold M., Barr I., Laabs B.J.C., '
                        'Flantua S.G.A. (2026). Mountain glacier extents at the Last Glacial '
                        'Maximum. Sci. Data. Data: doi:10.5281/zenodo.15600659. '
                        'Users must also cite the original per-polygon publications '
                        '(properties.source_reference).'),
        'license': 'CC BY 4.0',
        'generated': GENERATED,
        'script': 'data/scripts/quaternary/build_lgm_extent.py',
        'clip_bbox': list(BBOX_ICE),
        'layer': 'EmpiricallyReconstructedPaleoglaciers',
        'notes': ('Compilation of published paleoglacier reconstructions for MIS 3-2 '
                  '(~57-14 ka BP). Polygons are per-glacier extents, not a single unioned '
                  'LGM ice mask; ages and precision differ between source studies.'),
    }, indent=2), encoding='utf-8')
    print('wrote', OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
