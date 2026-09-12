"""Shared constants for the QUATERNARY pipeline."""
from datetime import date

# Terrain bounding box (contract 2.4 default).
BBOX_TERRAIN = (10.3, 45.8, 12.7, 47.2)   # (minLon, minLat, maxLon, maxLat)
# Wider bounding box used for ice frames and LGM extent so context beyond
# the terrain box (Adige lobes, Bolzano basin, foreland) stays in the picture.
BBOX_ICE     = (9.5, 45.5, 13.5, 47.5)

# Reference point for uplift extraction (Dolomites centre).
REF_LAT, REF_LON = 46.5, 11.8

GENERATED = date.today().isoformat()


def clip_geojson(fc: dict, bbox: tuple[float, float, float, float]) -> dict:
    """Trivially clip a FeatureCollection to a bbox by whole-feature bbox test.

    This does not intersect polygons with the box - a feature is kept iff its
    envelope overlaps the target envelope. Sufficient here because the sources
    have per-feature bboxes small enough that no fragment is missed at the
    edge of the terrain window.
    """
    minx, miny, maxx, maxy = bbox
    kept = []
    for f in fc.get('features', []):
        g = f.get('geometry')
        if not g:
            continue
        b = _geom_bbox(g)
        if b is None:
            continue
        if b[2] < minx or b[0] > maxx or b[3] < miny or b[1] > maxy:
            continue
        kept.append(f)
    return {'type': 'FeatureCollection', 'features': kept}


def _geom_bbox(g):
    def walk(coords):
        if not coords:
            return None
        if isinstance(coords[0], (int, float)):
            return coords[0], coords[1], coords[0], coords[1]
        boxes = [walk(c) for c in coords]
        boxes = [b for b in boxes if b is not None]
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
    return walk(g.get('coordinates'))


def round_coords(g, ndigits: int = 5):
    """Round every coordinate in-place. Reduces file size for web delivery."""
    def walk(c):
        if not c:
            return c
        if isinstance(c[0], (int, float)):
            return [round(c[0], ndigits), round(c[1], ndigits)]
        return [walk(x) for x in c]
    g['coordinates'] = walk(g['coordinates'])
    return g
