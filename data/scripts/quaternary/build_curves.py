"""Build curve JSON files under app/public/data/curves/ from the raw sources.

Contract 3 (docs/04-data-contracts.md): each file has
{ "dataset_id", "label", "x", "unit", "series": [{name, values:[[x,y],...]}, ...] }
plus "source_ref", "attribution" (with "(modified: ...)" where values are derived), "license" and "license_url".
sorted by x descending (oldest first).
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import GENERATED, REF_LAT, REF_LON

OUT_DIR = Path('E:/Projects/Dolomites/app/public/data/curves')
RAW_DIR = Path('E:/Projects/Dolomites/data/raw')
OUT_DIR.mkdir(parents=True, exist_ok=True)


def sort_desc(series_list):
    """Sort every series [[x,y]...] by x descending (oldest first)."""
    for s in series_list:
        s['values'].sort(key=lambda p: p[0], reverse=True)


# ---------------------------------------------------------------------------
# PhanDA GMST + CO2 percentiles (Judd et al. 2024). Reference age is AverageAge.
# ---------------------------------------------------------------------------

def build_phanda():
    src = RAW_DIR / 'phanda-2024' / 'PhanDA_GMSTandCO2_percentiles.csv'
    rows = list(csv.DictReader(src.open('r', encoding='utf-8-sig')))
    gmst_series = {p: [] for p in ['05', '16', '50', '84', '95']}
    co2_series  = {p: [] for p in ['05', '16', '50', '84', '95']}
    for r in rows:
        try:
            age = float(r['AverageAge'])
        except (KeyError, ValueError):
            continue
        for p in gmst_series:
            v = r.get(f'GMST_{p}')
            if v not in (None, '', 'NaN'):
                gmst_series[p].append([age, float(v)])
            v = r.get(f'CO2_{p}')
            if v not in (None, '', 'NaN'):
                co2_series[p].append([age, float(v)])

    def dump(kind, series, unit, label):
        payload = {
            'dataset_id': 'phanda-judd-2024',
            'label': 'modeled',
            'source_ref': 'judd-2024',
            'attribution': ('Judd E.J., Tierney J.E., Lunt D.J., Montañez I.P., '
                            'Huber B.T., Wing S.L., Valdes P.J. (2024). A 485-million-year '
                            "history of Earth's surface temperature. Science 385. "
                            'Percentiles CSV: github.com/EJJudd/PhanDA. CC BY 4.0 '
                            '(modified: GMST and CO2 percentile columns extracted and sorted by age).'),
            'license': 'CC BY 4.0',
            'license_url': 'https://creativecommons.org/licenses/by/4.0/',
            'generated': GENERATED,
            'script': 'data/scripts/quaternary/build_curves.py',
            'x': 'ma',
            'unit': unit,
            'notes': ('Age is the mid-stage AverageAge from the source CSV. '
                      'Percentiles are of the ensemble posterior (p05, p16, p50, p84, p95).'),
            'series': [
                {'name': f'{kind}_p{p}', 'values': v}
                for p, v in series.items()
            ],
        }
        sort_desc(payload['series'])
        path = OUT_DIR / f'phanda-{label}.json'
        path.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')
        print('wrote', path, path.stat().st_size, 'bytes')

    dump('gmst', gmst_series, 'degC', 'gmst')
    dump('co2',  co2_series,  'ppm',  'co2')


# ---------------------------------------------------------------------------
# CENOGRID (Westerhold et al. 2020) - decimate to 10 kyr bins on the age axis.
# ---------------------------------------------------------------------------

def build_cenogrid():
    src = RAW_DIR / 'cenogrid-2020' / 'PANGAEA.917660.tab'
    text = src.read_text(encoding='utf-8')
    idx = text.find('*/')
    body = text[idx + 2:].strip().splitlines()
    header = body[0].split('\t')
    # Column 4 = 'Tuned time [Ma]'; column 15 = benthic d18O CorrAdjusted (used
    # in the splice figures of Westerhold et al. 2020); column 18 = LOESS-10
    # smoothed version. See PANGAEA.917660 header.
    icol_age = header.index('Tuned time [Ma]')
    for i, h in enumerate(header):
        if 'δ18O' in h and 'CorrAdjusted' in h:
            icol_d18o = i
            break
    else:
        raise SystemExit('CorrAdjusted d18O column not found in ' + str(src))
    # Bin to 10 kyr on the tuned Ma axis
    bins = {}
    for line in body[1:]:
        parts = line.split('\t')
        if len(parts) <= max(icol_age, icol_d18o):
            continue
        try:
            age_ma = float(parts[icol_age])
            d = float(parts[icol_d18o])
        except ValueError:
            continue
        bin_ma = round(age_ma * 100) / 100.0  # 10 kyr = 0.01 Ma
        bins.setdefault(bin_ma, []).append(d)
    d18o = [[b, round(sum(v) / len(v), 4)] for b, v in bins.items()]
    d18o.sort(key=lambda p: p[0], reverse=True)
    payload = {
        'dataset_id': 'cenogrid-westerhold-2020',
        'label': 'observed',
        'source_ref': 'westerhold-2020',
        'attribution': ('Westerhold T., Marwan N., Drury A.J. et al. (2020). An astronomically '
                        "dated record of Earth's climate and its predictability over the last "
                        '66 million years. Science 369, 1383-1387. Data: PANGAEA 917660, CC BY 4.0 '
                        '(modified: benthic d18O decimated to 10-kyr bin means).'),
        'license': 'CC BY 4.0',
        'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'generated': GENERATED,
        'script': 'data/scripts/quaternary/build_curves.py',
        'x': 'ma',
        'unit': 'permille_PDB',
        'notes': ('Benthic foraminifer delta 18O reference splice, decimated to 10-kyr '
                  'bins (arithmetic mean per bin). Ages are on the tuned time scale.'),
        'series': [{'name': 'benthic_d18o_mean_10ka', 'values': d18o}],
    }
    path = OUT_DIR / 'cenogrid-d18o.json'
    path.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')
    print('wrote', path, path.stat().st_size, 'bytes')


# ---------------------------------------------------------------------------
# Spratt & Lisiecki (2016) sea-level stack from NOAA text file.
# ---------------------------------------------------------------------------

def build_spratt():
    src = RAW_DIR / 'spratt-lisiecki-2016' / 'spratt2016.txt'
    text = src.read_text(encoding='utf-8')
    lines = text.splitlines()
    # find header line
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith('age_calkaBP'):
            header_idx = i
            break
    header = lines[header_idx].split('\t')
    icol = {name: i for i, name in enumerate([h.strip() for h in header])}
    short = []
    short_lo = []
    short_up = []
    long_ = []
    long_lo = []
    long_up = []
    for ln in lines[header_idx + 1:]:
        parts = ln.split('\t')
        if len(parts) < 9:
            continue
        try:
            age = float(parts[icol['age_calkaBP']])
        except ValueError:
            continue

        def get(col):
            v = parts[icol[col]].strip()
            if v in ('', 'NaN'):
                return None
            return float(v)
        s = get('SeaLev_shortPC1'); slo = get('SeaLev_shortPC1_err_lo'); sup = get('SeaLev_shortPC1_err_up')
        l = get('SeaLev_longPC1');  llo = get('SeaLev_longPC1_err_lo');  lup = get('SeaLev_longPC1_err_up')
        if s is not None:  short.append([age, s]);   short_lo.append([age, slo]);  short_up.append([age, sup])
        if l is not None:  long_.append([age, l]);   long_lo.append([age, llo]);   long_up.append([age, lup])
    payload = {
        'dataset_id': 'spratt-lisiecki-2016',
        'label': 'modeled',
        'source_ref': 'spratt-lisiecki-2016',
        'attribution': ('Spratt R.M., Lisiecki L.E. (2016). A Late Pleistocene sea level '
                        'stack. Climate of the Past 12, 1079-1092. NOAA dataset DOI '
                        '10.25921/rd66-5820. NOAA NCEI Paleoclimatology '
                        '(modified: stack and 95% bound columns extracted and sorted by age).'),
        'license': 'US Government / NOAA - open (attribution requested)',
        'license_url': 'https://www.ncei.noaa.gov/access/paleo-search/study/19982',
        'generated': GENERATED,
        'script': 'data/scripts/quaternary/build_curves.py',
        'x': 'ka',
        'unit': 'm_above_present',
        'notes': ('Scaled first principal component of seven sea-level reconstructions '
                  '(short stack: 0-430 ka) and five reconstructions (long stack: '
                  '0-798 ka). 95% CI (lo/up) from bootstrap.'),
        'series': [
            {'name': 'sealev_short_pc1',      'values': short},
            {'name': 'sealev_short_pc1_lo95', 'values': short_lo},
            {'name': 'sealev_short_pc1_up95', 'values': short_up},
            {'name': 'sealev_long_pc1',       'values': long_},
            {'name': 'sealev_long_pc1_lo95',  'values': long_lo},
            {'name': 'sealev_long_pc1_up95',  'values': long_up},
        ],
    }
    sort_desc(payload['series'])
    path = OUT_DIR / 'spratt-lisiecki-sealevel.json'
    path.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')
    print('wrote', path, path.stat().st_size, 'bytes')


# ---------------------------------------------------------------------------
# ALPS 2017 uplift: single point + uncertainty at (46.5N, 11.8E).
# ---------------------------------------------------------------------------

def build_uplift():
    src = RAW_DIR / 'alps2017-uplift' / 'ALPS2017_DEF_VT.GRD'
    data = src.read_bytes().decode('latin1')
    rows = []
    for ln in data.splitlines():
        s = ln.strip()
        if not s or not s[0].isdigit():
            continue
        parts = s.split()
        if len(parts) < 4:
            continue
        try:
            lon = float(parts[0]); lat = float(parts[1])
            vz  = float(parts[2]); uz  = float(parts[3])
        except ValueError:
            continue
        rows.append((lon, lat, vz, uz))
    # find nearest grid cell to (REF_LAT, REF_LON)
    best = min(rows, key=lambda r: (r[0] - REF_LON) ** 2 + (r[1] - REF_LAT) ** 2)
    lon, lat, vz, uz = best
    # dataset resolution 0.3 deg lon x 0.2 deg lat
    payload = {
        'dataset_id': 'alps2017-uplift',
        'label': 'modeled',
        'source_ref': 'sanchez-2018',
        'attribution': ('Sánchez L., Völksen Ch., Sokolov A., Arenz H., Seitz F. (2018). '
                        'Present-day surface deformation of the Alpine region inferred from '
                        'geodetic techniques. Earth System Science Data 10, 1503-1526. '
                        'Data: PANGAEA 886889, file ALPS2017_DEF_VT.GRD, CC BY 3.0 '
                        '(modified: vertical velocity and its uncertainty at the grid cell nearest the '
                        'reference point, converted from m/yr to mm/yr).'),
        'license': 'CC BY 3.0',
        'license_url': 'https://creativecommons.org/licenses/by/3.0/',
        'generated': GENERATED,
        'script': 'data/scripts/quaternary/build_curves.py',
        'x': 'ma',
        'unit': 'mm_per_yr',
        'reference_point': {'lat': REF_LAT, 'lon': REF_LON},
        'grid_cell': {'lat': lat, 'lon': lon, 'nominal_size_deg': [0.3, 0.2]},
        'notes': ('Vertical velocity at the nearest cell of the ALPS2017 25 km x 25 km '
                  'gridded deformation model. Positive = uplift. The pointwise value comes '
                  'from a geodetic least-squares collocation of ~300 continuous GNSS stations '
                  'over 12.4 years (2005-2016), reference frame IGb08 epoch 2010.0. '
                  'Uncertainty is the standard uncertainty of the vertical component '
                  '(m/yr in source, converted to mm/yr here).'),
        'series': [
            {'name': 'vertical_velocity_mm_per_yr',           'values': [[0.0, round(vz * 1000, 3)]]},
            {'name': 'vertical_velocity_uncertainty_mm_per_yr', 'values': [[0.0, round(uz * 1000, 3)]]},
        ],
    }
    path = OUT_DIR / 'alps2017-uplift.json'
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('wrote', path, path.stat().st_size, 'bytes')
    print(f'  cell ({lon}°E, {lat}°N)  vz={vz*1000:+.3f} mm/yr  ±{uz*1000:.3f} mm/yr')


if __name__ == '__main__':
    build_phanda()
    build_cenogrid()
    build_spratt()
    build_uplift()
