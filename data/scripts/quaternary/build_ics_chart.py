"""Build app/public/data/ics-chart.json from the official ICS chart data.

Source: i-c-stratigraphy/chart, release v2026-06.5 (commit 44d1043, 2026-06-29),
file chart.ttl, owl:versionInfo "2026-06", CC BY 4.0. This is the RDF the ICS
uses to generate the online International Chronostratigraphic Chart. Boundary
ages (time:hasBeginning / time:hasEnd -> inMYA), colours (schema:color) and
hierarchy (skos:broader) are copied from it unchanged.

Contract 4: eons, eras, periods, epochs, ages from 300 Ma to 0. Two chart ranks
are not in that list and are skipped: Sub-Period (Mississippian, Pennsylvanian)
and Super-Eon (Precambrian); an interval whose skos:broader is a skipped rank
gets the next ancestor as parent. Series that have no English prefLabel in
chart.ttl (Lower/Middle/Upper ...) are named from their IRI
("MiddleTriassic" -> "Middle Triassic").

parse_chart() is also imported by data/scripts/terrain/build_geology_pmtiles.py
so geology ages come from the same file.

The output is written to a temp file and renamed over ics-chart.json in one
step, because the site build reads it.
"""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from common import GENERATED

RELEASE = 'v2026-06.5'
CHART_URL = f'https://raw.githubusercontent.com/i-c-stratigraphy/chart/{RELEASE}/chart.ttl'
CHART_SHA256 = '0158959e8fdae2a8bdbb14ca3e424d2370362cd8dfc8af86e7be73c74368b355'
CHART_TTL = Path('E:/Projects/Dolomites/data/raw/ics-2026/chart-official/chart.ttl')
OUT = Path('E:/Projects/Dolomites/app/public/data/ics-chart.json')

RANK_TYPE = {'Eon': 'eon', 'Era': 'era', 'Period': 'period', 'Epoch': 'epoch', 'Age': 'age'}
MAX_MA = 300

# Values from research/geology/dolomites-geological-history.md (source 1c, ICS news post on v2026/06).
CROSS_CHECK = [('Base Ladinian', 'Ladinian', 241.464),
               ('Base Anisian', 'Anisian', 247.0),
               ('Base Olenekian', 'Olenekian', 250.8)]


def fetch_chart():
    if not CHART_TTL.exists():
        r = requests.get(CHART_URL, timeout=60)
        r.raise_for_status()
        CHART_TTL.parent.mkdir(parents=True, exist_ok=True)
        CHART_TTL.write_bytes(r.content)
    sha = hashlib.sha256(CHART_TTL.read_bytes()).hexdigest()
    if sha != CHART_SHA256:
        sys.exit(f'{CHART_TTL}: sha256 {sha} differs from pinned {CHART_SHA256}')


def _inmya(body, prop):
    node = re.search(prop + r'\s*\[(.*?)\]', body, re.S).group(1)
    return float(re.search(r'\w+:inMYA\s+([\d.]+)', node).group(1))


def parse_chart(path=CHART_TTL):
    """Return (owl:versionInfo, {IRI local name: interval}) for every ranked concept in chart.ttl."""
    text = path.read_text(encoding='utf-8')
    version = re.search(r'owl:versionInfo "([^"]+)"', text).group(1)
    chart = {}
    for m in re.finditer(r'^\w+:(\w+)\n(.*?)^\.$', text, re.M | re.S):
        key, body = m.groups()
        rank = re.search(r'gts:rank rank:([\w-]+)', body)
        if not rank:
            continue
        pref = re.search(r'skos:prefLabel\s+(.*?)\s;\n', body, re.S)
        labels = {lang: s for s, lang in re.findall(r'"([^"]+)"@([\w-]+)', pref.group(1))} if pref else {}
        broader = re.search(r'skos:broader \w+:(\w+)', body)
        chart[key] = {
            'name': labels.get('en') or re.sub(r'(?<=[a-z])(?=[A-Z0-9])', ' ', key),
            'rank': rank.group(1),
            'broader': broader.group(1) if broader else None,
            'start_ma': _inmya(body, 'time:hasBeginning'),
            'end_ma': _inmya(body, 'time:hasEnd'),
            'color': re.search(r'schema:color\s+"(#[0-9A-Fa-f]{6})"', body).group(1).upper(),
        }
    return version, chart


def replace_with_retry(tmp, dst, tries=10):
    """os.replace is atomic, but Windows refuses it while another process holds dst open."""
    for i in range(tries):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(1)


def main():
    fetch_chart()
    version, chart = parse_chart()

    def parent_of(key):
        p = chart[key]['broader']
        while p and chart[p]['rank'] not in RANK_TYPE:
            p = chart[p]['broader']
        return chart[p]['name'] if p else None

    intervals = [
        {'name': iv['name'], 'type': RANK_TYPE[iv['rank']], 'parent': parent_of(key),
         'start_ma': iv['start_ma'], 'end_ma': iv['end_ma'], 'color': iv['color']}
        for key, iv in chart.items()
        if iv['rank'] in RANK_TYPE and iv['end_ma'] < MAX_MA
    ]
    order = list(RANK_TYPE.values())
    intervals.sort(key=lambda i: (-i['start_ma'], i['end_ma'], order.index(i['type'])))
    by_name = {i['name']: i for i in intervals}
    if len(by_name) != len(intervals):
        sys.exit('duplicate interval names')

    skipped = sorted(iv['name'] for iv in chart.values() if iv['rank'] not in RANK_TYPE and iv['end_ma'] < MAX_MA)
    ages = sorted((i for i in intervals if i['type'] == 'age'), key=lambda i: -i['start_ma'])
    gaps = [f"{a['name']} ends at {a['end_ma']} Ma but {b['name']} begins at {b['start_ma']} Ma"
            for a, b in zip(ages, ages[1:]) if a['end_ma'] != b['start_ma']]
    outside = [f"{i['name']} ({i['start_ma']}-{i['end_ma']} Ma) extends beyond its parent {i['parent']}"
               for i in intervals if i['parent'] and (i['start_ma'] > by_name[i['parent']]['start_ma']
                                                      or i['end_ma'] < by_name[i['parent']]['end_ma'])]

    payload = {
        'version': version,
        'source_ref': 'ics-2026',
        'dataset_id': 'ics-2026',
        'label': 'interpreted',
        'attribution': (f'International Commission on Stratigraphy, International Chronostratigraphic Chart '
                        f'{version} (data release {RELEASE}, github.com/i-c-stratigraphy/chart), CC BY 4.0. '
                        'Cohen, K.M., Harper, D.A.T., Gibbard, P.L. & Car, N. (2025) The ICS International '
                        'Chronostratigraphic Chart this decade. Episodes 48: 105-115.'),
        'license': 'CC BY 4.0',
        'generated': GENERATED,
        'script': 'data/scripts/quaternary/build_ics_chart.py',
        'source': {'url': CHART_URL, 'release': RELEASE, 'sha256': CHART_SHA256,
                   'version_in_file': version},
        'notes': [
            'Boundary ages, colours and parents copied from chart.ttl without change.',
            f'Chart ranks outside contract 4 omitted: {", ".join(skipped)}; their children take the next ancestor as parent.',
            'Series without an English prefLabel in chart.ttl (Lower/Middle/Upper ...) are named from the chart IRI.',
        ] + [f'As published in the chart: {g}.' for g in gaps + outside],
        'cross_check': {
            'reference': 'research/geology/dolomites-geological-history.md (source 1c, ICS news post on v2026/06)',
            'boundaries': [{'name': label, 'research_ma': ma, 'source_ma': by_name[n]['start_ma'],
                            'match': by_name[n]['start_ma'] == ma} for label, n, ma in CROSS_CHECK],
        },
        'intervals': intervals,
    }
    tmp = OUT.with_name(OUT.name + '.tmp')
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    replace_with_retry(tmp, OUT)

    print('wrote', OUT, OUT.stat().st_size, 'bytes; chart version', version)
    print('  intervals by type:', {t: sum(1 for i in intervals if i['type'] == t) for t in order})
    for note in payload['notes']:
        print('  note:', note)
    for b in payload['cross_check']['boundaries']:
        print(f"  {b['name']:16}: research={b['research_ma']:>7} Ma  chart={b['source_ma']}  match={b['match']}")


if __name__ == '__main__':
    main()
