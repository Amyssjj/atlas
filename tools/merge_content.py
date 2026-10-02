"""Merge content batches from data/work/<era-id>.json into the app's data files.

Each batch holds, for one era: Chinese text for the era card (summary_zh, note_zh, snapshot labels),
patches for existing events (place_zh, summary_zh, level), new events, and the long-form details.
Writes data/eras.json, data/events.json and data/details/<era-id>.json. Safe to run again.
"""
import glob, json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
EV_KEYS = ["id", "year", "endYear", "circa", "level", "category", "title", "title_zh", "place", "place_zh",
           "lat", "lon", "summary", "summary_zh", "source"]

eras_doc = json.load(open(P("data/eras.json")))
eras = {e["id"]: e for e in eras_doc["eras"]}
events = json.load(open(P("data/events.json")))
by_id = {e["id"]: e for e in events}
original = set(by_id)
problems = []

for path in sorted(glob.glob(P("data/work/*.json"))):
    w = json.load(open(path))
    era = eras[w["era"]["id"]]
    for k in ("summary_zh", "note_zh"):
        if w["era"].get(k):
            era[k] = w["era"][k]
    labels = w["era"].get("snapshot_labels_zh", {})
    for s in era["snapshots"]:
        if s["borders"] in labels:
            s["label_zh"] = labels[s["borders"]]
        elif s.get("label"):
            problems.append(f"{era['id']}: no label_zh for {s['borders']}")
    for eid, patch in w.get("events_patch", {}).items():
        if eid not in by_id:
            problems.append(f"{era['id']}: patch for unknown event {eid}")
            continue
        by_id[eid].update({k: v for k, v in patch.items() if k in ("place_zh", "summary_zh", "level")})
    for ev in w.get("new_events", []):
        if ev["id"] in original and by_id[ev["id"]].get("level", 1) == 1:
            problems.append(f"{era['id']}: new event id {ev['id']} clashes with an existing event")
            continue
        if not era["start"] <= ev["year"] <= era["end"]:
            problems.append(f"{era['id']}: {ev['id']} year {ev['year']} outside era")
            continue
        missing = [k for k in ("title", "title_zh", "place", "lat", "lon", "summary", "summary_zh", "category") if k not in ev]
        if missing:
            problems.append(f"{ev['id']}: missing {missing}")
            continue
        by_id[ev["id"]] = {k: ev[k] for k in EV_KEYS if k in ev}
    in_era = [e for e in by_id.values() if era["start"] <= e["year"] <= era["end"]]
    details = w.get("details", {})
    for e in in_era:
        if e["id"] not in details:
            problems.append(f"{era['id']}: no details for {e['id']}")
        if "summary_zh" not in e:
            problems.append(f"{era['id']}: no summary_zh for {e['id']}")
    os.makedirs(P("data/details"), exist_ok=True)
    with open(P("data", "details", f"{era['id']}.json"), "w") as f:
        json.dump({k: v for k, v in details.items() if k in by_id}, f, ensure_ascii=False, separators=(",", ":"))

out = sorted(by_id.values(), key=lambda e: (e["year"], e.get("level", 1)))
for e in out:
    e.setdefault("level", 1)
with open(P("data/events.json"), "w") as f:
    json.dump([{k: e[k] for k in EV_KEYS if k in e} for e in out], f, ensure_ascii=False, indent=1)
with open(P("data/eras.json"), "w") as f:
    json.dump(eras_doc, f, ensure_ascii=False, indent=1)

from collections import Counter
print(len(out), "events by level", dict(Counter(e["level"] for e in out)))
for p in problems:
    print("  !", p)
