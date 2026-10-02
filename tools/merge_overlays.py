"""Merge batches from data/work3/<era-id>.json: people and capitals go into data/layers/<era-id>.json (alongside the
rulers, armies and routes there); population, faith and inventions are collected into data/overlays.json, because
they build up over time and the page shows everything up to the current year.
"""
import glob, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
eras = {e["id"]: e for e in json.load(open(P("data/eras.json")))["eras"]}
ok_pt = lambda x: 60 <= x.get("lon", 0) <= 150 and 0 <= x.get("lat", 0) <= 60
glob_ = {"population": [], "faith": [], "inventions": []}
seen = set()

for path in sorted(glob.glob(P("data/work3/*.json"))):
    w = json.load(open(path))
    era = eras[w["era"]]
    issues = []
    lp = P("data", "layers", f"{era['id']}.json")
    layer = json.load(open(lp)) if os.path.exists(lp) else {}
    people = []
    for p in w.get("people", []):
        if p.get("died") is None:  # dates unknown: show the person for the whole era
            p["show"] = [era["start"], era["end"]]
        if not ok_pt(p) or p["id"] in seen:
            issues.append(f"person dropped: {p.get('id')}")
            continue
        seen.add(p["id"]); people.append(p)
    caps = [c for c in w.get("capitals", []) if ok_pt(c) and c["from"] <= c["to"]]
    if len(caps) < len(w.get("capitals", [])):
        issues.append(f"{len(w['capitals']) - len(caps)} capitals dropped")
    layer.update(people=people, capitals=caps)
    with open(lp, "w") as f:
        json.dump(layer, f, ensure_ascii=False, separators=(",", ":"))
    glob_["population"] += [p for p in w.get("population", []) if p.get("millions")]
    for key in ("faith", "inventions"):
        for x in w.get(key, []):
            if not ok_pt(x) or x["id"] in seen:
                issues.append(f"{key} dropped: {x.get('id')}")
                continue
            seen.add(x["id"]); glob_[key].append(x)
    print(f"{era['id']:15s} people {len(people):2d}  capitals {len(caps):2d}  pop {len(w.get('population', []))}  faith {len(w.get('faith', []))}  inventions {len(w.get('inventions', []))}")
    for i in issues:
        print("   !", i)

for k in glob_:
    glob_[k].sort(key=lambda x: x["year"])
with open(P("data/overlays.json"), "w") as f:
    json.dump(glob_, f, ensure_ascii=False, separators=(",", ":"))
print({k: len(v) for k, v in glob_.items()})
