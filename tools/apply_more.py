"""Write the source check of the later layers into the data: python3 tools/apply_more.py [tools/more_verdicts.json]

Verdicts ({"set": lives|ties|disasters|periods|economy, "key", "s": ok|fixed|doubt, "n", "n_zh", "fix": {field: value}})
come from comparing each item with Wikipedia passages gathered by tools/fact_more.py (reviewed by AI against that text
only). Keys: "<life id>#<step index>" for life stops, "<a>|<b>|<year>|<kind>" for ties, the id for disasters and climate phases,
"<metric>|<year>" for economy snapshots. Each becomes the item's `check` mark ({s, n, n_zh, was}); a fix replaces the
fields and keeps the old values in check.was. Re-running restores the originals first, so it can be applied again."""
import json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
V = {(v["set"], v["key"]): v for v in json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "tools/more_verdicts.json")))}


def load(rel):
    return json.load(open(os.path.join(ROOT, rel)))


def compact(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


count = {}


def mark(kind, key, x):
    old = x.pop("check", None) or {}
    x.update(old.get("was") or {})
    v = V.get((kind, key(x) if callable(key) else key))
    if not v: return
    m = {"s": v["s"]}
    new = {k: val for k, val in (v.get("fix") or {}).items() if x.get(k) != val} if v["s"] == "fixed" else {}
    if new:
        m["was"] = {k: x.get(k) for k in new}
        x.update(new)
    elif v["s"] == "fixed":
        m["s"] = "ok"
    for k in ("n", "n_zh"):
        if v.get(k): m[k] = v[k]
    x["check"] = m
    c = count.setdefault(kind, {"ok": 0, "fixed": 0, "doubt": 0})
    c[m["s"]] += 1


# Each file is written back in the layout its builder (or its author) uses, so diffs stay small.
lives = load("data/lives.json")
for life in lives:
    for i, s in enumerate(life["steps"]): mark("lives", f"{life['id']}#{i}", s)
open(os.path.join(ROOT, "data/lives.json"), "w").write(compact(lives))

R = load("data/relations.json")
for l in R["links"]: mark("ties", lambda l: f"{l['a']}|{l['b']}|{l['year']}|{l['kind']}", l)
with open(os.path.join(ROOT, "data/relations.json"), "w") as f:  # as tools/build_relations.py writes it
    f.write('{"note": ' + json.dumps(R["note"], ensure_ascii=False) + ',\n "people": ' + compact(R["people"]) + ',\n "links": [\n')
    f.write(",\n".join(compact(l) for l in R["links"]) + "\n]}\n")

C = load("data/climate.json")
for d in C["disasters"]: mark("disasters", d["id"], d)
for p in C["periods"]: mark("periods", p["id"], p)
open(os.path.join(ROOT, "data/climate.json"), "w").write(compact(C))

# data/economy.json is laid out by hand, one snapshot per line pair: only its "check" fields are rewritten in place.
path = os.path.join(ROOT, "data/economy.json")
text = re.sub(r', "check": \{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}', "", open(path).read())
E = json.loads(text)
for metric, snaps in E["metrics"].items():
    for s in snaps:
        mark("economy", f"{metric}|{s['year']}", s)
        if "check" not in s: continue
        if s["check"].get("was"): sys.exit(f"economy {metric}|{s['year']}: fixes to economy.json are made by hand")
        block = text.index(f'"{metric}": [')
        at = text.index(f'{{ "year": {s["year"]}, ', block)
        end = at + len(f'{{ "year": {s["year"]}, ')
        text = text[:end] + '"check": ' + json.dumps(s["check"], ensure_ascii=False) + ", " + text[end:]
json.loads(text)
open(path, "w").write(text)

print(json.dumps(count, ensure_ascii=False))
