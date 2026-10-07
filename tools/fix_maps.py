"""Hand corrections to the border maps, applied after they are built.

The world maps (tools/build_world.py, from Cliopatria + historical-basemaps) and the dynasty maps
(tools/build_borders.py and friends) get some places wrong: a state missing, a label in the wrong language, two states
on the same land, an area given to a state that only took it decades later. Each fix below names a span of years and
what to do over it; a map whose years only partly fall in the span is split, so the change starts in the right year.

Ops:
  rename  feature `name` becomes `to` (and `zh`), merged into `to` if that feature already exists
  zh      only the Chinese name changes
  assign  the land in `area` goes to `owner` (made if missing); `take` limits it to land held by those features
          (or "focus" for the map's main states), `unowned` to land no feature holds
  overlap on world maps, where two states cover the same land the smaller one keeps it (Cliopatria leaves colonial
          empires and occupations over states that were already independent)
Areas: {"box": [w, s, e, n]}, {"poly": [[lon, lat], ...]}, {"ne": "file:FIELD=value"} (Natural Earth, downloaded to
tools/.cache/ne), {"feature": [map path, name]}; "clip"/"minus" boxes trim them. An owner can be a name or
{"at": [lon, lat]}: whatever feature holds that point on the map being fixed.

Splits are written as data/world/<year>.json (+ -outer) and data/borders/fix/<period>-<year>.geojson, listed with
"fix": true in data/world/index.json and data/eras.json; a rerun removes and remakes them, so it is safe to run again.
Run after build_world / build_borders / carve_states / snap_terrain / taiwan.py, then rerun build_countries.py."""
import copy, glob, json, os, re, urllib.request
import shapely
from shapely.geometry import box, mapping, shape, Polygon, Point

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson"
CLIP = box(60, 5, 150, 58)   # the dynasty maps' window (tools/build_borders.py); world "-outer" maps leave it out
KOREA_N = [[124.0, 37.6], [130.0, 37.6], [130.0, 40.6], [128.2, 41.6], [126.2, 41.0], [124.3, 40.0]]   # the north of the peninsula
LELANG = [[124.3, 39.9], [125.8, 40.4], [126.9, 39.6], [127.1, 38.3], [126.5, 37.65], [125.2, 37.65], [124.4, 38.5]]
GOJOSEON = [[121.8, 40.6], [123.6, 41.9], [126.6, 41.9], [128.2, 40.6], [127.6, 38.8], [126.5, 37.6], [124.6, 37.6], [124.0, 39.5]]
LUOYANG = [112.45, 34.62]
GAZA = [[34.21, 31.32], [34.27, 31.22], [34.37, 31.27], [34.56, 31.53], [34.49, 31.6], [34.15, 31.6]]
JAPAN = [139.7, 35.7]

FIXES = [
    # --- China, 1912-1949 ---
    {"years": [1913, 1923], "do": "rename", "name": "Manchu Empire", "to": "Republic of China", "zh": "中华民国"},
    {"years": [1924, 1927], "do": "zh", "name": "Chinese Warlords", "zh": "中华民国（北洋政府）"},
    {"years": [1928, 1935], "do": "rename", "name": "Chinese Warlords", "to": "Republic of China", "zh": "中华民国",
     "label": "1928: the Northern Expedition ends; the Nationalist government in Nanjing reunites China in name",
     "label_zh": "1928年：北伐完成，南京国民政府在名义上统一全国"},
    {"years": [1924, 1931], "do": "zh", "name": "Manchuria", "zh": "东北（奉系）"},
    {"years": [1921, 1944], "do": "assign", "area": {"ne": "ne_10m_admin_1_states_provinces:name=Tuva"},
     "owner": "Tuvan People's Republic", "zh": "唐努图瓦"},
    {"years": [1936, 1944], "do": "rename", "name": "White Russia", "to": "Tuvan People's Republic", "zh": "唐努图瓦"},
    {"years": [1951, 1959], "do": "rename", "name": "Tibet", "to": "China", "zh": "中国",
     "label": "1951: the Seventeen Point Agreement; the PLA enters Lhasa", "label_zh": "1951年：签订十七条协议，解放军进入拉萨"},
    # --- Japan, Korea, Ryukyu, Sakhalin, Kurils ---
    {"years": [1905, 1944], "do": "assign", "area": {"ne": "ne_10m_admin_1_states_provinces:name=Sakhalin", "clip": [140, 45.5, 146, 50.0]},
     "owner": {"at": JAPAN},
     "label": "1905: the Treaty of Portsmouth gives southern Sakhalin to Japan", "label_zh": "1905年：《朴次茅斯和约》将库页岛南部割予日本"},
    {"years": [1429, 1878], "do": "assign", "area": {"ne": "ne_10m_admin_1_states_provinces:name=Okinawa"},
     "owner": "Ryukyu Kingdom", "zh": "琉球国", "color": "#9a8a4a"},
    {"years": [1879, 1944], "do": "assign", "area": {"ne": "ne_10m_admin_1_states_provinces:name=Okinawa"},
     "owner": {"at": JAPAN}, "label": "1879: Japan annexes the Ryukyu Kingdom as Okinawa", "label_zh": "1879年：日本吞并琉球，设冲绳县"},
    {"years": [1946, 1971], "do": "assign", "area": {"ne": "ne_10m_admin_1_states_provinces:name=Okinawa"},
     "owner": "Ryukyu Islands (USA)", "zh": "琉球（美国治理）", "color": "#6a7f99"},
    {"years": [1946, 1951], "do": "assign", "area": {"box": [128.5, 30.5, 146.5, 45.8]}, "take": ["United States of America"],
     "owner": "Japan (USA)", "zh": "日本（盟军占领）"},
    {"years": [1952, 2030], "do": "assign", "area": {"box": [128.5, 30.5, 146.5, 45.8]}, "take": ["United States of America", "Japan (USA)"],
     "owner": "Japan", "zh": "日本", "label": "1952: the occupation of Japan ends", "label_zh": "1952年：盟军对日占领结束"},
    {"years": [1972, 2030], "do": "assign", "area": {"ne": "ne_10m_admin_1_states_provinces:name=Okinawa"}, "owner": {"at": JAPAN},
     "label": "1972: Okinawa returns to Japan", "label_zh": "1972年：冲绳归还日本"},
    {"years": [1946, 1949], "do": "assign", "area": {"poly": [[124, 38.0], [131, 38.0], [131, 43.0], [124, 43.0]]}, "take": ["USSR"],
     "owner": "Korea (USSR)", "zh": "朝鲜（苏占区）"},
    {"years": [1946, 1949], "do": "assign", "area": {"poly": [[124, 33], [131, 33], [131, 38.0], [124, 38.0]]},
     "take": ["United States of America"], "owner": "Korea (USA)", "zh": "朝鲜（美占区）"},
    {"years": [1948, 2030], "do": "rename", "name": "Korea (USSR)", "to": "Korea, Democratic People's Republic of", "zh": "朝鲜民主主义人民共和国"},
    {"years": [1948, 2030], "do": "rename", "name": "Korea (USA)", "to": "Korea, Republic of", "zh": "韩国"},
    {"years": [1946, 2030], "do": "assign", "area": {"ne": "ne_10m_admin_0_disputed_areas:BRK_NAME=Kuril Is."}, "unowned": True,
     "owner": {"at": [142.7, 51.0]}},
    # --- Korea in the dynasty maps ---
    {"years": [-206, -109], "do": "assign", "area": {"poly": GOJOSEON}, "take": ["Tungus", "Xiongnu"], "owner": "Gojoseon", "zh": "古朝鲜（卫满朝鲜）", "color": "#a3727a"},
    {"years": [-108, 312], "do": "assign", "area": {"poly": LELANG}, "owner": {"at": LUOYANG}},
    {"years": [-108, -38], "do": "rename", "name": "Koguryo", "to": "Buyeo and Ye-Maek", "zh": "扶余 · 濊貊"},
    {"years": [313, 419], "do": "assign", "area": {"poly": KOREA_N}, "take": "focus", "owner": {"at": [126.18, 41.12]}},
    {"years": [618, 667], "do": "rename", "name": "Balhae", "to": "Koguryo", "zh": "高句丽"},
    {"years": [668, 697], "do": "rename", "name": "Balhae", "to": "Andong Protectorate", "zh": "安东都护府", "focus": True,
     "label": "668: Tang and Silla destroy Goguryeo; the Andong Protectorate is set up at Pyongyang",
     "label_zh": "668年：唐与新罗灭高句丽，于平壤设安东都护府"},
    {"years": [698, 906], "do": "assign", "area": {"poly": [[124, 37.6], [131, 37.6], [129.5, 39.4], [124, 39.4]]}, "take": ["Balhae"],
     "owner": "Silla", "zh": "新罗", "label": "698: Dae Joyeong founds Balhae", "label_zh": "698年：大祚荣建立渤海国"},
    # --- West Asia, Caucasus ---
    {"years": [1967, 1993], "do": "assign", "area": {"ne": "ne_10m_admin_0_countries:ADMIN=Palestine"}, "owner": "Israel", "zh": "以色列",
     "label": "1967: the Six-Day War; Israel occupies the West Bank, Gaza, Sinai and the Golan", "label_zh": "1967年：六日战争，以色列占领约旦河西岸、加沙、西奈和戈兰高地"},
    {"years": [1949, 1966], "do": "assign", "area": {"poly": GAZA}, "owner": {"at": [31.2, 30.0]}},
    {"years": [1967, 1993], "do": "assign", "area": {"poly": GAZA}, "take": ["Egypt", "Palestine"], "owner": "Israel"},
    {"years": [1967, 1981], "do": "assign", "area": {"box": [32.2, 27.7, 34.95, 31.35]}, "take": ["Egypt"], "owner": "Israel"},
    {"years": [1960, 1961], "do": "zh", "name": "Egypt", "zh": "阿拉伯联合共和国"},
    {"years": [1962, 1972], "do": "assign", "area": {"ne": "ne_10m_admin_0_countries:ADMIN=Syria"}, "take": ["Egypt"], "owner": "Syria", "zh": "叙利亚",
     "label": "1961: Syria leaves the United Arab Republic", "label_zh": "1961年：叙利亚退出阿拉伯联合共和国"},
    {"years": [1967, 2030], "do": "assign", "area": {"ne": "ne_10m_admin_0_disputed_areas:BRK_NAME=Golan Heights"}, "owner": "Israel", "zh": "以色列"},
    {"years": [1994, 2030], "do": "assign", "area": {"ne": "ne_10m_admin_0_countries:ADMIN=Palestine"}, "owner": "Palestine", "zh": "巴勒斯坦",
     "color": "#7d9b6a", "label": "1994: the Palestinian Authority is set up under the Oslo Accords", "label_zh": "1994年：依据奥斯陆协议成立巴勒斯坦民族权力机构"},
    {"years": [1994, 2030], "do": "assign", "area": {"poly": GAZA}, "owner": "Palestine", "zh": "巴勒斯坦"},
    {"years": [1992, 2022], "do": "assign", "area": {"ne": "ne_10m_admin_0_disputed_areas:BRK_NAME=Artsakh"}, "owner": "Artsakh", "zh": "阿尔察赫（纳卡）", "color": "#a07d5a"},
    {"years": [2023, 2030], "do": "assign", "area": {"ne": "ne_10m_admin_0_disputed_areas:BRK_NAME=Artsakh"}, "owner": "Azerbaijan", "zh": "阿塞拜疆",
     "label": "2023: Azerbaijan retakes Nagorno-Karabakh", "label_zh": "2023年：阿塞拜疆收复纳卡地区"},
    # --- South Asia ---
    {"years": [1946, 1959], "do": "assign", "area": {"ne": "ne_10m_admin_0_disputed_areas:BRK_NAME=Arunachal Pradesh"}, "take": ["Bhutan"],
     "owner": {"at": [77.2, 28.6]}},
    # --- one owner per place on the post-war world maps ---
    {"years": [1945, 2030], "do": "overlap"},
]


def ne(spec):
    f, cond = spec.split(":")
    k, v = cond.split("=", 1)
    path = P("tools/.cache/ne", f + ".geojson")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(NE.format(f), path)
    d = NE_CACHE.get(path) or NE_CACHE.setdefault(path, json.load(open(path)))
    gs = [shape(x["geometry"]).buffer(0) for x in d["features"] if str(x["properties"].get(k)) == v]
    assert gs, f"no Natural Earth feature {spec}"
    return shapely.union_all(gs)


NE_CACHE = {}


def area(spec):
    if "box" in spec: g = box(*spec["box"])
    elif "poly" in spec: g = Polygon(spec["poly"])
    elif "ne" in spec: g = ne(spec["ne"])
    elif "feature" in spec:
        d = json.load(open(P(spec["feature"][0])))
        g = shapely.union_all([shape(f["geometry"]).buffer(0) for f in d["features"] if f["properties"]["name"] == spec["feature"][1]])
    if "clip" in spec: g = g.intersection(box(*spec["clip"]))
    if "minus" in spec: g = g.difference(box(*spec["minus"]))
    return g


def rnd(o):
    return [rnd(x) for x in o] if isinstance(o[0], (list, tuple)) else [round(o[0], 3), round(o[1], 3)]


def polys(g):
    """Only the polygons of a geometry (unions and differences can leave lines and points behind)."""
    if g.geom_type in ("Polygon", "MultiPolygon"): return g
    return shapely.union_all([p for p in getattr(g, "geoms", []) if p.geom_type in ("Polygon", "MultiPolygon")] or [Polygon()])


def put_geom(f, g):
    g = polys(shapely.set_precision(polys(g), 0.001))
    if g.is_empty:
        f["geometry"] = None
        return
    m = mapping(g)
    f["geometry"] = {"type": m["type"], "coordinates": rnd(m["coordinates"])}
    if "area" in f["properties"]: f["properties"]["area"] = round(g.area, 1)
    if "label" in f["properties"] and isinstance(f["properties"]["label"], list):
        big = max(getattr(g, "geoms", [g]), key=lambda x: x.area)
        c = big.representative_point()
        f["properties"]["label"] = [round(c.x, 2), round(c.y, 2)]


def feat_at(fc, pt):
    p = Point(pt)
    return next((f for f in fc["features"] if f.get("geometry") and shape(f["geometry"]).buffer(0).contains(p)), None)


def apply(fc, fx, outer, world):
    """Apply one fix to a FeatureCollection in place. Returns True if anything changed."""
    feats = fc["features"]
    by = {f["properties"]["name"]: f for f in feats}
    do = fx["do"]
    if do == "zh":
        f = by.get(fx["name"])
        if f and f["properties"].get("name_zh") != fx["zh"]:
            f["properties"]["name_zh"] = fx["zh"]
            return True
        return False
    if do == "rename":
        f = by.get(fx["name"])
        if not f: return False
        tgt = by.get(fx["to"])
        if tgt and tgt is not f:
            put_geom(tgt, shapely.union_all([shape(tgt["geometry"]).buffer(0), shape(f["geometry"]).buffer(0)]))
            feats.remove(f)
        else:
            f["properties"]["name"] = fx["to"]
            f["properties"]["name_zh"] = fx.get("zh", f["properties"].get("name_zh", ""))
            if "focus" in fx: f["properties"]["focus"] = fx["focus"]
        return True
    if do == "overlap":
        if not world: return False
        changed = False
        geo = {id(f): shape(f["geometry"]).buffer(0) for f in feats}
        order = sorted(feats, key=lambda f: geo[id(f)].area)
        for i, f in enumerate(order):
            for big in order[i + 1:]:
                g, bg = geo[id(f)], geo[id(big)]
                if bg.intersects(g) and bg.intersection(g).area > 0.05:
                    geo[id(big)] = bg.difference(g)
                    put_geom(big, geo[id(big)])
                    changed = True
        fc["features"] = [f for f in feats if f.get("geometry")]
        return changed
    if do == "assign":
        a = AREAS.setdefault(id(fx), area(fx["area"]))
        if outer: a = a.difference(CLIP)
        if a.is_empty: return False
        own = fx["owner"]
        if isinstance(own, dict):
            t = feat_at(fc, own["at"])
            if not t: return False
            own = t["properties"]["name"]
        take = fx.get("take")
        held = []
        for f in feats:
            if f["properties"]["name"] == own or not f.get("geometry"): continue
            if take == "focus" and not f["properties"].get("focus"): continue
            if isinstance(take, list) and f["properties"]["name"] not in take: continue
            held.append(f)
        if fx.get("unowned"):
            others = shapely.union_all([shape(f["geometry"]).buffer(0) for f in feats if f.get("geometry")])
            gain = a.difference(others)
        else:
            gain = shapely.union_all([shape(f["geometry"]).buffer(0).intersection(a) for f in held] or [Polygon()])
            if take is None:   # plain assign: unheld land in the area too
                others = shapely.union_all([shape(f["geometry"]).buffer(0) for f in feats if f.get("geometry")])
                gain = shapely.union_all([gain, a.difference(others)])
        if gain.is_empty or gain.area < 0.005: return False
        for f in held:
            g = shape(f["geometry"]).buffer(0)
            if g.intersects(gain): put_geom(f, g.difference(gain))
        tgt = by.get(own)
        if tgt:
            put_geom(tgt, shapely.union_all([shape(tgt["geometry"]).buffer(0), gain]))
        else:
            props = {"name": own, "name_zh": fx.get("zh", ""), "focus": False}
            if world or "color" in fx: props["color"] = fx.get("color", "#8a8a8a")
            props["area"] = 0
            props["label"] = [0, 0]
            tgt = {"type": "Feature", "geometry": None, "properties": props}
            put_geom(tgt, gain)
            feats.append(tgt)
        fc["features"] = [f for f in feats if f.get("geometry")]
        return True
    raise ValueError(do)


AREAS = {}


def dump_world(obj):
    return re.sub(r"(\d+\.\d{2})\d+", r"\1", json.dumps(obj, separators=(",", ":"), ensure_ascii=False))


# ---------- the maps and their years ----------

def world_maps():
    """[(from, to, entry)] for every world snapshot."""
    idx = json.load(open(P("data/world/index.json")))
    return idx, [(e["from"], (idx[i + 1]["from"] - 1) if i + 1 < len(idx) else 9999, e) for i, e in enumerate(idx)]


ERAS_TXT = P("data/eras.json")


def china_maps(eras):
    out = []
    for e in eras["eras"]:
        sn = e.get("snapshots") or []
        for i, s in enumerate(sn):
            out.append((s["from"], (sn[i + 1]["from"] - 1) if i + 1 < len(sn) else e["end"], e, s))
    return out


def load_ref(ref):
    path, _, sid = ref.partition("#")
    d = json.load(open(P(path)))
    return d[sid] if sid else d


def save_ref(ref, fc):
    path, _, sid = ref.partition("#")
    if sid:
        d = json.load(open(P(path)))
        d[sid] = fc
        json.dump(d, open(P(path), "w"), ensure_ascii=False, separators=(",", ":"))
    else:
        json.dump(fc, open(P(path), "w"), ensure_ascii=False, separators=(",", ":"))


def remove_fix_snapshots(txt):
    return re.sub(r',\n    \{\n     "from": -?\d+,\n     "borders": "data/borders/fix/[^"]+",\n     "fix": true(?:,\n     "label": "[^"]*",\n     "label_zh": "[^"]*")?\n    \}', "", txt)


def insert_snapshot(txt, era_id, after_from, new_from, path, fx):
    """Insert a snapshot entry into data/eras.json's text after the era's snapshot that starts at after_from."""
    start = txt.index(f'"id": "{era_id}"')
    m = re.compile(r'\n    \{\n     "from": ' + str(after_from) + r',\n(?:     [^\n]*\n)*?    \}').search(txt, start)
    lab = f',\n     "label": {json.dumps(fx["label"], ensure_ascii=False)},\n     "label_zh": {json.dumps(fx["label_zh"], ensure_ascii=False)}' if fx and fx.get("label") else ""
    entry = f',\n    {{\n     "from": {new_from},\n     "borders": "{path}",\n     "fix": true{lab}\n    }}'
    return txt[:m.end()] + entry + txt[m.end():]


def main():
    # Start from the built maps: drop the splits of an earlier run.
    for f in glob.glob(P("data/borders/fix/*.geojson")): os.remove(f)
    os.makedirs(P("data/borders/fix"), exist_ok=True)
    idx = [e for e in json.load(open(P("data/world/index.json"))) if not e.get("fix")]
    for f in glob.glob(P("data/world/*.json")):
        b = os.path.basename(f)
        if b in ("index.json", "names_zh.json"): continue
        if not any(b in (os.path.basename(e["full"]), os.path.basename(e.get("outer", ""))) for e in idx): os.remove(f)
    json.dump(idx, open(P("data/world/index.json"), "w"), indent=1)
    txt = remove_fix_snapshots(open(ERAS_TXT).read())
    open(ERAS_TXT, "w").write(txt)

    # 1. Split maps at every fix boundary that falls inside a map's years.
    cuts = {}
    for fx in FIXES:
        if fx["do"] == "overlap": continue
        a, b = fx["years"]
        cuts.setdefault(a, fx)
        cuts.setdefault(b + 1, None)
    idx, wm = world_maps()
    for y, fx in sorted(cuts.items()):
        for lo, hi, e in wm:
            if lo < y <= hi:
                new = {"from": y, "full": f"data/world/{y}.json", "fix": True}
                open(P(new["full"]), "w").write(open(P(e["full"])).read())
                if "outer" in e:
                    new["outer"] = f"data/world/{y}-outer.json"
                    open(P(new["outer"]), "w").write(open(P(e["outer"])).read())
                idx.insert(idx.index(e) + 1, new)
                break
        idx, wm = idx, [(x["from"], (idx[i + 1]["from"] - 1) if i + 1 < len(idx) else 9999, x) for i, x in enumerate(idx)]
    json.dump(idx, open(P("data/world/index.json"), "w"), indent=1)
    for y, fx in sorted(cuts.items()):
        eras = json.loads(txt)
        for lo, hi, e, s in china_maps(eras):
            if lo < y <= hi:
                path = f"data/borders/fix/{e['id']}-{y}.geojson"
                save_ref(path, load_ref(s["borders"]))
                txt = insert_snapshot(txt, e["id"], s["from"], y, path, fx)
                break
    open(ERAS_TXT, "w").write(txt)

    # 2. Apply every fix to every map whose years fall inside it.
    eras = json.loads(txt)
    _, wm = world_maps()
    n = 0
    for fx in FIXES:
        a, b = fx["years"]
        for lo, hi, e in wm:
            if not (a <= lo and hi <= b): continue
            for key in ("full", "outer"):
                if key not in e: continue
                fc = json.load(open(P(e[key])))
                if apply(fc, fx, key == "outer", True):
                    open(P(e[key]), "w").write(dump_world(fc)); n += 1
        if fx["do"] == "overlap": continue
        spans = china_maps(eras)
        for lo, hi, e, s in spans:
            if not (a <= lo and hi <= b): continue
            # A border file shared by several snapshots must not change for years outside the fix.
            assert all(a <= l2 and h2 <= b for l2, h2, _, s2 in spans if s2["borders"] == s["borders"]), (s["borders"], fx)
            fc = load_ref(s["borders"])
            if apply(fc, fx, False, False):
                save_ref(s["borders"], fc); n += 1
    print("maps changed:", n)


if __name__ == "__main__":
    main()
