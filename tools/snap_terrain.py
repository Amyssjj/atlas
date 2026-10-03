"""Move borders onto the mountain crests and rivers near them.

The border sources are coarse: historical-basemaps polygons are a few dozen straight segments, and the state maps
from tools/build_states.py / tools/carve_states.py are Voronoi cells. So a border that should run along the Yangtze or
the rim of the Sichuan basin ends up cutting across valleys. This pass rasterises a map onto the grid from
tools/terrain_grid.py, keeps the inside of every polity fixed, and lets the land within BAND degrees of a border be
re-split by a marker watershed over a "barrier" image: crests and rivers score high, and so does the old border line
(less), so a border moves onto a crest or river close by and stays where it was on open plains.
Coastlines are kept as they were (the result is clipped to the map's features plus Natural Earth land).

Usage: python3 tools/snap_terrain.py [--force] [border files or bundle#id ...]   (default: every map in eras.json)
A snapped map is marked "snapped": true and skipped next time unless --force; rerun the generators first to start
again from the raw shapes. Run after tools/build_borders.py, build_states.py and carve_states.py."""
import heapq, json, os, re, sys
import numpy as np
import shapely
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import shape, mapping, box
from skimage.morphology import medial_axis
from numba import njit
import terrain_grid as tg

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
BAND = 2.5          # degrees a border may move
ALPHA = 12          # extra cost of a cell per unit of barrier (crossing the Yangtze costs about 1.5 degrees of travel)
_t = _land = None

def land_outline():
    global _land
    if _land is None:
        f = P("tools/.cache/ne_50m_land.geojson")  # fetched by tools/build_states.py
        _land = shapely.union_all([shape(x["geometry"]).buffer(0) for x in json.load(open(f))["features"]])
    return _land

def terrain():
    global _t
    if _t is None:
        _t = tg.load()
        _t["barrier"] = np.maximum(_t["ridge"], _t["river"])
    return _t

@njit(cache=True)
def compete(cost, ok, seed, start):
    """Multi-source Dijkstra over the grid: every cell goes to the label that reaches it cheapest."""
    H, W = cost.shape
    best = np.full((H, W), np.inf)
    lab = np.zeros((H, W), np.int32)
    done = np.zeros((H, W), np.bool_)
    heap = [(0.0, 0, 0, 0)]; heap.pop()
    for r in range(H):
        for c in range(W):
            if seed[r, c] != 0 and ok[r, c]:
                best[r, c] = start[r, c]; lab[r, c] = seed[r, c]
                heap.append((float(start[r, c]), r, c, int(seed[r, c])))
    heapq.heapify(heap)
    dr = (-1, -1, -1, 0, 0, 1, 1, 1); dc = (-1, 0, 1, -1, 1, -1, 0, 1)
    while heap:
        b, r, c, k = heapq.heappop(heap)
        if done[r, c] or b > best[r, c]: continue
        done[r, c] = True; lab[r, c] = k
        for i in range(8):
            rr = r + dr[i]; cc = c + dc[i]
            if rr < 0 or cc < 0 or rr >= H or cc >= W or not ok[rr, cc] or done[rr, cc]: continue
            step = 1.4142 if dr[i] != 0 and dc[i] != 0 else 1.0
            nb = b + step * 0.5 * (cost[r, c] + cost[rr, cc])
            if nb < best[rr, cc]:
                best[rr, cc] = nb; heapq.heappush(heap, (nb, rr, cc, k))
    return lab

def rings(g):
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        yield p.exterior.coords, [i.coords for i in p.interiors]

def rasterise(geoms, shp):
    lab = Image.new("I", shp[::-1], 0); d = ImageDraw.Draw(lab)
    for k, g in geoms:
        for ext, holes in rings(g):
            d.polygon([tg.to_px(x, y) for x, y in ext], fill=k)
            for h in holes: d.polygon([tg.to_px(x, y) for x, y in h], fill=0)
    return np.array(lab, np.int32)

def polygonise(mask):
    """Exact pixel outline of a boolean mask, in lon/lat."""
    boxes = []
    for r in np.nonzero(mask.any(1))[0]:
        row = np.concatenate([[0], mask[r].astype(np.int8), [0]])
        edges = np.nonzero(np.diff(row))[0]
        for a, b in zip(edges[::2], edges[1::2]):
            boxes.append(box(tg.W + a * tg.STEP, tg.N - (r + 1) * tg.STEP, tg.W + b * tg.STEP, tg.N - r * tg.STEP))
    return shapely.union_all(boxes, grid_size=tg.STEP / 1000) if boxes else None

def snap(fc):
    t = terrain()
    feats = fc["features"]
    geoms = [(i + 1, shape(f["geometry"]).buffer(0)) for i, f in enumerate(feats) if f.get("geometry")]
    # Work in a window around the map plus a margin.
    x0, y0, x1, y1 = shapely.union_all([g for _, g in geoms]).bounds
    c0, r0 = map(int, tg.to_px(x0 - 1.5, y1 + 1.5)); c1, r1 = map(int, tg.to_px(x1 + 1.5, y0 - 1.5))
    H, Wd = t["dem"].shape
    c0, r0, c1, r1 = max(c0, 0), max(r0, 0), min(c1, Wd), min(r1, H)
    full = rasterise(geoms, (H, Wd)); lab = full[r0:r1, c0:c1]
    land = t["land"][r0:r1, c0:c1] | (lab > 0)
    sea = ~land
    band = BAND / tg.STEP
    # Sources: the inside of every polity deeper than BAND (start cost 0), plus the middle line of arms too narrow to
    # have such a core (start cost BAND - depth, so the arm still reaches its old border at the same cost).
    seed = np.zeros_like(lab); start = np.full(lab.shape, np.inf, np.float32)
    lk = np.where(land, lab, -2)
    for i, sl in enumerate(ndimage.find_objects(lk + 2)):  # slot i holds value i + 1, i.e. label i - 1
        if sl is None or i == 0: continue
        k = i - 1
        sl = tuple(slice(max(a.start - 2, 0), a.stop + 2) for a in sl)
        own = lk[sl] == k
        d = ndimage.distance_transform_edt(own | sea[sl])
        deep = own & (d > band)
        # (the middle line of every part narrower than the band, measured against its widest point nearby)
        local = ndimage.maximum_filter(np.where(own, d, 0), size=int(2 * band) | 1)
        arm = own & ~deep & medial_axis(own | sea[sl]) & (d >= np.minimum(0.5 * band, 0.6 * local))
        if k == 0: arm &= d >= 0.5 * band  # land nobody holds keeps only its wide parts, so a polity may grow to a ridge
        v = k if k else -1
        seed[sl][deep] = v; start[sl][deep] = 0
        seed[sl][arm] = v; start[sl][arm] = (band - d)[arm]
    cost = 1 + ALPHA * t["barrier"][r0:r1, c0:c1]
    out = compete(np.ascontiguousarray(cost, np.float32), land, seed, start)
    out[out == -1] = 0
    # Sea cells take the nearest land label, so the coast comes from the original outline below.
    idx = ndimage.distance_transform_edt(~land, return_distances=False, return_indices=True)
    out = out[idx[0], idx[1]]
    full[:] = 0; full[r0:r1, c0:c1] = out
    # Coasts as drawn; inland a polity may now reach into land no feature covered.
    win = box(tg.W + c0 * tg.STEP, tg.N - r1 * tg.STEP, tg.W + c1 * tg.STEP, tg.N - r0 * tg.STEP)
    grid = box(tg.W, tg.S, tg.E, tg.N)
    outline = shapely.union_all([g for _, g in geoms] + [land_outline().intersection(win)])
    keys = [k for k, _ in geoms]
    polys = [polygonise(full == k) for k in keys]
    have = [i for i, p in enumerate(polys) if p is not None and not p.is_empty]
    simple = shapely.coverage_simplify([polys[i] for i in have], tolerance=tg.STEP * 2.5)
    new = dict(zip(have, simple))
    for i, (k, g) in enumerate(geoms):
        f = feats[k - 1]
        if i not in new:
            continue  # too small for the grid: keep as drawn
        # Parts beyond the terrain grid stay as drawn.
        ng = new[i].intersection(outline).intersection(grid).union(g.difference(grid)).buffer(0)
        if ng.is_empty:
            f["geometry"] = None; continue
        ng = shapely.set_precision(ng, 0.001)
        f["geometry"] = mapping(ng)
        pr = f["properties"]
        if "label" in pr and not ng.contains(shapely.Point(pr["label"])):
            big = max(ng.geoms, key=lambda q: q.area) if hasattr(ng, "geoms") else ng
            p = big.representative_point(); pr["label"] = [round(p.x, 2), round(p.y, 2)]
        if "area" in pr: pr["area"] = round(ng.area, 1)
    fc["features"] = [f for f in feats if f.get("geometry")]
    fc["snapped"] = True
    return fc

def dump(obj):
    return re.sub(r"(\d+\.\d{3})\d+", r"\1", json.dumps(obj, separators=(",", ":"), ensure_ascii=False))

def run(paths, force):
    for path in paths:
        f, _, key = path.partition("#")
        d = json.load(open(P(f)))
        fc = d[key] if key else d
        if fc.get("snapped") and not force:
            print(f"{path}: already snapped"); continue
        snap(fc)
        open(P(f), "w").write(dump(d))
        print(f"{path}: snapped", flush=True)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    if not args:
        eras = json.load(open(P("data/eras.json"))); eras = eras["eras"] if isinstance(eras, dict) else eras
        args = list(dict.fromkeys(s["borders"] for e in eras for s in e["snapshots"]))
    run(args, "--force" in sys.argv)
