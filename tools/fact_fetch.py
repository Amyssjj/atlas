"""Fetch reference facts for the fact check (run by .github/workflows/facts.yml, since Wikipedia and Wikidata are
reachable from GitHub's runners but not from the build machine).

For every event and person with an English Wikipedia `source`, and for every ruler (found by Wikipedia search), it
saves the page's Wikidata dates, coordinates, Chinese label and the opening paragraph of the article.

Writes <out>/facts.json: {"pages": {title: {...}}, "src": {source url: title}, "rulers": {key: [title, ...]}}.
tools/fact_check.py compares it with the data."""
import glob, json, os, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "Atlas/1.0 (https://github.com/daiyip/atlas; educational history map; fact check)"}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)
PREFIX = "https://en.wikipedia.org/wiki/"
WP, WD = "https://en.wikipedia.org/w/api.php", "https://www.wikidata.org/w/api.php"


def api(base, **q):
    q.update(format="json", formatversion=2)
    url = base + "?" + urllib.parse.urlencode(q)
    for i in range(6):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception as e:
            print("retry", e, file=sys.stderr); time.sleep(5 * (i + 1))
    return {}


def ruler_key(polity, r):
    return f"{polity}|{r['name']}|{r['from']}|{r['to']}"


# ---- what to look up
sources, rulers = set(), {}
for e in json.load(open(os.path.join(ROOT, "data/events.json"))):
    if str(e.get("source", "")).startswith(PREFIX): sources.add(e["source"])
for f in sorted(glob.glob(os.path.join(ROOT, "data/layers/*.json"))):
    L = json.load(open(f))
    for L in (L.values() if os.path.basename(f).startswith("world-") else [L]):
        for p in L.get("people", []):
            if str(p.get("source", "")).startswith(PREFIX): sources.add(p["source"])
        for polity, rs in (L.get("rulers") or {}).items():
            for r in rs:
                q = r.get("title") if r.get("title") and r.get("title") != r["name"] and not r.get("rank") else f"{r['name']} {polity}"
                rulers[ruler_key(polity, r)] = q
src_title = {u: urllib.parse.unquote(u[len(PREFIX):].split("#")[0]).replace("_", " ") for u in sources}
print(len(sources), "sources,", len(rulers), "rulers", flush=True)

pages = {}  # resolved title -> {"qid", "extract"}
src_map = {}


def take(q, back=None):
    """Record pages from a query result; returns {asked title: resolved title}."""
    back = back or {}
    for k in ("normalized", "redirects"):
        for x in q.get(k, []): back[x["to"]] = back.get(x["from"], x["from"])
    got = {}
    for pg in q.get("pages", []):
        if pg.get("missing") or pg.get("invalid"): continue
        t = pg["title"]
        cur = pages.setdefault(t, {})
        if pg.get("pageprops", {}).get("wikibase_item"): cur["qid"] = pg["pageprops"]["wikibase_item"]
        if pg.get("extract"): cur["extract"] = pg["extract"][:1500]
        if "disambiguation" in pg.get("pageprops", {}): cur["disambig"] = True
        src = t
        while src in back: src = back[src]
        got[src] = t
    return got


# ---- source pages: Wikidata id + intro (extracts allow 20 pages per call)
titles = sorted(set(src_title.values()))
for i in range(0, len(titles), 20):
    chunk = titles[i:i + 20]
    d = api(WP, action="query", titles="|".join(chunk), redirects=1, prop="pageprops|extracts",
            exintro=1, explaintext=1, exlimit=20)
    got = take(d.get("query", {}))
    for u, t in src_title.items():
        if t in got: src_map[u] = got[t]
    if i % 400 == 0: print("pages", i, flush=True)
    time.sleep(0.2)

# ---- rulers: top three search hits with their intros
ruler_hits = {}
for n, (key, q) in enumerate(sorted(rulers.items())):
    d = api(WP, action="query", generator="search", gsrsearch=q, gsrlimit=3, prop="pageprops|extracts",
            exintro=1, explaintext=1, exlimit=3)
    qq = d.get("query", {})
    take(qq)
    hits = sorted(qq.get("pages", []), key=lambda p: p.get("index", 9))
    ruler_hits[key] = [p["title"] for p in hits if not p.get("missing")]
    if n % 200 == 0: print("rulers", n, flush=True)
    time.sleep(0.1)

# ---- Wikidata: dates, coordinates, positions held, Chinese labels
def tval(v):
    try:
        t = v["time"]; y = int(t[:t.index("-", 1)])
        return [y, v.get("precision", 9)]
    except Exception:
        return None

qids = sorted({p["qid"] for p in pages.values() if p.get("qid")})
wd = {}
for i in range(0, len(qids), 50):
    d = api(WD, action="wbgetentities", ids="|".join(qids[i:i + 50]), props="claims|labels",
            languages="zh|zh-hans|zh-cn|zh-hant|en")
    for q, ent in (d.get("entities") or {}).items():
        c = ent.get("claims", {})
        out = {}
        for p in ("P585", "P580", "P582", "P569", "P570", "P571", "P576"):
            vals = [tval(s["mainsnak"].get("datavalue", {}).get("value", {})) for s in c.get(p, []) if s["mainsnak"].get("datavalue")]
            vals = [v for v in vals if v]
            if vals: out[p] = vals
        for s in c.get("P625", [])[:1]:
            v = s["mainsnak"].get("datavalue", {}).get("value")
            if v: out["coord"] = [round(v["longitude"], 3), round(v["latitude"], 3)]
        held = []
        for s in c.get("P39", []):
            qual = s.get("qualifiers", {})
            st = [tval(x.get("datavalue", {}).get("value", {})) for x in qual.get("P580", []) if x.get("datavalue")]
            en = [tval(x.get("datavalue", {}).get("value", {})) for x in qual.get("P582", []) if x.get("datavalue")]
            if st or en: held.append([st[0] if st else None, en[0] if en else None])
        if held: out["held"] = held
        labels = ent.get("labels", {})
        zh = [labels[k]["value"] for k in ("zh-hans", "zh-cn", "zh", "zh-hant") if k in labels]
        if zh: out["zh"] = sorted(set(zh))
        if "en" in labels: out["en"] = labels["en"]["value"]
        wd[q] = out
    if i % 1000 == 0: print("wikidata", i, flush=True)
    time.sleep(0.2)
for p in pages.values():
    if p.get("qid") in wd: p["wd"] = wd[p["qid"]]

json.dump({"pages": pages, "src": src_map, "rulers": ruler_hits}, open(os.path.join(OUT, "facts.json"), "w"),
          ensure_ascii=False)
print("done", len(pages), "pages,", len(wd), "wikidata items")
