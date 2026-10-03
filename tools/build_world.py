"""Build the world border maps (data/world/*.json) from the historical-basemaps world snapshots.

Each snapshot becomes data/world/<year>.json (the whole world). Snapshots that fall inside the Chinese dynasties
(2000 BC to 1900) also get data/world/<year>-outer.json: the same map with the East Asia window that the dynasty
maps cover (tools/build_borders.py CLIP) cut out, drawn around those maps.
Chinese names come from data/world/names_zh.json (English NAME -> Chinese), then from the dynasty maps' own
translations. Usage: python3 tools/build_world.py   (downloads into tools/.cache/hb on first run)"""
import colorsys, glob, hashlib, json, os, re, urllib.request
import shapely
from shapely.geometry import box, mapping, shape

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
SRC = "https://raw.githubusercontent.com/aourednik/historical-basemaps/master/geojson/world_{}.geojson"
KEYS = ["bc3000", "bc2000", "bc1500", "bc1000", "bc700", "bc500", "bc400", "bc323", "bc300", "bc200", "bc100", "bc1",
        "100", "200", "300", "400", "500", "600", "700", "800", "900", "1000", "1100", "1200", "1279", "1300", "1400",
        "1492", "1500", "1530", "1600", "1650", "1700", "1715", "1783", "1800", "1815", "1880", "1900", "1914", "1920",
        "1930", "1938", "1945", "1960", "1994", "2000", "2010"]
CLIP = box(60, 5, 150, 58)   # same window as tools/build_borders.py
TOL = 0.03                   # degrees; the sources are coarse anyway

def year(k): return -int(k[2:]) if k.startswith("bc") else int(k)

def fetch(k):
    f = P("tools/.cache/hb", f"world_{k}.geojson")
    if not os.path.exists(f):
        urllib.request.urlretrieve(SRC.format(k), f)
    return json.load(open(f))

def colour(name):
    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, 0.42 + (h >> 9) % 12 / 100, 0.25 + (h >> 5) % 15 / 100)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))

def known_zh():
    zh = {}
    for f in glob.glob(P("data/borders/*.geojson")) + glob.glob(P("data/borders/*.json")):
        d = json.load(open(f))
        for fc in ([d] if "features" in d else d.values()):
            for ft in fc.get("features", []):
                p = ft["properties"]
                if p.get("name") and p.get("name_zh"): zh.setdefault(p["name"], p["name_zh"])
    extra = P("data/world/names_zh.json")
    if os.path.exists(extra): zh.update(json.load(open(extra)))
    return zh

def dump(obj):
    return re.sub(r"(\d+\.\d{2})\d+", r"\1", json.dumps(obj, separators=(",", ":"), ensure_ascii=False))

def main():
    os.makedirs(P("data/world"), exist_ok=True)
    zh = known_zh()
    names, index = {}, []
    for k in KEYS:
        y = year(k)
        feats = []
        for ft in fetch(k)["features"]:
            p = ft["properties"]; name = (p.get("NAME") or "").strip()
            if not ft.get("geometry") or not name: continue
            g = shape(ft["geometry"]).buffer(0).simplify(TOL, preserve_topology=True)
            if g.is_empty or g.area < 0.02: continue
            names[name] = names.get(name, 0) + 1
            feats.append((name, g, p))
        def fc(clip_out):
            out = []
            for name, g, p in feats:
                if clip_out: g = g.difference(CLIP)
                if g.is_empty or g.area < 0.02: continue
                g = shapely.set_precision(g, 0.001)
                c = g.representative_point()
                out.append({"type": "Feature", "geometry": mapping(g), "properties": {
                    "name": name, "name_zh": zh.get(name, ""), "focus": False, "color": colour(name),
                    "area": round(g.area, 1), "label": [round(c.x, 2), round(c.y, 2)]}})
            return {"type": "FeatureCollection", "features": out}
        open(P("data/world", f"{y}.json"), "w").write(dump(fc(False)))
        outer = -2070 <= y <= 1912
        if outer: open(P("data/world", f"{y}-outer.json"), "w").write(dump(fc(True)))
        index.append({"from": y, "full": f"data/world/{y}.json", **({"outer": f"data/world/{y}-outer.json"} if outer else {})})
        print(k, len(feats), flush=True)
    json.dump(index, open(P("data/world/index.json"), "w"), indent=1)
    json.dump({n: zh.get(n, "") for n in sorted(names)}, open(P("tools/.cache/world_names.json"), "w"), ensure_ascii=False, indent=1)
    print("names", len(names), "translated", sum(1 for n in names if zh.get(n)))

if __name__ == "__main__":
    main()
