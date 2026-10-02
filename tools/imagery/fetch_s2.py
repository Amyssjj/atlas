# Download Sentinel-2 L2A 120m mosaic (2020, Aug 12 period) RGB bands at 480m (COG overview 4) for 60-145E, 8-56N.
import rasterio, numpy as np, os, sys
from concurrent.futures import ThreadPoolExecutor
from rasterio.enums import Resampling
BASE = "https://sentinel-s2-l2a-mosaic-120.s3.amazonaws.com/2020/8/12/"
F = int(sys.argv[1]) if len(sys.argv) > 1 else 4
def one(gzd):
    out = f"src/{gzd}-{F}.npz"
    if os.path.exists(out): return gzd, "cached"
    bands = []
    try:
        for b in ("B04", "B03", "B02"):
            with rasterio.open(BASE + gzd + "/" + b + ".tif") as d:
                h, w = d.height // F, d.width // F
                bands.append(d.read(1, out_shape=(h, w), resampling=Resampling.average))
                tr = d.transform * d.transform.scale(d.width / w, d.height / h); crs = d.crs.to_string()
    except Exception as e:
        return gzd, "missing " + str(e)[:80]
    np.savez_compressed(out, rgb=np.stack(bands), transform=np.array(tr)[:6], crs=crs)
    return gzd, "ok"
gzds = [f"{z}{b}" for z in range(37, 58) for b in "MNPQRSTUV"]
os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"
with ThreadPoolExecutor(12) as ex:
    for g, s in ex.map(one, gzds): print(g, s, flush=True)
