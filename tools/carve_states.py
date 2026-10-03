"""Draw several states inside an existing map by carving it into seed cells (like tools/build_states.py, but the
land comes from a base border file instead of Natural Earth). Used for the Sixteen Kingdoms on the Jin maps and for
the Southern Ming, Shun, Xi, Zheng and Three Feudatories on the early Qing maps.

Usage: python3 tools/carve_states.py data/states/sixteen-kingdoms.json [more specs]

Spec: {"radius", "seeds": {id: [lon, lat]}, "states": {id: {name, zh, color?, focus?}},
       "snapshots": [{id, from, label, label_zh, base, area: [base feature names], extra?: [[w, s, e, n]], rest, set, names?}]}
`base`, `area`, `extra` and `rest` carry over from the previous snapshot when left out. Every snapshot's `set` gives
seeds a new owner (owners carry over). The carved area is the named base features plus land inside the `extra` boxes;
each seed gets the part of it nearest to it (within `radius` degrees), and whatever no owned seed covers goes to `rest`.
Base features outside the area are kept as they are. `names` renames a state from then on ({id: [name, zh]}).
All snapshots of a spec go into one bundle, data/borders/<spec name>.json ({snapshot id: FeatureCollection}), which
data/eras.json points at as "data/borders/<spec name>.json#<snapshot id>" (the published page has a file limit)."""
import json, os, re, sys
from shapely.geometry import shape, mapping, MultiPoint, Point, box
from shapely.ops import unary_union, voronoi_diagram

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
_land = None
def land():
    global _land
    if _land is None:
        f = P("tools/.cache/ne_50m_land.geojson")  # fetched by tools/build_states.py
        _land = unary_union([shape(x["geometry"]).buffer(0) for x in json.load(open(f))["features"]])
    return _land

def build(spec_path):
    spec = json.load(open(P(spec_path)))
    seeds, states, r = spec["seeds"], spec["states"], spec["radius"]
    names = list(seeds)
    pts = [Point(*seeds[n]) for n in names]
    env = box(min(p.x for p in pts) - 10, min(p.y for p in pts) - 10, max(p.x for p in pts) + 10, max(p.y for p in pts) + 10)
    vor = {}
    for poly in voronoi_diagram(MultiPoint(pts), envelope=env).geoms:
        for n, p in zip(names, pts):
            if poly.contains(p): vor[n] = poly.intersection(p.buffer(r, 32)); break
    owner, cur, renames, bundle = {}, {}, {}, {}
    for snap in spec["snapshots"]:
        for k in ("base", "area", "extra", "rest"):
            if k in snap: cur[k] = snap[k]
        renames.update(snap.get("names", {}))
        for st, ss in snap.get("set", {}).items():
            assert st in states, f"{snap['id']}: unknown state {st}"
            for s in ss:
                assert s in seeds, f"{snap['id']}: unknown seed {s}"
                owner[s] = st
        base = json.load(open(P(cur["base"])))["features"]
        inside = [f for f in base if f["properties"]["name"] in cur["area"]]
        area = unary_union([shape(f["geometry"]).buffer(0) for f in inside] +
                           [land().intersection(box(*b)) for b in cur.get("extra", [])])
        by = {}
        for s in names:
            st = owner.get(s, cur["rest"])
            g = vor[s].intersection(area)
            if not g.is_empty: by.setdefault(st, []).append(g)
        covered = unary_union([g for gs in by.values() for g in gs])
        left = area.difference(covered)
        if not left.is_empty: by.setdefault(cur["rest"], []).append(left)
        feats = [f for f in base if f["properties"]["name"] not in cur["area"]]
        for st, gs in by.items():
            meta = states[st]
            name, zh = renames.get(st, (meta["name"], meta["zh"]))
            u = unary_union(gs).buffer(0.02).buffer(-0.02).simplify(0.02, preserve_topology=True)
            if u.is_empty: continue
            big = max(u.geoms, key=lambda g: g.area) if hasattr(u, "geoms") else u
            pt = big.representative_point()
            props = {"name": name, "name_zh": zh, "focus": meta.get("focus", True), "approx": True,
                     "label": [round(pt.x, 2), round(pt.y, 2)], "area": round(u.area, 1)}
            if meta.get("color"): props["color"] = meta["color"]
            feats.append({"type": "Feature", "properties": props, "geometry": mapping(u)})
        feats.sort(key=lambda f: f["properties"]["focus"])
        bundle[snap["id"]] = {"type": "FeatureCollection", "features": feats}
        print(f"{snap['id']:12s} {', '.join(sorted(states[s]['zh'] for s in by))}")

    out = re.sub(r"(\d+\.\d{3})\d+", r"\1", json.dumps(bundle, separators=(",", ":"), ensure_ascii=False))
    open(P("data/borders", os.path.basename(spec_path)), "w").write(out)

if __name__ == "__main__":
    for s in sys.argv[1:]: build(s)
