"""Add batches of events to data/events.json and tag reforms and uprisings among the existing ones.

Usage: python3 tools/merge_events.py <dir>   (the dir holds <era-id>.json files, each a list of events)
Checks fields, years against the era, coordinates and duplicates (same Chinese title within 5 years), and prints what
it drops. New events have no long-form story; the story view says so and links to Wikipedia. Safe to run again."""
import glob, json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
CATS = {"war", "politics", "reform", "rebellion", "culture", "economy", "diplomacy", "science", "society"}
KEYS = ["id", "year", "endYear", "circa", "level", "category", "title", "title_zh", "place", "place_zh",
        "lat", "lon", "summary", "summary_zh", "source"]
eras = {e["id"]: e for e in json.load(open(P("data/eras.json")))["eras"]}
events = json.load(open(P("data/events.json")))
ids = {e["id"] for e in events}

# Existing events written before the reform / rebellion tags existed.
REFORM = re.compile(r"变法|改革|新政|改制|均田|两税|一条鞭|摊丁|改土归流|府兵|青苗|推恩|租庸调|九品中正|科举")
REBEL = re.compile(r"起义|民变|黄巾|赤眉|绿林|红巾|太平天国|叛|之乱|暴动")
NOT_REBEL = re.compile(r"永嘉之乱|八王之乱|靖康|侯景之乱前")
retagged = 0
for e in events:
    t = e.get("title_zh", "")
    if e["category"] in ("politics", "economy", "society") and REFORM.search(t):
        e["category"] = "reform"; retagged += 1
    elif e["category"] in ("war", "politics", "society") and REBEL.search(t) and not NOT_REBEL.search(t):
        e["category"] = "rebellion"; retagged += 1
print(retagged, "existing events retagged")

added = 0
for path in sorted(glob.glob(os.path.join(sys.argv[1], "*.json"))):
    k = os.path.basename(path)[:-5]
    if k not in eras:
        continue
    era, n = eras[k], 0
    for e in json.load(open(path)):
        why = None
        if e.get("category") not in CATS: why = f"category {e.get('category')}"
        elif e.get("level") not in (1, 2, 3): why = f"level {e.get('level')}"
        elif not isinstance(e.get("year"), int) or not (era["start"] <= e["year"] <= era["end"]): why = f"year {e.get('year')}"
        elif not (60 <= e.get("lon", 0) <= 145 and 5 <= e.get("lat", 0) <= 60): why = "coordinates"
        elif not e.get("title_zh") or not e.get("summary_zh") or not e.get("title"): why = "missing text"
        elif any(x.get("title_zh") == e["title_zh"] and abs(x["year"] - e["year"]) <= 5 for x in events): why = "duplicate"
        if why:
            print(f"  drop {k} {e.get('year')} {e.get('title_zh')}: {why}")
            continue
        q = {key: e.get(key) for key in KEYS}
        if q["endYear"] is None: del q["endYear"]
        q["circa"] = bool(q["circa"])
        while q["id"] in ids: q["id"] += "-2"
        ids.add(q["id"])
        events.append(q)
        n += 1
    added += n
    print(f"{k}: +{n}")
events.sort(key=lambda e: (e["year"], e.get("level", 1)))
json.dump(events, open(P("data/events.json"), "w"), ensure_ascii=False, indent=1)
print(added, "added,", len(events), "events in all")

# Link the new events to cities and people (tools/link_events.py fills only events without those fields).
import subprocess
subprocess.run([sys.executable, os.path.join(ROOT, "tools", "link_events.py")], check=True)
