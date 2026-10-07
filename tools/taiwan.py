"""Give Taiwan an owner on every China map from the Ming to the end of the Qing, so it can be clicked and selected.

The source maps leave the island out after 1683 (historical-basemaps has no Qing Taiwan) and let the Middag
Kingdom swallow Tainan in 1674-1678. The island's outline is the Ming map's "Taiwan" feature. Owners:
  before 1644 (Ming maps)      台湾诸部 (unchanged, Chinese name filled in)
  1644-1661 (early Qing)       荷属台湾, with the 大肚王国 (Middag) in the centre-west
  1662-1682 (early Qing)       明郑 (东宁), with the 大肚王国
  1683-1894                    清 (Taiwan prefecture of Fujian from 1684, a province from 1885)
  1895-1911                    日本 (ceded by the Treaty of Shimonoseki)
Run after build_borders / carve_states / snap_terrain, then rerun build_countries.py. Safe to run again."""
import json, os
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

ROOT = os.path.join(os.path.dirname(__file__), "..")
P = lambda p: os.path.join(ROOT, p)
B = lambda n: P(f"data/borders/{n}")


def rnd(o):
    return [rnd(x) for x in o] if isinstance(o, (list, tuple)) and o and isinstance(o[0], (list, tuple)) else [round(o[0], 3), round(o[1], 3)]


def geom(g):
    m = mapping(g)
    return {"type": m["type"], "coordinates": rnd(m["coordinates"])}


def put(fc, name, island_part, **props):
    """Remove the island from every feature, then add `island_part` to feature `name` (made if missing)."""
    tgt = None
    for f in fc["features"]:
        g = shape(f["geometry"]).buffer(0)
        if g.intersects(ISLAND):
            g = g.difference(ISLAND)
        if f["properties"]["name"] == name:
            tgt, g = f, unary_union([g, island_part])
        f["geometry"] = geom(g) if not g.is_empty else None
        if f["geometry"] and "area" in f["properties"]:
            f["properties"]["area"] = round(g.area, 1)
    if tgt is None:
        tgt = {"type": "Feature", "properties": {"name": name, **props}, "geometry": geom(island_part)}
        fc["features"].append(tgt)
    tgt["properties"].update({k: v for k, v in props.items() if not tgt["properties"].get(k)})
    fc["features"] = [f for f in fc["features"] if f["geometry"]]


ming = json.load(open(B("ming.geojson")))
ISLAND = shape(next(f for f in ming["features"] if f["properties"]["name"] == "Taiwan")["geometry"]).buffer(0)

for n in ["ming.geojson", "ming-1616.geojson", "ming-1621.geojson", "ming-1636.geojson"]:
    fc = json.load(open(B(n)))
    for f in fc["features"]:
        if f["properties"]["name"] == "Taiwan" and not f["properties"].get("name_zh"):
            f["properties"]["name_zh"] = "台湾诸部"
    json.dump(fc, open(B(n), "w"), ensure_ascii=False, separators=(",", ":"))

# Early Qing bundle: Middag keeps its 1664 shape; the rest of the island goes to the Dutch, then to the Zheng.
eq = json.load(open(B("early-qing.json")))
middag = shape(next(f for f in eq["qm-1664"]["features"] if f["properties"]["name"] == "Middag Kingdom")["geometry"]).buffer(0).intersection(ISLAND)
for sid, fc in eq.items():
    year = int(sid.split("-")[1])
    owner = ("Dutch Formosa", "荷属台湾", False, "#6a8aa0") if year < 1662 else ("Kingdom of Tungning", "明郑 (东宁)", True, "#2f8a7a")
    put(fc, owner[0], ISLAND.difference(middag), name_zh=owner[1], focus=owner[2], color=owner[3], approx=True)
    for f in fc["features"]:
        if f["properties"]["name"] == "Middag Kingdom":
            f["geometry"] = geom(unary_union([shape(f["geometry"]).buffer(0), middag]))
    if not any(f["properties"]["name"] == "Middag Kingdom" for f in fc["features"]):
        put(fc, "Middag Kingdom", middag, color="#7272a8", focus=False)
        for f in fc["features"]:  # put() took the island from the owner; give it back outside Middag
            if f["properties"]["name"] == owner[0]:
                f["geometry"] = geom(unary_union([shape(f["geometry"]).buffer(0), ISLAND.difference(middag)]))
    for f in fc["features"]:
        if f["properties"]["name"] == "Middag Kingdom":
            f["properties"]["name_zh"] = "大肚王国"
json.dump(eq, open(B("early-qing.json"), "w"), ensure_ascii=False, separators=(",", ":"))

# Qing maps: the island is Qing's; from 1895 Japan's. qing-1900 (used from 1860) is split at 1895: qing-1860 keeps
# Taiwan Qing, qing-1900 gives it to Japan under the name its Japan feature already has.
src_1900 = B("qing-1900.geojson")
base_1860 = json.load(open(B("qing-1860.geojson") if os.path.exists(B("qing-1860.geojson")) else src_1900))
for n, fc in [("qing-1683.geojson", None), ("qing-1720.geojson", None), ("qing-1800.geojson", None), ("qing-1860.geojson", base_1860)]:
    fc = fc or json.load(open(B(n)))
    put(fc, "Qing", ISLAND, name_zh="清", focus=True)
    fc["snapped"] = True
    json.dump(fc, open(B(n), "w"), ensure_ascii=False, separators=(",", ":"))
fc = json.load(open(src_1900))
put(fc, "Imperial Japan", ISLAND, name_zh="日本", focus=False)
json.dump(fc, open(src_1900, "w"), ensure_ascii=False, separators=(",", ":"))
print("Taiwan set on Ming, early Qing and Qing maps")
