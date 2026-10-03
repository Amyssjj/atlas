"""Add events of the world regions (data/regions.json) to data/events.json.

Usage: python3 tools/merge_region_events.py <file.json> ...   (each a list of events with a `region` field)
Checks fields, category, level, year (3000 BCE to 2026) and duplicates (same Chinese title within 5 years in the
same region); an event already present by id is replaced, so a batch can be merged again after fixes. Region
events have no long story, no city or person links and no country tags (tools/link_events.py skips them).
AI-drafted, not source-checked."""
import json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
CATS = {"war", "politics", "reform", "rebellion", "culture", "economy", "diplomacy", "science", "society"}
KEYS = ["id", "region", "also", "year", "endYear", "circa", "level", "category", "title", "title_zh", "place", "place_zh",
        "lat", "lon", "summary", "summary_zh", "source"]
regions = {r["id"] for r in json.load(open(P("data/regions.json")))["regions"]}
events = json.load(open(P("data/events.json")))
added = replaced = 0
for path in sys.argv[1:]:
    n = 0
    batch = json.load(open(path))
    new_ids = {e.get("id") for e in batch}
    events = [e for e in events if e["id"] not in new_ids or e.get("region", "china") == "china"]
    regs = {e.get("region") for e in batch}
    for e in events:  # a China event a previous run of this batch folded into
        if e.get("also") and e.get("region", "china") == "china":
            e["also"] = [r for r in e["also"] if r not in regs]
            if not e["also"]: del e["also"]
    for e in batch:
        why = None
        if e.get("region") not in regions or e["region"] == "china": why = f"region {e.get('region')}"
        elif e.get("category") not in CATS: why = f"category {e.get('category')}"
        elif e.get("level") not in (1, 2, 3): why = f"level {e.get('level')}"
        elif not isinstance(e.get("year"), int) or not -3000 <= e["year"] <= 2026 or e["year"] == 0: why = f"year {e.get('year')}"
        elif not (-180 <= e.get("lon", 999) <= 180 and -60 <= e.get("lat", 999) <= 80): why = "coordinates"
        elif not e.get("title_zh") or not e.get("summary_zh") or not e.get("title"): why = "missing text"
        elif any(x.get("region") == e["region"] and x.get("title_zh") == e["title_zh"] and abs(x["year"] - e["year"]) <= 5 for x in events): why = "duplicate"
        elif any(x["id"] == e["id"] for x in events): why = "id taken by a China event"
        if why:
            print(f"  drop {e.get('id')} {e.get('year')} {e.get('title_zh')}: {why}")
            continue
        q = {k: e.get(k) for k in KEYS}
        for k in ("endYear", "also"):
            if q[k] is None: del q[k]
        q["circa"] = bool(q["circa"])
        q.update(places=[], people=[], states=[])
        events.append(q)
        n += 1
    added += n
    print(f"{os.path.basename(path)}: {n} events")
# One event written for two regions (卡迭石战役 for Egypt and the Middle East) is kept once and listed under both:
# the copy whose point lies in its own region stays, the other region goes to its `also`. Same Chinese title within
# 5 years, or a pair named in SAME.
SAME = [("埃兰攻陷乌尔", "埃兰人攻陷乌尔"), ("冈比西斯二世征服埃及", "冈比西斯征服埃及"), ("塞琉古王朝建立", "塞琉古王国建立"),
        ("沙普尔一世俘虏罗马皇帝瓦勒良", "埃德萨战役（瓦勒良被俘）"), ("第一次尼西亚公会议", "尼西亚公会议"),
        ("阿拉伯人征服西班牙", "塔里克渡海征服西班牙"), ("白益王朝进入巴格达", "布韦希王朝控制巴格达"),
        ("托洛萨会战", "拉斯纳瓦斯德托洛萨战役"), ("艾因贾鲁特战役", "艾因贾鲁战役"), ("奥斯曼一世建国", "奥斯曼帝国建立"),
        ("祖哈布条约", "席林堡条约（佐哈布条约）"), ("万历朝鲜之役", "万历朝鲜战争"), ("卡尔纳尔战役与洗劫德里", "纳迪尔沙洗劫德里")]
same = {frozenset(x) for x in SAME}
outlines = {r["id"]: r["polygon"] for r in json.load(open(P("data/regions.json")))["regions"]}
def inside(e):
    poly, x, y, c = outlines[e["region"]], e["lon"], e["lat"], False
    for i in range(len(poly)):
        (xi, yi), (xj, yj) = poly[i], poly[i - 1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
    return c
reg = [e for e in events if e.get("region", "china") != "china"]
gone = set()
# A region event that repeats one of China's (白江口之战 for Korea and Japan) folds into the China event.
china = {}
for e in events:
    if e.get("region", "china") == "china": china.setdefault(e["title_zh"], []).append(e)
for e in reg:
    for c in china.get(e["title_zh"], []):
        if abs(c["year"] - e["year"]) <= 5:
            c["also"] = sorted(set(c.get("also", [])) | {e["region"]} | set(e.get("also", [])))
            gone.add(e["id"])
            break
for i, a in enumerate(reg):
    for b in reg[i + 1:]:
        if a["id"] in gone or b["id"] in gone or a["region"] == b["region"] or abs(a["year"] - b["year"]) > 5: continue
        if a["title_zh"] != b["title_zh"] and frozenset((a["title_zh"], b["title_zh"])) not in same: continue
        keep, drop = (b, a) if inside(b) and not inside(a) else (a, b)
        keep["also"] = sorted(set(keep.get("also", [])) | {drop["region"]} | set(drop.get("also", [])))
        gone.add(drop["id"])
events = [e for e in events if e["id"] not in gone]
print(len(gone), "events shared between regions folded into one")
events.sort(key=lambda e: (e["year"], e.get("level", 1)))
json.dump(events, open(P("data/events.json"), "w"), ensure_ascii=False, indent=1)
print(added, "region events merged,", len(events), "events in all")
