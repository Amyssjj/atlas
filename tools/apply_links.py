"""Apply a link report from tools/check_links.py: python3 tools/apply_links.py <links.json>

A link whose page exists (maybe under a redirect) is rewritten to the resolved title. A missing page is replaced
by a search hit only when the hit is nearly the same title (capitals, accents, dashes); the fixes are listed in
tools/link_fixes.json. Other missing pages and disambiguation pages are left as they are (the page opens them
through Wikipedia search) and listed there as unfixed. Events and people also get `source_zh` (a Chinese Wikipedia URL) when the page
has a Chinese version and the entry has none."""
import difflib, glob, json, os, sys, unicodedata, urllib.parse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
rep = json.load(open(sys.argv[1]))
url = lambda t: "https://en.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_"), safe="_(),'!:")
zurl = lambda t: "https://zh.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_"), safe="_(),'!:")
fixes, stats = {}, {"resolved": 0, "replaced": 0, "unfixed": 0, "zh": 0}

def norm(t):
    t = unicodedata.normalize("NFKD", t.replace("\u2013", "-").replace("\u2014", "-")).encode("ascii", "ignore").decode()
    return " ".join(t.lower().replace("_", " ").split())
def close(a, b):
    return norm(a) == norm(b) or difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() >= 0.97

def fix(x):
    r = rep.get(x.get("source"))
    if not r: return
    if r["ok"] and not r["disambig"]:
        new = url(r["title"])
        if new != x["source"]: stats["resolved"] += 1
    elif not r["ok"] and any(close(r["title"], t) for t in r.get("suggest", [])):
        new = url(next(t for t in r["suggest"] if close(r["title"], t)))
        fixes[x["source"]] = {"was": x["source"], "now": new, "for": x.get("title_zh") or x.get("name_zh"), "other": r["suggest"][1:]}
        stats["replaced"] += 1
    else:
        stats["unfixed"] += 1
        fixes[x["source"]] = {"was": x["source"], "now": None, "for": x.get("title_zh") or x.get("name_zh"),
                              "disambig": r["disambig"], "suggest": r.get("suggest", [])}
        return
    x["source"] = new
    if r.get("zh") and r["ok"] and not r["disambig"] and not x.get("source_zh"):
        x["source_zh"] = zurl(r["zh"]); stats["zh"] += 1

events = json.load(open(P("data/events.json")))
for e in events: fix(e)
json.dump(events, open(P("data/events.json"), "w"), ensure_ascii=False, indent=1)
for f in sorted(glob.glob(P("data/layers/*.json"))):
    L = json.load(open(f))
    # world-<region>.json bundles hold one layer file per period
    for x in (L.values() if os.path.basename(f).startswith("world-") else [L]):
        for p in x.get("people", []): fix(p)
    json.dump(L, open(f, "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(fixes, open(P("tools/link_fixes.json"), "w"), ensure_ascii=False, indent=1)
print(stats)
