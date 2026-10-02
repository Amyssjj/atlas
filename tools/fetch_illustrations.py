"""Download a free-licensed image for each entry of tools/illust_queries.json (run by .github/workflows/illustrations.yml,
since Wikimedia is reachable from GitHub's runners). Writes out/raw/<n>.<ext> thumbnails and out/meta.json
{key: {file, page, wiki, license, artist, credit_url, img}}. Only public-domain and CC images are kept; fair-use files are skipped.

A query with "prefer": "artifact" (a site, tomb or excavated object) picks an object photograph from the article
when it has one — a jade, a bronze, a tomb find — instead of a locator map. Pages with no lead image fall back to
the first usable photograph. Usage: python3 tools/fetch_illustrations.py <out dir> [queries.json]"""
import html, json, os, re, sys, time, urllib.parse, urllib.request
UA = {"User-Agent": "DynastyAtlas/1.0 (https://github.com/daiyip/atlas; educational history map)"}
FREE = re.compile(r"public domain|^pd|cc0|cc[- ]by|gfdl|attribution", re.I)
# Icons, maps and diagrams are not what a pin should stand up. "map" as a word, so "Gold mask" is kept.
SKIP_FILE = re.compile(r"(\.svg$|\bicon\b|\blogo\b|\bflag\b|\blocator\b|\blocation map\b|\brelief\b|\bpog\b|\bdot\b|\bsymbol\b|commons-logo|\bambox\b|\bwikidata\b|\bdiagram\b|\bchart\b|\bhaplogroup\b|people icon|red pog|orange dot|question book|\bplan of\b|\bmap\b)", re.I)
PHOTO = re.compile(r"\.(jpe?g|png|gif|webp)$", re.I)
ART_FILE = re.compile(r"出土|unearthed|excavated|玉|鼎|尊|俑|青铜|面具|牙璋|漆|编钟|甲骨|简|金缕|mask|jade|bronze|tomb|ding|zun|lacquer|oracle|pottery|ceramic|artifact|relic|statue|sculpture|yazhang|gold|coffin|silk|inscription", re.I)
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
QUERIES = sys.argv[2] if len(sys.argv) > 2 else "tools/illust_queries.json"
os.makedirs(OUT + "/raw", exist_ok=True)

def api(wiki, **q):
    q.update(format="json", formatversion=2)
    url = f"https://{wiki}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(q)
    for i in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception as e:
            print("retry", e, file=sys.stderr); time.sleep(5 * (i + 1))
    return {}

def resolve_titles(wiki, titles):
    """requested title -> title to query. A missing page tries one near-match (fixes capitalisation)."""
    titles = list(dict.fromkeys(titles))
    res = {t: t for t in titles}
    missing = []
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        d = api(wiki, action="query", titles="|".join(chunk), redirects=1)
        q = d.get("query", {})
        back = {}
        for k in ("normalized", "redirects"):
            for x in q.get(k, []): back[x["to"]] = back.get(x["from"], x["from"])
        for pg in q.get("pages", []):
            if "missing" not in pg: continue
            src = pg["title"]
            while src in back: src = back[src]
            missing.append(src)
        time.sleep(0.3)
    for t in missing:
        d = api(wiki, action="query", list="search", srsearch=t, srwhat="nearmatch", srlimit=1)
        hits = (d.get("query") or {}).get("search") or []
        if hits and hits[0]["title"] != t:
            res[t] = hits[0]["title"]
            print("nearmatch", t, "->", hits[0]["title"], file=sys.stderr)
        time.sleep(0.25)
    return res

def lead_images(wiki, titles):
    """title -> (resolved page title, File name) for pages that have a lead image and are not disambiguation pages."""
    res = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        d = api(wiki, action="query", titles="|".join(chunk), prop="pageimages|pageprops", piprop="name", redirects=1)
        q = d.get("query", {})
        back = {}
        for k in ("normalized", "redirects"):
            for x in q.get(k, []): back[x["to"]] = back.get(x["from"], x["from"])
        for pg in q.get("pages", []):
            if "pageimage" not in pg or "disambiguation" in pg.get("pageprops", {}): continue
            src = pg["title"]
            while src in back: src = back[src]
            res[src] = (pg["title"], pg["pageimage"])
        time.sleep(0.5)
    return res

def image_lists(wiki, titles):
    """title -> [File name without the File: prefix], following redirects back to the requested title."""
    res = {}
    for i in range(0, len(titles), 20):
        chunk = titles[i:i + 20]
        d = api(wiki, action="query", titles="|".join(chunk), prop="images", imlimit=50, redirects=1)
        q = d.get("query", {})
        back = {}
        for k in ("normalized", "redirects"):
            for x in q.get(k, []): back[x["to"]] = back.get(x["from"], x["from"])
        for pg in q.get("pages", []):
            if pg.get("missing") == "" or "images" not in pg: continue
            src = pg["title"]
            while src in back: src = back[src]
            res[src] = [im["title"].split(":", 1)[-1] for im in pg.get("images", [])]
        time.sleep(0.4)
    return res

def file_score(name, page_title, prefer):
    """None if the file is not a usable photograph. Higher is a better artifact picture."""
    if not PHOTO.search(name) or SKIP_FILE.search(name): return None
    if prefer != "artifact": return 1
    s = 1
    if re.search(r"出土|unearthed|excavated", name, re.I): s += 6
    stem = (page_title or "").split("(")[0].strip().lower()
    if stem and stem in name.lower(): s += 3
    if ART_FILE.search(name): s += 2
    # A comparison plate that names several cultures is a worse stand-in for one site.
    if name.count(",") >= 2 and not re.search(r"出土|unearthed", name, re.I): s -= 3
    return s

def choose_file(lead, files, prefer, page_title):
    """lead is a File name or None. Artifact queries want an object photo; everyone else keeps the lead image."""
    if prefer != "artifact" and lead and file_score(lead, page_title, None) is not None:
        return lead
    best, bests = None, -1
    seen = set()
    for f in ([lead] if lead else []) + list(files or []):
        if not f: continue
        k = f.replace("_", " ")
        if k in seen: continue
        seen.add(k)
        sc = file_score(f, page_title, prefer)
        if sc is None or sc <= bests: continue
        best, bests = f, sc
    if prefer == "artifact" and bests < 5:
        # A filename that merely says "bronze" should not replace the article's own lead photograph.
        # Override only for a clearly better find (excavated, or the site's name on an object photo).
        if lead and file_score(lead, page_title, None) is not None: return lead
        return best if bests >= 1 else None
    return best

def file_info(wiki, names):
    res = {}
    for i in range(0, len(names), 50):
        chunk = names[i:i + 50]
        d = api(wiki, action="query", titles="|".join("File:" + n for n in chunk), prop="imageinfo",
                iiprop="url|extmetadata|mime", iiurlwidth=320)
        for pg in d.get("query", {}).get("pages", []):
            ii = (pg.get("imageinfo") or [None])[0]
            if not ii: continue
            m = {k: v.get("value", "") for k, v in ii.get("extmetadata", {}).items()}
            lic = m.get("LicenseShortName") or m.get("License") or ""
            if m.get("NonFree", "").lower() == "true" or not FREE.search(lic): continue
            artist = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.get("Artist", "")))).strip()[:120]
            res[pg["title"].split(":", 1)[1].replace(" ", "_")] = {"thumb": ii.get("thumburl") or ii["url"], "license": lic,
                "artist": artist, "credit_url": ii.get("descriptionurl"), "mime": ii.get("mime")}
        time.sleep(0.5)
    return res

queries = json.load(open(QUERIES))
meta, got = {}, {}
def run(wiki, wanted):
    """wanted: {key: title}. Fills meta for keys whose page has a free image."""
    mapping = resolve_titles(wiki, wanted.values())
    wanted = {k: mapping.get(t, t) for k, t in wanted.items()}
    leads = lead_images(wiki, sorted(set(wanted.values())))
    need = []
    for key, title in wanted.items():
        if queries.get(key, {}).get("prefer") == "artifact" or title not in leads:
            need.append(title)
    lists = image_lists(wiki, sorted(set(need))) if need else {}
    chosen = {}
    for key, title in wanted.items():
        lead = leads.get(title)
        lead_file = lead[1] if lead else None
        page = lead[0] if lead else title
        prefer = queries.get(key, {}).get("prefer")
        f = choose_file(lead_file, lists.get(title, []), prefer, page)
        if f: chosen[key] = (page, f)
    infos = file_info(wiki, sorted({f for _, f in chosen.values()}))
    for key, (page, f) in chosen.items():
        info = infos.get(f.replace(" ", "_"))
        if not info: continue
        if f not in got:
            ext = {"image/png": "png", "image/gif": "gif"}.get(info["mime"], "jpg")
            if info["mime"] == "image/svg+xml": ext = "png"
            name = f"{len(got)}.{ext}"
            try:
                data = urllib.request.urlopen(urllib.request.Request(info["thumb"], headers=UA), timeout=60).read()
                open(f"{OUT}/raw/{name}", "wb").write(data); got[f] = name
            except Exception as e:
                print("skip", f, e, file=sys.stderr); continue
            time.sleep(0.2)
        meta[key] = {"img": got[f], "file": f, "page": page, "wiki": wiki, "license": info["license"],
                     "artist": info["artist"], "credit_url": info["credit_url"]}

for wiki in sorted({q["wiki"] for q in queries.values()}):
    run(wiki, {k: q["title"] for k, q in queries.items() if q["wiki"] == wiki})
print(len(meta), "with images after first pass", file=sys.stderr)
run("zh", {k: q["zh"] for k, q in queries.items() if k not in meta and q.get("zh")})
print(len(meta), "with images,", len(got), "files", file=sys.stderr)
json.dump(meta, open(OUT + "/meta.json", "w"), ensure_ascii=False, indent=0)
