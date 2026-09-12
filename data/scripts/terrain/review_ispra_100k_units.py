"""
Per-unit review of the ISPRA Carta Geologica d'Italia 1:100.000 (INSPIRE GML) units that intersect the terrain bbox.
Writes sources."ispra-geologia-100k-inspire".units, .rules and .review into geology_age_mapping.json; the build colours
an ISPRA polygon only as this review decided. Re-run it when the ISPRA data, the chart or the South Tyrol / Trentino
legends change, then rebuild.

Interpreter: E:/Projects/Dolomites/.venv/Scripts/python.exe. Reads the ISPRA GML through geology_gapfill_readers.py and,
for check C4, the build intermediates data/processed/terrain/geology-dolomites-{features,props}.pkl (only their
South Tyrol, Trentino and Veneto polygons are used, so a previous build of any source set works).

Why: in the harmonised INSPIRE dataset the GeologicEvent of a unit is not always its formation (for metamorphic units
it is the metamorphism, e.g. orthogneiss 'Cenozoic'), and the join of unit name, legend description and event has
visible errors (e.g. 'oliviniti' described as 'Filladi quarzifere'; 'dolomia dello sciliar' described as
'Norico. - Dolomia principale').

Checks per unit (flags):
  C1 lithology  the rock families named by the unit name and by its description are disjoint
  C2 wording    fewer than half of the significant words of the name occur in the description (names of two or more
                such words), or none of them (one-word names)
  C3 stated age the description opens with an age ('Norico. - ...', 'Lias. - ...', 'PERMIANO INF.: ...') that does not
                overlap the unit's own age
  C4 detailed   the unit's age is pre-Quaternary and, of >= C4_MIN_POINTS random points inside its polygons that fall on
     maps       dated pre-Quaternary units of the South Tyrol, Trentino or Veneto maps, fewer than C4_MAX_SHARE have an age
                range overlapping ISPRA's
Decision (rule), in this order:
  no_geological_age              the name is glaciers, snowfields, water or anthropic ground -> null
  contradiction_join             a flag, and the name matches exactly one South Tyrol / Trentino formation (same
                                 geographic name key, one map symbol) -> legend_join with that formation's age
                                 (join_from 'name'); or a flag other than C1/C2, a generic (non-formation) name, and a
                                 description that names exactly one formation, inline or in parentheses, matching one
                                 map symbol -> legend_join (join_from 'description', e.g. 'arenarie quarzose' described
                                 as '(Arenarie di Val Gardena)'); never when the description names several formations
  contradiction_quaternary_kept  only C1/C2, name and description both name Quaternary deposits and the age is
                                 Quaternary -> ISPRA age kept (the mismatch does not change the age)
  contradiction_null             any other flag -> null
  event_not_formation            eventProcess metamorphicProcess, faulting or unknown -> null
  age_unmapped                   an age name without a chart interval (e.g. 'Unknown') -> null
  source                         ISPRA's olderNamedAge / youngerNamedAge

Usage: review_ispra_100k_units.py [--dry-run] [--list N]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pickle
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import box
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_geology_pmtiles as B  # noqa: E402
import geology_gapfill_readers as GF  # noqa: E402

C4_MIN_POINTS = 30
C4_MAX_SHARE = 0.10
QUATERNARY_START = 2.58

LITH = {  # word stem in Italian -> rock family
    "fillad": "schist", "micascist": "schist", "calcescist": "schist", "scist": "schist", "ortogneis": "gneiss", "paragneis": "gneiss",
    "gneis": "gneiss", "anfibol": "amphibolite", "marm": "marble", "quarzit": "quartzite", "granit": "granitoid", "tonalit": "granitoid",
    "granodior": "granitoid", "diorit": "granitoid", "pegmatit": "granitoid", "aplit": "granitoid", "olivin": "ultramafic",
    "serpentin": "ultramafic", "porfid": "volcanic", "porfir": "volcanic", "riolit": "volcanic", "andesit": "volcanic", "basalt": "volcanic",
    "tuf": "volcanic", "ignimbr": "volcanic", "lav": "volcanic", "conglomer": "clastic", "arenar": "clastic", "brecc": "clastic",
    "argill": "clastic", "flysch": "clastic", "dolomi": "carbonate", "calcar": "carbonate", "marn": "carbonate", "gess": "evaporite",
    "milonit": "fault", "moren": "quaternary", "alluvi": "quaternary", "detrit": "quaternary", "coni": "quaternary", "conoid": "quaternary",
    "deiezion": "quaternary", "frana": "quaternary", "frane": "quaternary", "scoscendim": "quaternary", "torb": "quaternary",
    "lacustr": "quaternary", "palud": "quaternary", "fluvioglacial": "quaternary", "glacial": "quaternary", "falda": "quaternary",
}
STOP = set("a al alla allo ai agli alle con d da dal dalla dei degli del della delle dello di e ed fra i il in la le lo o per su tra "
           "talora spesso generalmente localmente prevalenti prevalentemente subordinati subordinate grigi grigie grigio chiari chiare "
           "scuri scure rossi rosse bianchi bianche verdi neri nere minuti minute medio media sottili spessi indistinti indistinte "
           "varie vari tipo loro".split())
AGE_WORDS = {
    "olocene": "Holocene", "attuale": "Holocene", "attuali": "Holocene", "pleistocene": "Pleistocene", "quaternario": "Quaternary",
    "pliocene": "Pliocene", "miocene": "Miocene", "oligocene": "Oligocene", "eocene": "Eocene", "paleocene": "Paleocene",
    "cretaceo": "Cretaceous", "cretacico": "Cretaceous", "giurassico": "Jurassic", "giura": "Jurassic", "lias": "Lower Jurassic",
    "dogger": "Middle Jurassic", "malm": "Upper Jurassic", "trias": "Triassic", "triassico": "Triassic", "retico": "Rhaetian",
    "norico": "Norian", "carnico": "Carnian", "ladinico": "Ladinian", "anisico": "Anisian", "scitico": "Lower Triassic",
    "werfeniano": "Lower Triassic", "permiano": "Permian", "permico": "Permian", "carbonifero": "Carboniferous", "devoniano": "Devonian",
    "siluriano": "Silurian", "ordoviciano": "Ordovician", "cambriano": "Cambrian", "paleozoico": "Paleozoic", "mesozoico": "Mesozoic",
    "cenozoico": "Cenozoic", "terziario": "Cenozoic", "precambriano": "Precambrian", "toarciano": "Toarcian", "senoniano": "Upper Cretaceous",
    "turoniano": "Turonian", "cenomaniano": "Cenomanian", "albiano": "Albian", "aptiano": "Aptian", "neocomiano": "Lower Cretaceous",
    "titonico": "Tithonian", "titoniano": "Tithonian",
}
AGE_QUAL = set("inf inferiore sup superiore medio media basso alto e ed p pp in genere generale".split())
TYPE_WORDS = set("formazione formazioni dolomia dolomie calcare calcari arenaria arenarie conglomerato conglomerati gruppo strati "
                 "membro membri marna marne scisti scisto filladi fillade quarzifera quarzifere quarzosa quarzose gneiss ortogneiss "
                 "paragneiss porfiroide porfiroidi unita complesso breccia brecce calcarenite calcareniti".split())
NAME_STOP = STOP | set("val valle monte m auct".split())
ALIAS = {"schlern": "sciliar"}  # German / Italian name of the same place (judgement: Dolomia dello Schlern = Sciliar)
NULL_NAME = re.compile(r"\b(ghiacciai|ghiacciaio|nevai|nevati|laghi|lago|acque|bacini|riporti|discariche|antropic)")
# a join needs a formation-style name: a unit word followed by a preposition and a proper name ('arenarie di val gardena',
# 'formazione a bellerophon', 'ortogneiss del gran veneziano') or 'rosso ammonitico'; lithological descriptions
# ('micascisti sericitici', 'dolomie e calcari') are never joined
FORMATION_NAME = re.compile(r"\b(formazione|formazioni|dolomia|dolomie|calcare|calcari|arenaria|arenarie|conglomerato|gruppo|strati|marne|marna|"
                            r"argillite|argilliti|carniola|fillade|filladi|scisti|ortogneiss|gneiss|granito|tonalite|granodiorite|porfiroide|porfiroidi)"
                            r"\s+(di|del|della|dello|dei|degli|delle|dell|a|ad)\b|\brosso ammonitico\b")


def ascii_lower(s: str | None) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def stems(s: str | None) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]+", ascii_lower(s)) if len(w) >= 4 and w not in STOP}


def families(s: str | None) -> set[str]:
    words = re.findall(r"[a-z]+", ascii_lower(s))
    return {fam for w in words for stem, fam in LITH.items() if w.startswith(stem)}


def leading_ages(desc: str | None) -> list[str]:
    s = ascii_lower(desc)
    m = re.match(r"^\s*([a-z .,]{3,60}?)\s*(?:\.\s*-|:|\.\s|\s-\s)", s)
    if not m:
        return []
    toks = re.findall(r"[a-z]+", m.group(1))
    if not toks or any(t not in AGE_WORDS and t not in AGE_QUAL for t in toks):
        return []
    return [AGE_WORDS[t] for t in toks if t in AGE_WORDS]


FORMATION_PHRASE = re.compile(
    r"\b(?:formazione|formazioni|dolomia|dolomie|calcare|calcari|arenaria|arenarie|conglomerato|gruppo|strati|marne|marna|argillite|"
    r"argilliti|carniola|fillade|filladi|scisti|ortogneiss|gneiss|granito|tonalite|granodiorite|porfiroide|porfiroidi)\s+"
    r"(?:di|del|della|dello|dei|degli|delle|dell|a|ad)\b[^.,;:()\[\]=\-]*|\brosso ammonitico\b[^.,;:()\[\]=\-]*")


def description_formation(desc: str | None, cand: dict, name_is_formation: bool, flags: list[str]):
    """A formation named in the description (inline or in parentheses) that may date a unit with a generic name.
    -> ((phrase, key, matches) or None, reason). Refused when the name is itself a formation name, when name and
    description contradict each other (C1/C2), when the description names more than one formation (including ones
    not in the legends), or when the formation matches no or several map symbols."""
    if name_is_formation:
        return None, "name is a formation name"
    if any(f.startswith(("C1", "C2")) for f in flags):
        return None, "description contradicts the name"
    found, unmatched = {}, []
    for m in FORMATION_PHRASE.finditer(ascii_lower(desc)):
        toks = m.group(0).split()
        hit = None
        for n in range(len(toks), 1, -1):  # longest leading part of the phrase that is a legend formation
            k = formation_key(" ".join(toks[:n]))
            if k and k in cand:
                hit = (" ".join(toks[:n]), k, cand[k])
                break
        if hit:
            found.setdefault(k, hit)
        else:
            unmatched.append(m.group(0).strip())
    if not found:
        return None, "no legend formation named"
    if len(found) > 1 or unmatched:
        return None, f"description names more than one formation: {sorted(found) + unmatched}"
    phrase, k, matches = next(iter(found.values()))
    if len({m[2] for m in matches}) != 1:
        return None, f"'{phrase}' matches several map symbols"
    return (phrase, k, matches), None


def formation_key(name: str | None) -> str:
    s = re.sub(r"\([^)]*\)", " ", ascii_lower(name))
    return " ".join(ALIAS.get(t, t) for t in re.findall(r"[a-z]+", s) if t not in TYPE_WORDS and t not in NAME_STOP and len(t) > 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print, do not write the mapping")
    ap.add_argument("--list", type=int, default=60, help="print this many flagged units")
    args = ap.parse_args()
    chart_version, by_name = B.load_chart()
    mapping = json.loads(B.MAPPING.read_text(encoding="utf-8"))
    ctx = B.AgeContext(mapping, by_name)
    cfg = mapping["sources"][B.ISPRA]

    def chart_name(tail):
        n = B.ispra_age_name(tail, cfg)
        return n if (n is None or n in by_name) else False

    d = GF.read_ispra(B.BBOX_LL)
    bb = box(*B.BBOX_LL)
    feats = [f for f in d["features"] if f["geom"].intersects(bb)]
    used = collections.Counter(f["unit"] for f in feats)
    units = d["units"]
    print(f"{len(used)} ISPRA units with {len(feats)} polygons in the bbox")

    # legend candidates: formation-level South Tyrol and Trentino units with a full age
    ctx.ensure_bz_units()
    cand = collections.defaultdict(set)  # key -> {(authority, id, sigla)}
    for sigla, names in ctx.bz_names.items():
        pairs = ctx.bz_units.get(sigla, {})
        if not pairs or any(not (o and y and ctx.bz_terms[o]["chart"] and ctx.bz_terms[y]["chart"]) for o, y in pairs):
            continue
        for nm in names:
            if re.search(r"\b(membro|membri|facies|litofacies)\b", ascii_lower(nm)):
                continue
            k = formation_key(nm)
            if k:
                cand[k].add(("bz-carg-attributes", sigla, sigla))
    for key, r in ctx.pat["unit_ages"]["units"].items():
        if not r["age"] or " - " in r["name"]:
            continue
        t = ctx.pat_terms.get(B.norm_age(r["age"]))
        if not (t and t["o"] and t["y"]):
            continue
        k = formation_key(r["name"])
        if k:
            cand[k].add(("pat-unit-legend", key, r["sigla"]))

    # C4 inputs: dated pre-Quaternary units of the detailed maps
    c4 = {}
    if B.FEATURES_PKL.exists() and B.PROPS_PKL.exists():
        F = B.load_pickle(B.FEATURES_PKL)
        props = B.load_pickle(B.PROPS_PKL)
        keep = [i for i, p in enumerate(props) if p["source"] in (B.BZ, B.PAT, B.VEN) and p["age_min_ma"] is not None
                and p["age_max_ma"] is not None and p["age_min_ma"] >= QUATERNARY_START]
        geoms = shapely.from_wkb([F["wkb"][i] for i in keep])
        det = [(props[i]["age_min_ma"], props[i]["age_max_ma"]) for i in keep]
        tree = STRtree(geoms)
        rng = np.random.default_rng(20260912)
        pts = collections.defaultdict(list)
        for f in feats:
            g = f["geom"].intersection(bb)
            if g.is_empty:
                continue
            minx, miny, maxx, maxy = g.bounds
            n = int(min(200, max(3, g.area / 2e-6)))
            xs, ys = rng.uniform(minx, maxx, n * 3), rng.uniform(miny, maxy, n * 3)
            inside = shapely.contains_xy(g, xs, ys)
            pts[f["unit"]].extend(list(zip(xs[inside], ys[inside]))[:n])
        for uid, pp in pts.items():
            if not pp:
                continue
            _, gi = tree.query(shapely.points(np.array(pp)), predicate="within")
            c4[uid] = [det[k] for k in gi]
        print(f"C4: detailed-map ages sampled for {len(c4)} units")
    else:
        print("C4 skipped: build intermediates missing")

    rows, counts = {}, collections.Counter()
    for uid in used:
        u = units[uid]
        on, yn = chart_name(u["older"]), chart_name(u["younger"])
        o = by_name[on] if on else None
        y = by_name[yn] if yn else None
        flags = []
        fn, fd = families(u["name"]), families(u["description"])
        if fn and fd and not (fn & fd):
            flags.append(f"C1 lithology: name {sorted(fn)} vs description {sorted(fd)}")
        sn, sd = stems(u["name"]), stems(u["description"])
        if sn and u["description"]:
            share = len(sn & sd) / len(sn)
            if (len(sn) >= 2 and share < 0.5) or share == 0:
                flags.append(f"C2 wording: {share:.0%} of the name's words in the description")
        ages = leading_ages(u["description"])
        if ages and o and y and not any(by_name[a]["start_ma"] > y["end_ma"] and by_name[a]["end_ma"] < o["start_ma"] for a in ages):
            flags.append(f"C3 stated age: description opens with {ages}, unit age {u['older']}-{u['younger']}")
        if o and y and y["end_ma"] >= QUATERNARY_START and len(c4.get(uid, [])) >= C4_MIN_POINTS:
            pts_ = c4[uid]
            agree = sum(1 for amin, amax in pts_ if amax > y["end_ma"] and amin < o["start_ma"])
            if agree / len(pts_) < C4_MAX_SHARE:
                flags.append(f"C4 detailed maps: {agree} of {len(pts_)} points on dated South Tyrol/Trentino/Veneto units overlap {u['older']}-{u['younger']}")
        row = {"name": u["name"], "description": (u["description"] or "")[:300] or None, "event_process": u["event_process"],
               "ispra_older": u["older"], "ispra_younger": u["younger"], "polygons_in_bbox": used[uid], "flags": flags}
        key = formation_key(u["name"])
        matches = cand.get(key, set()) if key else set()
        siglas = {m[2] for m in matches}
        name_is_formation = bool(FORMATION_NAME.search(ascii_lower(u["name"])))
        desc_hit, desc_why = None, None
        if flags and not (len(siglas) == 1 and name_is_formation):
            desc_hit, desc_why = description_formation(u["description"], cand, name_is_formation, flags)

        def join(formation, matches_, key_, source, note):
            evidence = []
            for auth, ident, _sigla in sorted(matches_):
                ev = {"formation": formation, "authority": auth}
                ev.update({"sigla": ident} if auth == "bz-carg-attributes" else {"unit": ident})
                evidence.append(ev)
            res = [ctx.resolve(e, f"ISPRA {uid}") for e in evidence]
            old = max((r["older"] for r in res), key=lambda iv: (iv["start_ma"], -(iv["start_ma"] - iv["end_ma"])))
            yng = min((r["younger"] for r in res), key=lambda iv: (iv["end_ma"], iv["start_ma"] - iv["end_ma"]))
            row.update(decision="legend_join", rule="contradiction_join", age_basis="legend_join", join_from=source,
                       older=old["name"], younger=yng["name"], evidence=evidence, note=note)

        if NULL_NAME.search(ascii_lower(u["name"])):
            row.update(decision="null", rule="no_geological_age", older=None, younger=None)
        elif flags and len(siglas) == 1 and name_is_formation:
            join(u["name"], matches, key, "name", f"Formation name key '{key}' matches map symbol {next(iter(siglas))} only.")
        elif desc_hit:
            phrase, dkey, dmatches = desc_hit
            join(phrase, dmatches, dkey, "description",
                 f"The name is not a formation name; the description names one formation, '{phrase}' (key '{dkey}'), "
                 f"which matches map symbol {next(iter({m[2] for m in dmatches}))} only.")
        elif (flags and all(f.startswith(("C1", "C2")) for f in flags) and fn <= {"quaternary"} and fd <= {"quaternary"}
              and (fn or fd) and o and y and o["start_ma"] <= QUATERNARY_START + 1e-9):
            row.update(decision="source", rule="contradiction_quaternary_kept", older=on, younger=yn)
        elif flags:
            row.update(decision="null", rule="contradiction_null", older=None, younger=None)
            if len(siglas) > 1:
                row["note"] = f"Name key '{key}' matches several map symbols {sorted(siglas)}; no join."
        elif cfg["event_process"].get(u["event_process"]) != "formation":
            if u["event_process"] not in cfg["event_process"]:
                sys.exit(f"event process {u['event_process']!r} of {uid} is not in the mapping")
            row.update(decision="null", rule="event_not_formation", older=None, younger=None)
        elif on is False or yn is False or o is None or y is None:
            row.update(decision="null", rule="age_unmapped", older=None, younger=None)
        else:
            if o["start_ma"] < y["start_ma"]:
                on, yn = yn, on
            row.update(decision="source", rule="source", older=on, younger=yn)
        rows[uid] = row
        counts[row["rule"]] += 1

    cfg["units"] = dict(sorted(rows.items(), key=lambda kv: int(kv[0].split("_")[1])))
    cfg["rules"] = [
        "One decision per GeologicUnit that intersects the terrain bbox, written by data/scripts/terrain/review_ispra_100k_units.py (see its docstring for checks C1-C4 and the decision order).",
        "Ages are used only for formation events (event_process 'formation'); metamorphicProcess, faulting and unknown events give null, because their age is the metamorphism or deformation (e.g. orthogneiss 'Cenozoic').",
        "Units whose name, description and age contradict each other (C1-C3) or whose age disagrees with the detailed South Tyrol/Trentino/Veneto maps where both exist (C4) are left uncoloured, unless the name matches exactly one formation of the South Tyrol / Trentino legends (legend_join with that age, join_from 'name'), or the name is generic and the description names exactly one formation (inline or in parentheses) that matches exactly one map symbol, with no C1/C2 contradiction between name and description (legend_join, join_from 'description'), or both name and description are Quaternary deposits with a Quaternary age (ISPRA age kept).",
        "Check C4 reads the ages of the detailed maps from the previous build, so its flags can change when those ages change (e.g. after the Veneto legend joins of 2026-09-12).",
        "The unit name shown (unit_name) is ISPRA's GeologicUnit name even where it contradicts the description; the lithology property lists the INSPIRE lithology terms, which follow the description.",
    ]
    cfg["review"] = {
        "script": "data/scripts/terrain/review_ispra_100k_units.py", "generated": date.today().isoformat(), "chart": chart_version,
        "units_in_bbox": len(used), "counts": dict(counts.most_common()),
        "thresholds": {"C4_min_points": C4_MIN_POINTS, "C4_max_share": C4_MAX_SHARE},
        "name_alias": ALIAS,
    }
    print(json.dumps(cfg["review"]["counts"], indent=1))
    flagged = sorted((r for r in rows.items() if r[1]["flags"]), key=lambda kv: -kv[1]["polygons_in_bbox"])
    for uid, r in flagged[:args.list]:
        print(f"{uid:8s} {r['polygons_in_bbox']:5d} {r['rule']:30s} {r['ispra_older']}-{r['ispra_younger']} | {r['name']} | {(r['description'] or '')[:70]} | "
              f"{r.get('older')}-{r.get('younger')} | {' ; '.join(r['flags'])}")
    if not args.dry_run:
        tmp = B.MAPPING.with_name(B.MAPPING.name + ".tmp")
        tmp.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, B.MAPPING)
        print(f"wrote {B.MAPPING}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
