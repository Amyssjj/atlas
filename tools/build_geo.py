"""Rivers and lakes for the map, clipped from Natural Earth 10m (public domain) to East Asia.
Usage: python3 tools/build_geo.py <dir with ne_10m_rivers_lake_centerlines.geojson and ne_10m_lakes.geojson>"""
import json, os, re, sys
from shapely.geometry import shape, mapping, box
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = sys.argv[1]
B = box(60, 8, 148, 56)

def clip(name, keep, simplify):
    out = []
    for f in json.load(open(os.path.join(SRC, name)))["features"]:
        p = f["properties"]
        if not keep(p):
            continue
        g = shape(f["geometry"]).buffer(0) if "lakes" in name else shape(f["geometry"])
        g = g.intersection(B)
        if g.is_empty:
            continue
        g = g.simplify(simplify, preserve_topology=True)
        if "lakes" in name and g.area < 0.02:
            continue
        out.append({"type": "Feature", "properties": {"rank": int(p.get("scalerank") or 9)}, "geometry": mapping(g)})
    return out

for src, dst, keep, s in [
    ("ne_10m_rivers_lake_centerlines.geojson", "rivers", lambda p: (p.get("scalerank") or 99) <= 9, 0.01),
    ("ne_10m_lakes.geojson", "lakes", lambda p: (p.get("scalerank") or 99) <= 9, 0.01),
]:
    fc = json.dumps({"type": "FeatureCollection", "features": clip(src, keep, s)}, separators=(",", ":"))
    fc = re.sub(r"(\d+\.\d{3})\d+", r"\1", fc)
    open(os.path.join(ROOT, "data", "geo", f"{dst}.geojson"), "w").write(fc)
    print(dst, len(fc) // 1024, "KB")
