"""Build state-level border snapshots from a seed-point spec (data/states/*.json).

Usage: python3 tools/build_states.py [cache_dir]
Needs shapely. Downloads Natural Earth 50m land into cache_dir to clip coastlines.

Each seed is a place a state held. Seeds are grown into Voronoi cells, each limited to
`radius` degrees around its seed and clipped to land, then merged by owner. A snapshot
lists only the seeds that change owner, so a conquest is one line in the spec.

Optional: `backdrop` names a border file whose non-focus features (the neighbours) are
added around the seeded states, minus the seeded land. A snapshot's `names` map renames
states or backdrop features from then on ({old name: [name, zh]} or null to drop one);
features that end up with the same name are merged, e.g. the Sixteen Prefectures and Liao.
"""
import json, os, re, sys, urllib.request
from shapely.geometry import shape, mapping, MultiPoint, Point, box
from shapely.ops import unary_union, voronoi_diagram

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CACHE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, ".cache")
LAND_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson"
PALETTE = ["#8a6f9e", "#5f87a3", "#a07d5a", "#6f9460", "#a3727a", "#4f8f86", "#9a8a4a", "#7272a8", "#b0805f", "#7d6b5a"]
SPECS = ["data/states/zhou-states.json", "data/states/north-south.json", "data/states/five-dynasties.json"]


def land(bounds):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "ne_50m_land.geojson")
    if not os.path.exists(p):
        urllib.request.urlretrieve(LAND_URL, p)
    clip = box(*bounds)
    parts = [shape(f["geometry"]).buffer(0).intersection(clip) for f in json.load(open(p))["features"]]
    return unary_union([g for g in parts if not g.is_empty])


def build(spec_path):
    spec = json.load(open(os.path.join(ROOT, spec_path)))
    seeds, states, r = spec["seeds"], spec["states"], spec["radius"]
    names = list(seeds)
    pts = [Point(*seeds[n]) for n in names]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    bounds = (min(xs) - r - 1, min(ys) - r - 1, max(xs) + r + 1, max(ys) + r + 1)
    ground = land(bounds)
    regions = voronoi_diagram(MultiPoint(pts), envelope=box(*bounds))
    cells = {}
    for poly in regions.geoms:
        for n, p in zip(names, pts):
            if poly.contains(p):
                cells[n] = poly.intersection(p.buffer(r, 32)).intersection(ground)
                break

    backdrop = []
    if spec.get("backdrop"):
        bd = json.load(open(os.path.join(ROOT, spec["backdrop"])))
        backdrop = [(f["properties"], shape(f["geometry"]).buffer(0)) for f in bd["features"] if not f["properties"]["focus"]]

    owner, renames = {}, {}
    for snap in spec["snapshots"]:
        renames.update(snap.get("names", {}))
        for st, ss in snap["set"].items():
            assert st in states, f"{snap['id']}: unknown state {st}"
            for s in ss:
                assert s in seeds, f"{snap['id']}: unknown seed {s}"
                owner[s] = st
        missing = [s for s in names if s not in owner]
        if missing:
            print(f"  warning {snap['id']}: seeds with no owner {missing}")
        by_state = {}
        for s, st in owner.items():
            by_state.setdefault(st, []).append(cells[s])
        merged = {}  # final name -> [props, geoms]

        def put(name, zh, props, geom):
            if name in renames:
                if renames[name] is None:
                    return
                name, zh = renames[name]
            m = merged.setdefault(name, [dict(props, name=name, name_zh=zh), []])
            m[1].append(geom)

        seeded = []
        for st, geoms in by_state.items():
            meta = states[st]
            props = {"focus": not meta.get("outsider"), "kind": "state", "approx": True}
            if meta.get("color"):
                props["color"] = meta["color"]
            elif meta.get("outsider"):
                props["color"] = PALETTE[sum(map(ord, meta["name"])) % len(PALETTE)]
            if meta.get("minor"):
                props["minor"] = True
            g = unary_union(geoms)
            seeded.append(g)
            put(meta["name"], meta["zh"], props, g)
        taken = unary_union(seeded).buffer(0.05)
        for bp, bg in backdrop:
            g = bg.difference(taken)
            if g.area > 0.3:
                props = {k: v for k, v in bp.items() if k not in ("label", "area")}
                put(bp["name"], bp.get("name_zh", ""), props, g)

        feats = []
        for name, (props, geoms) in merged.items():
            u = unary_union(geoms).buffer(0.02).buffer(-0.02).simplify(0.02, preserve_topology=True)
            if u.is_empty:
                continue
            big = max(u.geoms, key=lambda g: g.area) if hasattr(u, "geoms") else u
            pt = big.representative_point()
            props.update(label=[round(pt.x, 2), round(pt.y, 2)], area=round(u.area, 1))
            feats.append({"type": "Feature", "properties": props, "geometry": mapping(u)})
        feats.sort(key=lambda f: f["properties"]["focus"])
        out = json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":"), ensure_ascii=False)
        out = re.sub(r"(\d+\.\d{3})\d+", r"\1", out)
        open(os.path.join(ROOT, "data", "borders", f"{snap['id']}.geojson"), "w").write(out)
        print(f"{snap['id']:10s} {len(feats):3d} polities  {len(out)//1024} KB")


if __name__ == "__main__":
    for s in SPECS:
        build(s)
