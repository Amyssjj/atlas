"""Download a free-licensed lead image for each entry of tools/illust_queries.json (run by .github/workflows/illustrations.yml,
since Wikimedia is reachable from GitHub's runners). Writes out/raw/<n>.<ext> thumbnails and out/meta.json
{key: {file, page, wiki, license, artist, credit_url, img}}. Only public-domain and CC images are kept; fair-use files are skipped."""
import html, json, os, re, sys, time, urllib.parse, urllib.request
UA = {"User-Agent": "DynastyAtlas/1.0 (https://github.com/daiyip/atlas; educational history map)"}
FREE = re.compile(r"public domain|^pd|cc0|cc[- ]by|gfdl|attribution", re.I)
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
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

queries = json.load(open("tools/illust_queries.json"))
meta, got = {}, {}
def run(wiki, wanted):
    """wanted: {key: title}. Fills meta for keys whose page has a free lead image."""
    leads = lead_images(wiki, sorted(set(wanted.values())))
    infos = file_info(wiki, sorted({f for _, f in leads.values()}))
    for key, title in wanted.items():
        if title not in leads: continue
        page, f = leads[title]
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
