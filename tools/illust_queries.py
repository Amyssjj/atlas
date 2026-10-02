"""Write tools/illust_queries.json: one Wikipedia page per person, event and map point, for tools/fetch_illustrations.py.
Keys are "p:<person>", "e:<event>", "f:<faith>", "i:<invention>", "s:<pass>", "r:<road>", "w:<wall>", "c:<clan>".
`zh` is a Chinese title tried when the English page has no free image.
`prefer` "artifact" marks a site, tomb or excavated object: the fetcher then looks for an object photograph.
The same test lives in app.js (isArtifactEntry), so the picture a pin asks for is the one the fetcher tried to pack."""
import glob, json, os, re, urllib.parse
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
ART = re.compile(r"遗址|出土|墓葬|马王堆|三星堆|石峁|兵马俑|甲骨|方尊|竹简|简牍|金印|牙璋|漆棺|编钟|青铜")
ART_PLACE = re.compile(r"出土|墓葬|遗址|三星堆|石峁|马王堆")
def page(url):
    m = re.match(r"https?://(\w+)\.wikipedia\.org\/wiki\/(.+)", url or "")
    return (m.group(1), urllib.parse.unquote(m.group(2)).replace("_", " ")) if m else (None, None)
def blob(o):
    return "\n".join(str(o.get(k) or "") for k in ("title", "title_zh", "name", "name_zh", "summary", "summary_zh", "place", "place_zh", "note", "note_zh"))
def artifact(o):
    text = blob(o)
    if not ART.search(text): return False
    if o.get("category") in ("war", "diplomacy", "rebellion") and not ART_PLACE.search(text): return False
    return True
def add(out, key, obj):
    wiki, title = page(obj.get("source"))
    if not title: return
    q = {"wiki": wiki, "title": title, "zh": obj.get("name_zh") or obj.get("title_zh")}
    # Event headlines are not Wikipedia titles; only a person's name is a safe Chinese fallback.
    if key.startswith("e:"): q["zh"] = None
    # A person always wants a portrait. Artifact preference is for the place or the object itself.
    if artifact(obj) and not key.startswith("p:"): q["prefer"] = "artifact"
    out[key] = q
out = {}
for f in sorted(glob.glob(P("data/layers/*.json"))):
    for p in json.load(open(f)).get("people", []):
        add(out, "p:" + p["id"], p)
for e in json.load(open(P("data/events.json"))):
    add(out, "e:" + e["id"], e)
for kind, prefix, path in (
    ("faith", "f:", "data/overlays.json"),
    ("inventions", "i:", "data/overlays.json"),
):
    for item in json.load(open(P(path))).get(kind, []):
        add(out, prefix + item["id"], item)
for prefix, path in (("s:", "data/passes.json"), ("r:", "data/roads.json"), ("w:", "data/walls.json"), ("c:", "data/clans.json")):
    for item in json.load(open(P(path))):
        add(out, prefix + item["id"], item)
json.dump(out, open(P("tools/illust_queries.json"), "w"), ensure_ascii=False, indent=0)
pref = sum(1 for v in out.values() if v.get("prefer") == "artifact")
print(len(out), "queries,", len({(v["wiki"], v["title"]) for v in out.values()}), "pages,", pref, "artifact")
