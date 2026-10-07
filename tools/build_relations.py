"""人物关系网: check and pack the ties between people (data/relations.json).

    python3 tools/build_relations.py [new-batch.json ...]

data/relations.json holds `links` (who taught, served, fought or wrote to whom; AI-drafted) and a `people` index
(name, years, home, period) for every person a link names, so the app can draw a tie to someone whose period file
isn't loaded. Batches given on the command line are merged in (a pair keeps one link per kind). Links naming an
unknown person or event are dropped, years are pulled inside both lifetimes, and the index is rebuilt from
data/layers/*.json. Rerun after editing people.
"""
import json, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/relations.json"
KINDS = {"teach", "serve", "kin", "friend", "rival", "war", "verse"}

eras = json.load(open(ROOT / "data/eras.json"))["eras"]
people, era_of = {}, {}
for e in eras:
    f = ROOT / f"data/layers/{e['id']}.json"
    if not f.exists():
        continue
    for p in json.load(open(f)).get("people", []):
        if p["id"] not in people:
            people[p["id"]], era_of[p["id"]] = p, e["id"]
events = {x["id"] for x in json.load(open(ROOT / "data/events.json"))}

old = json.load(open(OUT))["links"] if OUT.exists() else []
links, seen, dropped, moved = [], set(), 0, 0
for l in old + [l for f in sys.argv[1:] for l in json.load(open(f))]:
    a, b, k = l.get("a"), l.get("b"), l.get("kind")
    if a not in people or b not in people or a == b or k not in KINDS:
        dropped += 1
        continue
    key = (k, a, b) if k in ("teach", "serve", "kin", "verse", "war") else (k, *sorted((a, b)))
    if key in seen:
        continue
    seen.add(key)
    if l.get("event") and l["event"] not in events:
        l.pop("event")
    # Both alive at `year`: inside the overlap of the two lives (a life with no birth year spans its last 40 years).
    span = lambda p: (p.get("born") if p.get("born") is not None else p["died"] - 40, p.get("died") if p.get("died") is not None else 2026)
    (a0, a1), (b0, b1) = span(people[a]), span(people[b])
    lo, hi = max(a0, b0), min(a1, b1)
    if lo > hi:
        dropped += 1
        continue
    y = int(l.get("year", lo))
    if not lo <= y <= hi:
        y, moved = min(hi, max(lo, y)), moved + 1
    out = {"a": a, "b": b, "kind": k, "year": y}
    if l.get("to") is not None and int(l["to"]) > y:
        out["to"] = min(int(l["to"]), hi)
    for f in ("rel_zh", "rel", "text_zh", "text", "event"):
        if l.get(f):
            out[f] = l[f]
    links.append(out)
links.sort(key=lambda l: (l["year"], l["a"], l["b"]))

used = sorted({x for l in links for x in (l["a"], l["b"])})
index = {}
for i in used:
    p = people[i]
    index[i] = {"name": p["name"], "name_zh": p.get("name_zh"), "born": p.get("born"), "died": p.get("died"),
                "lon": p["lon"], "lat": p["lat"], "field": p.get("field"), "era": era_of[i]}
with open(OUT, "w") as f:
    f.write('{"note": "AI-drafted, not source-checked. Built by tools/build_relations.py.",\n "people": ')
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    f.write(',\n "links": [\n')
    f.write(",\n".join(json.dumps(l, ensure_ascii=False, separators=(",", ":")) for l in links))
    f.write("\n]}\n")
from collections import Counter
print(f"{len(links)} links, {len(used)} of {len(people)} people linked; dropped {dropped}, years moved {moved}")
print(dict(Counter(l["kind"] for l in links)), sum(1 for l in links if "event" in l), "with events")
