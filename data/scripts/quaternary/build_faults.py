"""DISS 3.3.1 sources (composite + individual) -> app/public/data/terrain/faults.geojson.

Uses the WFS endpoints exposed by services.seismofaults.eu for DISS 3.3.1
(the same endpoints the official DISS download page uses to build its
"download GeoJSON" bundle).

- iss331   : Individual Seismogenic Sources (surface projection polygons)
- csstop331: Composite Seismogenic Sources (surface trace of the top edge)
- dss331   : Debated Seismogenic Sources (polygons)

All three are clipped by whole-feature bbox to the terrain window and
tagged with a `class` property so the app can style them differently.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import BBOX_TERRAIN, GENERATED, clip_geojson, round_coords

SRC = Path('E:/Projects/Dolomites/data/raw/diss331')
OUT = Path('E:/Projects/Dolomites/app/public/data/terrain/faults.geojson')
META = Path('E:/Projects/Dolomites/app/public/data/terrain/faults.meta.json')


LAYER_KINDS = {
    'iss331':    ('individual',        'iss'),
    'csstop331': ('composite_top',     'css'),
    'dss331':    ('debated',           'dss'),
}


def main():
    out_features = []
    for layer, (kind, short) in LAYER_KINDS.items():
        fc = json.loads((SRC / f'{layer}.geojson').read_text(encoding='utf-8'))
        clipped = clip_geojson(fc, BBOX_TERRAIN)
        for f in clipped['features']:
            round_coords(f['geometry'], 5)
            props = {
                'type': kind,
                'idsource': f['properties'].get('idsource'),
                'name': f['properties'].get('sourcename'),
                'maxmag': f['properties'].get('maxmag'),
                'mindepth_km': f['properties'].get('mindepth'),
                'maxdepth_km': f['properties'].get('maxdepth'),
                # keep DISS internal id so users can look up the source card
                'linktoinfo': f['properties'].get('linktoinfo'),
            }
            out_features.append({'type': 'Feature', 'geometry': f['geometry'], 'properties': props})
        print(f'{layer}: {len(fc["features"])} total, {len(clipped["features"])} in clip')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'type': 'FeatureCollection', 'features': out_features}, separators=(',', ':')), encoding='utf-8')
    META.write_text(json.dumps({
        'dataset_id': 'diss-3.3.1',
        'label': 'interpreted',
        'source_ref': 'diss-3.3.1',
        'attribution': ('DISS Working Group (2021). Database of Individual Seismogenic '
                        'Sources (DISS), version 3.3.1: A compilation of potential sources '
                        'for earthquakes larger than M 5.5 in Italy and surrounding areas. '
                        'INGV. doi:10.13127/diss3.3.1'),
        'license': 'CC BY 4.0',
        'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'generated': GENERATED,
        'script': 'data/scripts/quaternary/build_faults.py',
        'clip_bbox': list(BBOX_TERRAIN),
        'source_layers': list(LAYER_KINDS.keys()),
        'notes': ('DISS 3.3.1 subset in the Dolomites terrain window. Class '
                  '(properties.type): "individual" = ISS surface projection polygon; '
                  '"composite_top" = CSS top-edge line; "debated" = DSS polygon. '
                  'Fetched from the '
                  'DISS 3.3.1 WFS at services.seismofaults.eu on ' + GENERATED + '.'),
    }, indent=2), encoding='utf-8')
    print('wrote', OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
