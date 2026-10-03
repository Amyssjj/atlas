"""Check every English Wikipedia `source` link of events and people (run by .github/workflows/links.yml, since
Wikipedia is reachable from GitHub's runners but not from the build machine).

Writes <out>/links.json: {url: {"ok": bool, "title": resolved title, "zh": Chinese Wikipedia title or null,
"disambig": bool, "suggest": [top search hits when the page is missing or a disambiguation page]}}.
tools/apply_links.py reads it back."""
import glob, json, os, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "DynastyAtlas/1.0 (https://github.com/daiyip/atlas; educational history map)"}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)
PREFIX = "https://en.wikipedia.org/wiki/"

def api(**q):
    q.update(format="json", formatversion=2)
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(q)
    for i in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception as e:
            print("retry", e, file=sys.stderr); time.sleep(5 * (i + 1))
    return {}

urls = set()
for e in json.load(open(os.path.join(ROOT, "data/events.json"))):
    if str(e.get("source", "")).startswith(PREFIX): urls.add(e["source"])
for f in glob.glob(os.path.join(ROOT, "data/layers/*.json")):
    for p in json.load(open(f)).get("people", []):
        if str(p.get("source", "")).startswith(PREFIX): urls.add(p["source"])
title_of = {u: urllib.parse.unquote(u[len(PREFIX):].split("#")[0]).replace("_", " ") for u in urls}
print(len(urls), "links")

res = {}
titles = sorted(set(title_of.values()))
info = {}
for i in range(0, len(titles), 50):
    chunk = titles[i:i + 50]
    d = api(action="query", titles="|".join(chunk), redirects=1, prop="pageprops|langlinks", lllang="zh", lllimit="max")
    q = d.get("query", {})
    back = {}
    for k in ("normalized", "redirects"):
        for x in q.get(k, []): back[x["to"]] = back.get(x["from"], x["from"])
    for pg in q.get("pages", []):
        src = pg["title"]
        while src in back: src = back[src]
        info[src] = {"ok": not pg.get("missing") and not pg.get("invalid"), "title": pg["title"],
                     "disambig": "disambiguation" in pg.get("pageprops", {}),
                     "zh": (pg.get("langlinks") or [{}])[0].get("title")}
    time.sleep(0.3)
for u, t in title_of.items():
    r = dict(info.get(t, {"ok": False, "title": t, "disambig": False, "zh": None}))
    if not r["ok"] or r["disambig"]:
        d = api(action="query", list="search", srsearch=t, srlimit=3)
        r["suggest"] = [x["title"] for x in d.get("query", {}).get("search", [])]
        time.sleep(0.2)
    res[u] = r
json.dump(res, open(os.path.join(OUT, "links.json"), "w"), ensure_ascii=False, indent=1)
print(sum(not r["ok"] for r in res.values()), "missing,", sum(r["disambig"] for r in res.values()), "disambiguation pages")
