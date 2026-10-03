"""Write fact-check verdicts into the data: python3 tools/apply_facts.py <report.json> [verdicts.json ...]

Items the report found `ok` get "check": {"s": "ok"}. A verdict ({"key", "s": ok|fixed|doubt, "set": {field: value},
"n", "n_zh"}) overrides that: `set` changes the item's fields (the old values are kept in check.was) and the note
says what changed or why it is doubtful. Items with neither keep no check mark ("not yet checked")."""
import glob, json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
report = json.load(open(sys.argv[1]))
verdict = {}
for f in sys.argv[2:]:
    for v in json.load(open(f)): verdict[v["key"]] = v
status = {r["key"]: r["status"] for r in report}
n = {"ok": 0, "fixed": 0, "doubt": 0}


def mark(x, key):
    x.pop("check", None)
    v = verdict.get(key)
    if v:
        c = {"s": v["s"]}
        if v.get("set"):
            c["was"] = {k: x.get(k) for k in v["set"]}
            x.update(v["set"])
        for k in ("n", "n_zh"):
            if v.get(k): c[k] = v[k]
        x["check"] = c
    elif status.get(key) == "ok":
        x["check"] = {"s": "ok"}
    if "check" in x: n[x["check"]["s"]] += 1


def dump(path, data):
    s = open(path).read()
    ind = 1 if s.startswith("{\n \"") or s.startswith("[\n {") else 2 if s.startswith(("{\n  ", "[\n  ")) else None
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=ind, separators=None if ind else (",", ":"))
    if s.endswith("\n"): open(path, "a").write("\n")


p = os.path.join(ROOT, "data/events.json")
evs = json.load(open(p))
for e in evs: mark(e, e["id"])
dump(p, evs)
for f in sorted(glob.glob(os.path.join(ROOT, "data/layers/*.json"))):
    D = json.load(open(f))
    world = os.path.basename(f).startswith("world-")
    for L in (D.values() if world else [D]):
        for x in L.get("people", []):
            mark(x, "|".join(map(str, ("p", x["name"], x.get("born"), x.get("died")))))
        for polity, rs in (L.get("rulers") or {}).items():
            for x in rs: mark(x, f"{polity}|{x['name']}|{x['from']}|{x['to']}")
    dump(f, D)
print(n)
