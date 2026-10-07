"""Evidence for checking the newer AI-drafted data against Wikipedia: run by .github/workflows/facts.yml with `more`,
since Wikipedia is reachable from GitHub's runners but not from the build machine.

It covers four data sets:
- life journeys (data/lives.json): for every stop, passages from the person's whole English and Chinese articles that
  mention the stop's year or its place;
- ties (data/relations.json): for every link, passages of each person's article that name the other person;
- climate and disasters (data/climate.json): the disaster's own article (source, else the best search hit for its
  name, in both languages) and those of its linked events, with the opening text and the passages naming its years;
  for the warm and cold periods, passages from a few climate-history articles;
- economy (data/economy.json): for every snapshot, passages naming its year, reign or record from articles about the
  census or record it cites and about China's historical population and finances.

Writes <out>/more.json: {"lives": {"<life id>#<step>": rec}, "ties": {"<a>|<b>": rec}, "disasters": {id: rec},
"periods": {id: rec}, "economy": {"<metric>|<year>": rec}}, each rec {"src": [titles], "p": [passage, ...], "intro"?}.
Reviewed verdicts go in tools/more_verdicts.json; tools/apply_more.py writes them into the data."""
import glob, json, os, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "Atlas/1.0 (https://github.com/daiyip/atlas; educational history map; fact check)"}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)
EN, ZH = "https://en.wikipedia.org/wiki/", "https://zh.wikipedia.org/wiki/"
API = {"en": "https://en.wikipedia.org/w/api.php", "zh": "https://zh.wikipedia.org/w/api.php"}
W = 170  # characters kept on each side of a hit


def api(lang, **q):
    q.update(format="json", formatversion=2)
    url = API[lang] + "?" + urllib.parse.urlencode(q)
    for i in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception as e:
            print("retry", e, file=sys.stderr); time.sleep(4 * (i + 1))
    return {}


def title_of(url, prefix):
    return urllib.parse.unquote(url[len(prefix):].split("#")[0]).replace("_", " ") if str(url or "").startswith(prefix) else None


cache, search_cache = {}, {}


def article(lang, title):
    """(plain text, resolved title) of a whole article, following redirects; zh in simplified. ("", None) if none."""
    if not title: return "", None
    k = (lang, title)
    if k not in cache:
        q = dict(action="query", titles=title, redirects=1, prop="extracts|pageprops", explaintext=1)
        if lang == "zh": q["variant"] = "zh-cn"
        pg = (api(lang, **q).get("query", {}).get("pages") or [{}])[0]
        ok = pg.get("extract") and not pg.get("missing") and "disambiguation" not in pg.get("pageprops", {})
        cache[k] = (pg["extract"], pg["title"]) if ok else ("", None)
        time.sleep(0.03)
    return cache[k]


def search(lang, q, n=1):
    k = (lang, q, n)
    if k not in search_cache:
        r = api(lang, action="query", list="search", srsearch=q, srlimit=n, srnamespace=0)
        search_cache[k] = [h["title"] for h in r.get("query", {}).get("search", [])]
    return search_cache[k]


def year_re(y, lang):
    if lang == "zh":
        return rf"(?:前|公元前){-y}年" if y < 0 else rf"(?<![\d前]){y}年"
    if y < 0:
        return rf"(?<![\d,]){-y}(?:\s)?(?:–\s*\d+\s*)?(?:BC|BCE|B\.C\.)|(?<![\d,]){-y}\s*[–-]\s*\d+\s*(?:BC|BCE)"
    return rf"(?<![\d,.]){y}(?![\d,])"


def hits(text, pattern, lang, limit=3):
    out = []
    for m in re.finditer(pattern, text):
        a, b = max(0, m.start() - W), min(len(text), m.end() + W)
        out.append(f"[{lang}] " + text[a:b].replace("\n", " "))
        if len(out) == limit: break
    return out


def merge(ps):
    """Drop passages that repeat one already kept (overlapping windows)."""
    out = []
    for p in ps:
        if not any(p[6:80] in q or q[6:80] in p for q in out): out.append(p)
    return out


def words(*names):
    """Search terms for a place or person name: the whole name and its parts before brackets and separators."""
    out = []
    for n in names:
        if not n: continue
        for part in re.split(r"[（）()、，,/;；]| or |及|与", n):
            part = part.strip(" .")
            part = re.sub(r"^(?:near|modern|today's|今)\s*", "", part)
            if len(part) >= 2 and part not in out and not part.isdigit(): out.append(part)
    return out[:4]


def esc(w):
    return re.escape(w) if re.search(r"[一-鿿]", w) else r"\b" + re.escape(w) + r"\b"


# ---- people: id -> (en title, zh title)
people = {}
for f in sorted(glob.glob(os.path.join(ROOT, "data/layers/*.json"))):
    D = json.load(open(f))
    for L in (D.values() if os.path.basename(f).startswith("world-") else [D]):
        for p in L.get("people", []):
            if p.get("id") and p["id"] not in people:
                people[p["id"]] = (title_of(p.get("source"), EN) or p["name"], title_of(p.get("source_zh"), ZH) or p.get("name_zh"), p)


def texts(pid):
    en, zh, _ = people.get(pid, (None, None, None))
    return [(lang, *article(lang, t)) for lang, t in (("en", en), ("zh", zh))]


more = {"lives": {}, "ties": {}, "disasters": {}, "periods": {}, "economy": {}}

# ---- life journeys
lives = json.load(open(os.path.join(ROOT, "data/lives.json")))
for n, life in enumerate(lives):
    arts = texts(life["person"])
    src = [t for _, _, t in arts if t]
    for i, s in enumerate(life["steps"]):
        ps = []
        for lang, text, t in arts:
            if not t: continue
            ps += hits(text, year_re(s["year"], lang), lang)
            for w in words(s.get("place_zh") if lang == "zh" else s.get("place")):
                ps += hits(text, esc(w), lang, 2)
        more["lives"][f"{life['id']}#{i}"] = {"src": src, "p": merge(ps)[:8]}
    if n % 20 == 0: print("lives", n, flush=True)

# ---- ties
R = json.load(open(os.path.join(ROOT, "data/relations.json")))
for n, l in enumerate(R["links"]):
    ps, src = [], []
    for me, other in ((l["a"], l["b"]), (l["b"], l["a"])):
        o = R["people"].get(other) or {}
        op = people.get(other, (None, None, {}))[2] or {}
        for lang, text, t in texts(me):
            if not t: continue
            src.append(t)
            names = [o.get("name_zh") or op.get("name_zh")] if lang == "zh" else words(o.get("name") or op.get("name"))[:2]
            for w in names:
                if w: ps += hits(text, esc(w), lang, 3)
    more["ties"][f"{l['a']}|{l['b']}"] = {"src": src, "p": merge(ps)[:8]}
    if n % 100 == 0: print("ties", n, flush=True)

# ---- disasters and climate periods
C = json.load(open(os.path.join(ROOT, "data/climate.json")))
events = {e["id"]: e for e in json.load(open(os.path.join(ROOT, "data/events.json")))}
for d in C["disasters"]:
    cands = [("en", title_of(d.get("source"), EN)), ("zh", title_of(d.get("source_zh"), ZH))]
    if not d.get("source"): cands += [("en", t) for t in search("en", d["name"])]
    cands += [("zh", t) for t in search("zh", d["name_zh"])]
    for eid in d.get("events", [])[:2]:
        e = events.get(eid) or {}
        cands += [("en", title_of(e.get("source"), EN)), ("zh", title_of(e.get("source_zh"), ZH))]
    rec, seen = {"src": [], "p": [], "intro": []}, set()
    for lang, t in cands:
        text, title = article(lang, t)
        if not title or (lang, title) in seen: continue
        seen.add((lang, title)); rec["src"].append(f"{lang}:{title}")
        rec["intro"].append(f"[{lang}:{title}] " + text[:900].replace("\n", " "))
        for y in sorted({d["from"], d["to"]}):
            rec["p"] += hits(text, year_re(y, lang), lang, 3)
    rec["p"] = merge(rec["p"])[:10]
    more["disasters"][d["id"]] = rec
print("disasters done", flush=True)
CLIMATE = [("en", "Climate of China"), ("en", "Little Ice Age"), ("en", "Medieval Warm Period"), ("en", "4.2-kiloyear event"),
           ("en", "Holocene climatic optimum"), ("en", "Late Antique Little Ice Age"), ("en", "Chu Kochen"),
           ("zh", "竺可桢"), ("zh", "小冰期"), ("zh", "中世纪温暖期"), ("zh", "全新世大暖期"), ("zh", "中国气候")]
CLIMATE += [("zh", t) for t in search("zh", "中国 五千年 气候变迁 竺可桢", 3)]
for p in C["periods"]:
    rec = {"src": [], "p": []}
    terms = [p["name"], p["name_zh"]] + words(p["name"], p["name_zh"])
    for lang, t in CLIMATE + [("en", x) for x in search("en", p["name"] + " China climate", 2)]:
        text, title = article(lang, t)
        if not title: continue
        got = []
        for y in sorted({p["from"], p["to"]}):
            got += hits(text, year_re(y, lang), lang, 2)
        for w in terms:
            got += hits(text, esc(w), lang, 1)
        if got: rec["src"].append(f"{lang}:{title}"); rec["p"] += got
    rec["p"] = merge(rec["p"])[:12]
    more["periods"][p["id"]] = rec
print("periods done", flush=True)

# ---- economy
E = json.load(open(os.path.join(ROOT, "data/economy.json")))
prov = E["provinces"]
GENERAL = [("en", "Historical census of China"), ("en", "Demographics of China"), ("en", "Economic history of China before 1912"),
           ("en", "Southward shift of China's economic center"), ("zh", "中国人口史"), ("zh", "中国历代人口"), ("zh", "经济重心南移"),
           ("zh", "中国经济史")]
for metric, snaps in E["metrics"].items():
    for s in snaps:
        books = re.findall(r"《([^》]+)》", s.get("src_zh", ""))
        cands = list(GENERAL)
        for b in books:
            cands += [("zh", b.split("·")[0]), ("zh", b.replace("·", ""))] + [("zh", t) for t in search("zh", b, 2)]
        cands += [("zh", t) for t in search("zh", f"{s['src_zh']}", 2)] + [("en", t) for t in search("en", s.get("src", ""), 2)]
        reign = re.findall(r"[一-鿿]{2}[元一二三四五六七八九十]+年", s.get("src_zh", ""))
        rec, seen = {"src": [], "p": []}, set()
        for lang, t in cands:
            text, title = article(lang, t)
            if not title or (lang, title) in seen: continue
            seen.add((lang, title))
            got = hits(text, year_re(s["year"], lang), lang, 3)
            for r in reign: got += hits(text, re.escape(r), lang, 3)
            if title in books or title.replace("·", "") in [b.replace("·", "") for b in books]:
                got.insert(0, f"[{lang}] " + text[:600].replace("\n", " "))
            if got: rec["src"].append(f"{lang}:{title}"); rec["p"] += got
        rec["p"] = merge(rec["p"])[:14]
        more["economy"][f"{metric}|{s['year']}"] = rec
print("economy done", flush=True)

json.dump(more, open(os.path.join(OUT, "more.json"), "w"), ensure_ascii=False)
print("done", {k: (len(v), sum(1 for r in v.values() if r["p"])) for k, v in more.items()})
