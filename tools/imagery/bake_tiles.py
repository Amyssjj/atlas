# Bake web-mercator JPEG tiles from the Sentinel-2 mosaic sources, with the sea coloured by depth from the DEM tiles.
import glob, io, math, os, sys, numpy as np
from concurrent.futures import ProcessPoolExecutor
from PIL import Image
import rasterio
from rasterio.warp import reproject, transform_bounds
from rasterio.enums import Resampling
from affine import Affine
HM = "/mnt/project-files/history-map"
DEM = "../dem/raw"
R = 6378137 * math.pi
GAIN, GAMMA, SAT = float(os.environ.get("GAIN", 3.2)), float(os.environ.get("GAMMA", 0.85)), float(os.environ.get("SAT", 1.45))

SRC = []
FACTOR = os.environ.get("FACTOR", "4")
for f in sorted(glob.glob(f"src/*-{FACTOR}.npz")):
    d = np.load(f)
    tr = Affine(*d["transform"]); crs = str(d["crs"]); h, w = d["rgb"].shape[1:]
    b = transform_bounds(crs, "EPSG:4326", tr.c, tr.f + tr.e * h, tr.c + tr.a * w, tr.f, densify_pts=21)
    SRC.append((f, tr, crs, b))

def tile_bounds(z, x, y):
    n = 2 ** z; s = 2 * R / n
    return -R + x * s, R - (y + 1) * s, -R + (x + 1) * s, R - y * s
def lonlat(z, x, y):
    n = 2 ** z
    lon = lambda x: x / n * 360 - 180
    lat = lambda y: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon(x), lat(y + 1), lon(x + 1), lat(y)

def dem(z, x, y):
    for p in (f"{DEM}/{z}/{x}/{y}.png", f"{HM}/tiles/terrarium/{z}/{x}/{y}.png"):
        if os.path.exists(p):
            a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
            return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    if z > 8:  # past the bundled elevation: enlarge a quarter of the parent
        e = dem(z - 1, x >> 1, y >> 1)
        if e is not None:
            q = e[(y & 1) * 128:(y & 1) * 128 + 128, (x & 1) * 128:(x & 1) * 128 + 128]
            return q.repeat(2, 0).repeat(2, 1)
    return None

SHALLOW, MID, DEEP = np.array([96, 196, 196.]), np.array([34, 120, 170.]), np.array([16, 48, 104.])
def sea_color(depth):
    t1 = np.clip(depth / 120, 0, 1)[..., None]
    t2 = np.clip((depth - 120) / 3500, 0, 1)[..., None] ** 0.6
    return SHALLOW * (1 - t1) + MID * t1 * (1 - t2) + DEEP * t2

def bake(job):
    z, x, y, out = job
    W = 256
    xb = tile_bounds(z, x, y)
    dst_tr = Affine((xb[2] - xb[0]) / W, 0, xb[0], 0, -(xb[3] - xb[1]) / W, xb[3])
    ll = lonlat(z, x, y)
    acc = np.zeros((3, W, W), np.float32)
    for f, tr, crs, b in SRC:
        if b[0] > ll[2] or b[2] < ll[0] or b[1] > ll[3] or b[3] < ll[1]: continue
        rgb = np.load(f)["rgb"]
        tmp = np.zeros((3, W, W), np.float32)
        reproject(rgb.astype(np.float32), tmp, src_transform=tr, src_crs=crs, src_nodata=0, dst_transform=dst_tr,
                  dst_crs="EPSG:3857", dst_nodata=0, resampling=Resampling.average if z < 7 else Resampling.bilinear)
        m = (acc[0] == 0) & (tmp[0] > 0)
        acc[:, m] = tmp[:, m]
    have = acc[0] > 0
    img = np.clip((acc.transpose(1, 2, 0) / 10000 * GAIN), 0, 1) ** GAMMA
    g = img.mean(axis=2, keepdims=True)
    img = np.clip(g + (img - g) * SAT, 0, 1) * 255
    e = dem(z, x, y)
    if e is None: e = np.full((W, W), -4000.0)
    refl = acc / 10000
    water = have & (refl[2] > refl[0]) & (refl.mean(axis=0) < 0.12)
    # Sea: below sea level and either outside the mosaic or water-looking (so the Turpan basin stays land).
    sea = (e < -40) | ((e <= 0) & (~have | water))
    img[sea] = sea_color(np.maximum(-e, 0))[sea]
    img[~sea & ~have] = np.array([112, 118, 84.])  # land outside the mosaic (far north and west)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.fromarray(img.astype(np.uint8)).save(out, quality=84, optimize=True)
    return out

if __name__ == "__main__":
    jobs = []
    if os.environ.get("Z9"):  # zoom 9 over China proper, from the finer source
        lon2x = lambda lon: int((lon + 180) / 360 * 512)
        lat2y = lambda lat: int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 512)
        for x in range(lon2x(95), lon2x(127) + 1):
            for y in range(lat2y(46), lat2y(18) + 1):
                jobs.append((9, x, y, f"tiles/9/{x}/{y}.jpg"))
        sys.argv = sys.argv[:1] + ["none"]
    for f in glob.glob(f"{HM}/tiles/terrarium/*/*/*.png") + glob.glob(f"{DEM}/*/*/*.png"):
        z, x, y = map(int, f[:-4].split("/")[-3:])
        if len(sys.argv) > 1 and str(z) not in sys.argv[1].split(","): continue
        jobs.append((z, x, y, f"tiles/{z}/{x}/{y}.jpg"))
    with ProcessPoolExecutor(os.cpu_count()) as ex:
        for i, _ in enumerate(ex.map(bake, jobs, chunksize=4)):
            if i % 200 == 0: print(i, len(jobs), flush=True)
    print("done", len(jobs))
