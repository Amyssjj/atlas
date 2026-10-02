"""Merge overlay batches from data/work2/<era-id>.json into data/layers/<era-id>.json.

Each batch has `rulers` (polity name -> reigns), `armies` (war event id -> sides) and `routes` (lines on the map).
Checks names, ids and coordinates against the app's data and prints anything it drops.
"""
import glob, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
eras = {e["id"]: e for e in json.load(open(P("data/eras.json")))["eras"]}
events = {e["id"]: e for e in json.load(open(P("data/events.json")))}
UNITS = {"infantry", "cavalry", "chariots", "archers", "crossbows", "navy", "siege", "firearms", "artillery", "elephants"}
KINDS = {"campaign", "journey", "trade", "canal", "wall"}
os.makedirs(P("data/layers"), exist_ok=True)

def load_borders(path):
    """A border file, or one map of a bundle when the path ends in #<id> (see tools/carve_states.py)."""
    f, _, key = path.partition("#")
    d = json.load(open(P(f)))
    return d[key] if key else d

for path in sorted(glob.glob(P("data/work2/*.json"))):
    if path.endswith("eras_index.json"):
        continue
    w = json.load(open(path))
    era = eras[w["era"]]
    names = set()
    for s in era["snapshots"]:
        names |= {f["properties"]["name"] for f in load_borders(s["borders"])["features"]}
    issues = []
    rulers = {}
    for name, reigns in w.get("rulers", {}).items():
        if name not in names:
            issues.append(f"ruler polity not on map: {name}")
            continue
        ok = [r for r in reigns if all(k in r for k in ("name", "name_zh", "from", "to")) and r["from"] <= r["to"]]
        if len(ok) < len(reigns):
            issues.append(f"{name}: dropped {len(reigns) - len(ok)} bad reigns")
        rulers[name] = sorted(ok, key=lambda r: r["from"])
    armies = {}
    for eid, a in w.get("armies", {}).items():
        if eid not in events:
            issues.append(f"army for unknown event {eid}")
            continue
        if len(a.get("sides", [])) < 2:
            issues.append(f"{eid}: fewer than 2 sides")
            continue
        for sd in a["sides"]:
            sd["units"] = [u for u in sd.get("units", []) if u in UNITS]
        armies[eid] = a
    routes = []
    for r in w.get("routes", []):
        pts = r.get("path", [])
        if r.get("kind") not in KINDS or len(pts) < 2 or r["from"] > r["to"] or not all(60 <= x <= 150 and 0 <= y <= 60 for x, y in pts):
            issues.append(f"route dropped: {r.get('id')}")
            continue
        if r.get("event") and r["event"] not in events:
            issues.append(f"route {r['id']}: unknown event {r['event']}, link removed")
            r.pop("event")
        routes.append(r)
    with open(P("data", "layers", f"{era['id']}.json"), "w") as f:
        json.dump({"rulers": rulers, "armies": armies, "routes": routes}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{era['id']:15s} rulers {len(rulers):3d} ({sum(map(len, rulers.values()))} reigns)  armies {len(armies):3d}  routes {len(routes):2d}")
    for i in issues:
        print("   !", i)
