"""Add `polities` to each data/layers/<era>.json: for every polity with rulers, its Chinese name and whether it is a
main (focus) polity of the era, taken from the era's border snapshots. The ruler list in the page uses it to name
and order the countries. Run after tools/merge_layers.py."""
import json
P = lambda f: f
def load_borders(path):
    """A border file, or one map of a bundle when the path ends in #<id> (see tools/carve_states.py)."""
    f, _, key = path.partition("#")
    d = json.load(open(P(f)))
    return d[key] if key else d
eras = json.load(open("data/eras.json"))
eras = eras["eras"] if isinstance(eras, dict) else eras
for e in eras:
    info = {}
    for s in e["snapshots"]:
        for f in load_borders(s["borders"])["features"]:
            p = f["properties"]
            i = info.setdefault(p["name"], {"name_zh": "", "focus": False})
            i["name_zh"] = i["name_zh"] or p.get("name_zh", "")
            i["focus"] = i["focus"] or bool(p.get("focus"))
    path = f"data/layers/{e['id']}.json"
    L = json.load(open(path))
    L["polities"] = {k: info.get(k, {"name_zh": "", "focus": False}) for k in L["rulers"]}
    json.dump(L, open(path, "w"), ensure_ascii=False, separators=(",", ":"))
    print(e["id"], len(L["polities"]))
