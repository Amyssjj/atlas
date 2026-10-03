"""Turn the `illustrations-raw` branch (made by .github/workflows/illustrations.yml) into data/illustrations.json and
data/img/<bucket>.json (WebP data URLs, loaded on demand by app.js).

Usage: git -C <repo> fetch origin illustrations-raw && git -C <repo> worktree add /tmp/raw origin/illustrations-raw
       python3 tools/pack_illustrations.py /tmp/raw
       python3 tools/pack_illustrations.py /tmp/raw --merge
An image that more than MAX_SHARED events share (a dynasty overview page, say) is left off those events as too generic.
data/illustrations-skip.json lists keys to leave without a picture (wrong or unsuitable images).
--merge keeps pictures already in data/ and only adds keys from this raw checkout (for a few new artifact pages
without re-packing the whole set)."""
import base64, collections, io, json, os, sys, zlib
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
RAW = sys.argv[1]
MERGE = "--merge" in sys.argv[2:]
BUCKETS, MAX_SHARED, BOX = 12, 3, (320, 280)

meta = json.load(open(os.path.join(RAW, "meta.json")))
skip = set(json.load(open(P("data/illustrations-skip.json")))) if os.path.exists(P("data/illustrations-skip.json")) else set()
uses = collections.Counter(m["file"] for k, m in meta.items() if k.startswith("e:"))
if MERGE and os.path.exists(P("data/illustrations.json")):
    prev = json.load(open(P("data/illustrations.json")))
    keys, images = dict(prev.get("keys", {})), dict(prev.get("images", {}))
    buckets = collections.defaultdict(dict)
    for b in range(BUCKETS):
        path = P(f"data/img/{b}.json")
        if os.path.exists(path): buckets[b].update(json.load(open(path)))
else:
    keys, images, buckets = {}, {}, collections.defaultdict(dict)
for key, m in sorted(meta.items()):
    if key in skip or (key.startswith("e:") and uses[m["file"]] > MAX_SHARED): continue
    iid = format(zlib.crc32(m["file"].encode()), "08x")
    if iid not in images:
        try:
            im = Image.open(os.path.join(RAW, "raw", m["img"]))
            im.load()
        except Exception as e:
            print("bad image", m["file"], e); continue
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA"); bg = Image.new("RGBA", im.size, "white"); bg.alpha_composite(im); im = bg
        im = im.convert("RGB"); im.thumbnail(BOX, Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "WEBP", quality=62, method=6)
        b = int(iid, 16) % BUCKETS
        buckets[b][iid] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
        url = m.get("credit_url") or f"https://commons.wikimedia.org/wiki/File:{m['file']}"
        images[iid] = {"b": b, "page": m["page"], "license": m["license"], "artist": m["artist"], "url": url, "w": im.width, "h": im.height}
    keys[key] = iid
os.makedirs(P("data/img"), exist_ok=True)
if not MERGE:
    for f in os.listdir(P("data/img")): os.remove(P("data/img", f))
used = set(keys.values())
for b, d in buckets.items():
    path = P(f"data/img/{b}.json")
    payload = json.dumps({i: u for i, u in d.items() if i in used}, separators=(",", ":"))
    old = open(path).read() if os.path.exists(path) else None
    if old != payload:
        open(path, "w").write(payload)
json.dump({"keys": keys, "images": images}, open(P("data/illustrations.json"), "w"), ensure_ascii=False, separators=(",", ":"))
size = sum(os.path.getsize(P("data/img", f)) for f in os.listdir(P("data/img")))
print(len(keys), "keys,", len(images), "images,", sum(k.startswith("p:") for k in keys), "people,",
      sum(k.startswith("e:") for k in keys), "events,", round(size / 1e6, 1), "MB")
