"""Pack tiles into archives: at z7-8 one file per 8x8 block of tiles, z9 per 16x16; below z7 (only with --all) one file per zoom.
Usage: python3 tools/pack_tiles.py <dir of z/x/y.png tiles> tiles/pack          (elevation, z7-8)
       python3 tools/pack_tiles.py <dir of z/x/y.jpg tiles> tiles/sat --all    (satellite imagery, z2-8)
Archive: 4-byte little-endian length N, N bytes of JSON index {"x/y": [offset, length]}, then the PNGs (offsets
relative to the start of the PNG data). Each archive is wrapped in a valid 1x1 PNG as a private 'tpAk' chunk."""
import glob, json, os, struct, sys, zlib

def chunk(t, d):
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)
groups = {}
ALL = "--all" in sys.argv
for f in glob.glob(f"{SRC}/*/*/*.png") + glob.glob(f"{SRC}/*/*/*.jpg"):
    z, x, y = map(int, f[:-4].split("/")[-3:])
    if z < 7 and not ALL: continue
    sh = 4 if z >= 9 else 3 if z >= 7 else z  # z7 -> z4, z8 -> z5, z9 -> z5; lower zooms: whole zoom in one archive
    groups.setdefault((z, x >> sh, y >> sh), []).append((x, y, f))
total = 0
for (z, px, py), tiles in sorted(groups.items()):
    idx, blobs, off = {}, [], 0
    for x, y, f in sorted(tiles):
        b = open(f, "rb").read()
        idx[f"{x}/{y}"] = [off, len(b)]; blobs.append(b); off += len(b)
    head = json.dumps(idx, separators=(",", ":")).encode()
    data = struct.pack("<I", len(head)) + head + b"".join(blobs)
    with open(f"{DST}/{z}-{px}-{py}.png", "wb") as o:
        o.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)) + chunk(b"tpAk", data)
                + chunk(b"IDAT", zlib.compress(b"\x00\x00")) + chunk(b"IEND", b""))
    total += off
print(len(groups), "archives", total // 2**20, "MB")
