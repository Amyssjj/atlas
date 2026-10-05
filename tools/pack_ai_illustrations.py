"""Pack AI-generated event illustrations (made by tools/ai_illustrate.py) into data/ai/<event id>-<hash>.webp and the
index data/ai-illustrations.json, read by app.js, which shows them labelled as AI-generated.

Usage: python3 tools/pack_ai_illustrations.py OUT_DIR/openai
data/ai-illustrations-skip.json lists event ids whose picture was judged wrong or unsuitable.
One file per picture, so opening an event loads only its own; the file name carries a content hash because sw.js keeps
data/ai/ files forever under the same name. 960x640 stays sharp in the large event view (up to 900x600) on
high-density screens."""
import io, json, os, sys, zlib
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
SRC, BOX, MODEL = sys.argv[1], (960, 640), "GPT Image 2"

skip = set(json.load(open(P("data/ai-illustrations-skip.json")))) if os.path.exists(P("data/ai-illustrations-skip.json")) else set()
keys, images, files = {}, {}, set()
os.makedirs(P("data/ai"), exist_ok=True)
for f in sorted(x for x in os.listdir(SRC) if x.endswith((".png", ".webp"))):
    eid = f.rsplit(".", 1)[0]
    if eid in skip: continue
    im = Image.open(os.path.join(SRC, f)).convert("RGB")
    im.thumbnail(BOX, Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=60, method=6)
    name = f"{eid}-{zlib.crc32(buf.getvalue()):08x}.webp"
    if not os.path.exists(P("data/ai", name)): open(P("data/ai", name), "wb").write(buf.getvalue())
    files.add(name)
    images["ai-" + eid] = {"f": name, "page": eid, "ai": MODEL, "w": im.width, "h": im.height}
    keys["a:" + eid] = "ai-" + eid
for f in os.listdir(P("data/ai")):
    if f not in files: os.remove(P("data/ai", f))
json.dump({"keys": keys, "images": images}, open(P("data/ai-illustrations.json"), "w"), separators=(",", ":"))
size = sum(os.path.getsize(P("data/ai", f)) for f in files)
print(len(keys), "events,", round(size / 1e6, 1), "MB")
