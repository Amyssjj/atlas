"""Carry states that outlived their period into the next period's first map, e.g. Wu (to 280) on the Western Jin map
and Chen / Western Liang (to 589 / 587) on the Sui map. Each output is the next period's map with the survivors cut
out of the new dynasty and drawn with their outline from the last map of their own period.

Usage: python3 tools/carry_states.py      (needs shapely; writes data/borders/<out>.geojson)"""
import json, os, re
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
# (output, base map of the new period, its dynasty feature, map the survivors come from, survivors)
JOBS = [
    ("western-jin-266", "western-jin", "Jin", "three-kingdoms", ["Wu"]),
    ("sui-581", "sui", "Sui Empire", "ns-579", ["Chen", "Western Liang"]),
    ("sui-587", "sui", "Sui Empire", "ns-579", ["Chen"]),
]
for out, base, dynasty, src, keep in JOBS:
    b = json.load(open(P(f"data/borders/{base}.geojson")))
    s = {f["properties"]["name"]: f for f in json.load(open(P(f"data/borders/{src}.geojson")))["features"]}
    cut = unary_union([shape(s[k]["geometry"]).buffer(0) for k in keep])
    feats = []
    for f in b["features"]:
        if f["properties"]["name"] == dynasty:
            g = shape(f["geometry"]).buffer(0).difference(cut.buffer(0.02))
            f = dict(f, geometry=mapping(g))
        feats.append(f)
    for k in keep:
        p = {x: s[k]["properties"][x] for x in ("name", "name_zh", "focus", "label", "area", "color") if x in s[k]["properties"]}
        feats.append({"type": "Feature", "properties": p, "geometry": s[k]["geometry"]})
    txt = json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":"), ensure_ascii=False)
    open(P(f"data/borders/{out}.geojson"), "w").write(re.sub(r"(\d+\.\d{3})\d+", r"\1", txt))
    print(out, len(feats), "features")
