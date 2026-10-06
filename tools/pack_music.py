"""Pack background music (made by tools/ai_music.py) into data/music/<region>__<period>-<hash>.m4a (96 kbps AAC, with
macOS afconvert) and the index data/music.json ({"<region>/<period>": {"f": file}}), read by app.js. Upload with
tools/upload_assets.py music; data/music/ is not in git.

Usage: python3 tools/pack_music.py ~/Pictures/atlas-ai/music"""
import json, os, subprocess, sys, tempfile, zlib
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
SRC = sys.argv[1]

os.makedirs(P("data/music"), exist_ok=True)
index, files = {}, set()
for f in sorted(x for x in os.listdir(SRC) if x.endswith(".mp3") and "__" in x):
    key = f[:-4].replace("__", "/", 1)
    with tempfile.NamedTemporaryFile(suffix=".m4a") as tmp:
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "96000", os.path.join(SRC, f), tmp.name], check=True)
        data = open(tmp.name, "rb").read()
    name = f"{f[:-4]}-{zlib.crc32(data):08x}.m4a"
    if not os.path.exists(P("data/music", name)): open(P("data/music", name), "wb").write(data)
    files.add(name); index[key] = {"f": name}
for f in os.listdir(P("data/music")):
    if f not in files: os.remove(P("data/music", f))
json.dump(index, open(P("data/music.json"), "w"), separators=(",", ":"), sort_keys=True)
print(len(index), "tracks,", round(sum(os.path.getsize(P("data/music", f)) for f in files) / 1e6, 1), "MB")
