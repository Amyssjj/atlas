"""Write tools/illust_queries.json: one Wikipedia page per person and event, for tools/fetch_illustrations.py.
Keys are "p:<person id>" and "e:<event id>"; `zh` is a Chinese title tried when the English page has no free image."""
import glob, json, os, re, urllib.parse
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
def page(url):
    m = re.match(r"https?://(\w+)\.wikipedia\.org/wiki/(.+)", url or "")
    return (m.group(1), urllib.parse.unquote(m.group(2)).replace("_", " ")) if m else (None, None)
out = {}
for f in sorted(glob.glob(P("data/layers/*.json"))):
    L = json.load(open(f))
    for p in [p for x in (L.values() if "/world-" in f else [L]) for p in x.get("people", [])]:
        wiki, title = page(p.get("source"))
        if title: out["p:" + p["id"]] = {"wiki": wiki, "title": title, "zh": p.get("name_zh")}
for e in json.load(open(P("data/events.json"))):
    wiki, title = page(e.get("source"))
    if title: out["e:" + e["id"]] = {"wiki": wiki, "title": title, "zh": None}
json.dump(out, open(P("tools/illust_queries.json"), "w"), ensure_ascii=False, indent=0)
print(len(out), "queries,", len({(v["wiki"], v["title"]) for v in out.values()}), "pages")
