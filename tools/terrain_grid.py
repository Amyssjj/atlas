"""A lon/lat grid of elevation and of "natural barriers" (mountain crests and big rivers) for tools/snap_terrain.py.

The elevation comes from the bundled elevation archives (zoom 6, about 2.4 km a pixel), resampled to STEP degrees.
Barrier strength is 0..3: ridges score by how far they stand above the land around them, rivers by their rank in
data/geo/rivers.geojson. The result is cached in tools/.cache/terrain.npz."""
import io, json, math, os, struct
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
W, S, E, N, STEP = 70.0, 8.0, 142.0, 56.0, 0.025
Z = 6

def lonlat_grid():
    lons = W + (np.arange(round((E - W) / STEP)) + 0.5) * STEP
    lats = N - (np.arange(round((N - S) / STEP)) + 0.5) * STEP
    return lons, lats

_packs = {}
def pack_tile(z, x, y):
    """One elevation tile from the bundled archives (tiles/pack/{z}-{x>>3}-{y>>3}.png, see tools/pack_tiles.py)."""
    f = P(f"tiles/pack/{z}-{x >> 3}-{y >> 3}.png")
    if f not in _packs:
        _packs[f] = None
        if os.path.exists(f):
            b = open(f, "rb").read(); o = 8
            while o + 8 <= len(b):
                n = struct.unpack(">I", b[o:o + 4])[0]
                if b[o + 4:o + 8] == b"tpAk":
                    m = struct.unpack("<I", b[o + 8:o + 12])[0]
                    _packs[f] = (b, json.loads(b[o + 12:o + 12 + m]), o + 12 + m)
                    break
                o += 12 + n
    if not _packs[f]: return None
    b, idx, base = _packs[f]
    e = idx.get(f"{x}/{y}")
    return b[base + e[0]:base + e[0] + e[1]] if e else None

def elevation():
    n = 2 ** Z
    lons, lats = lonlat_grid()
    fx = (lons + 180) / 360 * n * 256
    fy = (1 - np.log(np.tan(np.radians(lats)) + 1 / np.cos(np.radians(lats))) / math.pi) / 2 * n * 256
    x0, x1 = int(fx.min() // 256), int(fx.max() // 256)
    y0, y1 = int(fy.min() // 256), int(fy.max() // 256)
    mos = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.float32)
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            b = pack_tile(Z, tx, ty)
            if b is None: continue
            a = np.asarray(Image.open(io.BytesIO(b)).convert("RGB"), np.float32)
            mos[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    yy, xx = np.meshgrid(fy - y0 * 256 - 0.5, fx - x0 * 256 - 0.5, indexing="ij")
    return ndimage.map_coordinates(mos, [yy, xx], order=1)

def to_px(lon, lat):
    return (lon - W) / STEP, (N - lat) / STEP

def rivers(shape):
    """Rivers burnt in by Natural Earth rank: 1 Yangtze, 3 Yellow River, 6 Han/Xiang/Gan/Min, 7 Huai, 8 Wei."""
    strength = {1: 1.5, 2: 1.5, 3: 1.5, 4: 1.2, 5: 1.2, 6: 1.0, 7: 0.8, 8: 0.6}
    out = np.zeros(shape, np.float32)
    for rank in sorted(strength, reverse=True):
        img = Image.new("L", shape[::-1], 0); d = ImageDraw.Draw(img)
        for f in json.load(open(P("data/geo/rivers.geojson")))["features"]:
            if f["properties"].get("rank") != rank: continue
            g = f["geometry"]
            for line in (g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]):
                d.line([to_px(*c) for c in line], fill=255, width=3)
        out = np.maximum(out, np.asarray(img, np.float32) / 255 * strength[rank])
    return out

def build():
    dem = elevation()
    land = dem > 0
    # How far a cell stands above the land within ~40 km and ~120 km: crests score high, valleys and plains low.
    tpi = np.maximum(dem - ndimage.gaussian_filter(dem, 16), 0) + 0.5 * np.maximum(dem - ndimage.gaussian_filter(dem, 48), 0)
    ridge = np.clip(tpi / 700, 0, 3)  # higher crests keep scoring higher, so a border picks the main range
    ridge = ndimage.gaussian_filter(ridge, 1.2)
    riv = rivers(dem.shape)
    np.savez_compressed(P("tools/.cache/terrain.npz"), dem=dem.astype(np.float32), ridge=ridge.astype(np.float32),
                        river=riv, land=land)
    return dem, ridge, riv

def load():
    f = P("tools/.cache/terrain.npz")
    if not os.path.exists(f): build()
    return dict(np.load(f))

if __name__ == "__main__":
    dem, ridge, riv = build()
    img = np.stack([np.clip(ridge * 255, 0, 255), np.clip(dem / 20, 0, 255) * 0.4, np.clip(riv * 255, 0, 255)], -1).astype(np.uint8)
    Image.fromarray(img).save(P("tools/.cache/terrain.png"))
    print(dem.shape, float(dem.max()))
