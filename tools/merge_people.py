"""Add batches of famous people to data/layers/<era-id>.json.

Usage: python3 tools/merge_people.py <dir>   (the dir holds <era-id>.json files, each a list of people)
Checks fields, coordinates and duplicates (by Chinese name or alias, across all eras), moves anyone filed under an era
their adult life misses, and prints what it drops or moves. Then lists everyone (old and new) in each further era that
holds at least 8 years of their adult life. People already in the layers are kept as they are.
`aliases_zh` (optional) lists other Chinese names the event texts use, each of 2+ characters; see tools/link_events.py.
`show` (optional) is the [from, to] span the map shows them in, for someone whose adult life without a birth year would
start before they mattered (a king who came to the throne as a child)."""
import glob, json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
FIELDS = {"general", "statesman", "thinker", "poet", "writer", "historian", "scientist", "physician", "engineer",
          "artist", "religious", "explorer", "scholar"}
KEYS = ["id", "name", "name_zh", "aliases_zh", "born", "died", "circa", "field", "place", "place_zh", "lat", "lon",
        "known_for", "known_for_zh", "works", "source", "show"]
eras = {e["id"]: e for e in json.load(open(P("data/eras.json")))["eras"]}
layers = {k: json.load(open(P(f"data/layers/{k}.json"))) for k in eras}
seen = {n for L in layers.values() for p in L.get("people", []) for n in [p["name_zh"], *p.get("aliases_zh", [])]}
ids = {p["id"] for L in layers.values() for p in L.get("people", [])}

def overlap(p, era):
    """Years of the person's adult life (from 20, or the 40 years before death) inside the era."""
    if p.get("show"): a, b = p["show"]
    elif p.get("died") is None: return -1
    else: a, b = (p["born"] + 20 if p.get("born") is not None else p["died"] - 40), p["died"]
    return min(b, era["end"]) - max(a, era["start"])

for path in sorted(glob.glob(os.path.join(sys.argv[1], "*.json"))):
    k = os.path.basename(path)[:-5]
    if k not in eras:
        continue
    era, added = eras[k], 0
    for p in json.load(open(path)):
        why = None
        if p.get("field") not in FIELDS: why = f"field {p.get('field')}"
        elif p.get("died") is None: why = "no death year"
        elif p.get("born") is not None and p["born"] > p["died"]: why = "born after died"
        elif not (70 <= p.get("lon", 0) <= 135 and 15 <= p.get("lat", 0) <= 55): why = "coordinates"
        elif any(not isinstance(a, str) or len(a) < 2 for a in p.get("aliases_zh") or []): why = "aliases_zh"
        elif p["name_zh"] in seen: why = "duplicate"
        if why:
            print(f"  drop {k} {p.get('name_zh')}: {why}")
            continue
        q = {key: p.get(key) for key in KEYS}
        q["works"] = q["works"] or []
        for key in ("aliases_zh", "show"):
            if not q[key]: del q[key]
        while q["id"] in ids: q["id"] += "-2"
        # Filed under the wrong era (life outside it): move to the era holding most of their adult life.
        home = k if overlap(q, era) > 0 else max(eras, key=lambda e: overlap(q, eras[e]))
        if overlap(q, eras[home]) <= 0:
            print(f"  drop {k} {q['name_zh']}: outside every era"); continue
        if home != k: print(f"  move {q['name_zh']}: {k} -> {home}")
        seen.update([q["name_zh"], *q.get("aliases_zh", [])]); ids.add(q["id"])
        layers[home].setdefault("people", []).append(q)
        added += 1
    print(f"{k}: +{added}")

# Someone whose adult life spans two periods (曹操, 李煜...) is listed in each, so they show on either side of the break.
copies = 0
for k, L in layers.items():
    for p in list(L.get("people", [])):
        for e in eras:
            if e != k and overlap(p, eras[e]) >= 8 and all(q["name_zh"] != p["name_zh"] for q in layers[e].get("people", [])):
                layers[e].setdefault("people", []).append(dict(p)); copies += 1
for k, L in layers.items():
    json.dump(L, open(P(f"data/layers/{k}.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print(k, len(L.get("people", [])))
print(copies, "copies into neighbouring periods")
