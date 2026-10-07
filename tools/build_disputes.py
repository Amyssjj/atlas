"""Build data/disputes.json: places whose sovereignty is disputed, with the years of the dispute, who controls them,
who claims them and a short note. The map draws them hatched over the borders, which follow actual control.

Areas come from Natural Earth's disputed areas and countries (public domain; downloaded to tools/.cache/ne), from a
feature of one of the atlas's own world maps, or from a circle around small islands. Notes are AI-drafted.
Usage: python3 tools/build_disputes.py"""
import json, os, re, urllib.request
import shapely
from shapely.geometry import mapping, shape, Point

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *a: os.path.join(ROOT, *a)
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson"
DA, C0, A1 = "ne_10m_admin_0_disputed_areas", "ne_10m_admin_0_countries", "ne_10m_admin_1_states_provinces"

# id, years (to None = still disputed), names, area, controlled by, claimed by, note
D = [
    ("taiwan", 1949, None, "Taiwan", "台湾", {"ne": f"{DA}:BRK_NAME=Taiwan"},
     "Republic of China (Taiwan)", "中华民国（台湾）", "People's Republic of China", "中华人民共和国",
     "The Republic of China government moved to Taiwan in 1949 and has governed it since. The People's Republic of China regards Taiwan as part of its territory; most countries recognise the PRC, with differing positions on Taiwan's status.",
     "1949年中华民国政府迁至台湾，此后一直治理台湾。中华人民共和国认为台湾是其领土的一部分；多数国家与中华人民共和国建交，对台湾地位的表述各有不同。"),
    ("tibet-1912", 1912, 1950, "Tibet", "西藏", {"world": [1936, "Tibet"]},
     "Tibetan government (Ganden Phodrang)", "西藏噶厦政府", "Republic of China", "中华民国",
     "After the fall of the Qing, Tibet expelled Qing troops and governed itself, but no state formally recognised its independence. The Republic of China regarded it as Chinese territory. The PRC took control in 1950–51.",
     "清朝灭亡后，西藏驱逐清军，事实上自行治理，但没有国家正式承认其独立。中华民国视西藏为本国领土。1950至1951年中华人民共和国取得控制。"),
    ("mongolia-1911", 1911, 1945, "Outer Mongolia", "外蒙古", {"world": [1924, "Mongolia"]},
     "Bogd Khanate, then Mongolian People's Republic", "博克多汗国，后为蒙古人民共和国", "Republic of China", "中华民国",
     "Outer Mongolia declared independence in 1911 and became the Mongolian People's Republic in 1924 with Soviet backing. The Republic of China recognised its independence in 1946.",
     "外蒙古1911年宣布独立，1924年在苏联支持下成立蒙古人民共和国。中华民国于1946年承认其独立。"),
    ("manchukuo", 1932, 1945, "Manchukuo", "满洲国", {"ne": [f"{A1}:name=Heilongjiang", f"{A1}:name=Jilin", f"{A1}:name=Liaoning"]},
     "Manchukuo, a state set up and controlled by Japan", "日本扶植并控制的满洲国", "Republic of China", "中华民国",
     "Japan set up Manchukuo after seizing Manchuria in 1931. The League of Nations refused to recognise it; it ended with Japan's defeat in 1945.",
     "1931年九一八事变后日本占领东北，次年扶植成立满洲国。国际联盟不予承认，1945年随日本战败而终结。"),
    ("aksai-chin", 1950, None, "Aksai Chin", "阿克赛钦", {"ne": f"{DA}:BRK_NAME=Aksai Chin"},
     "China", "中国", "India", "印度",
     "China built a road through it in the 1950s and has held it since the 1962 Sino-Indian War. India claims it as part of Ladakh.",
     "1950年代中国修筑新藏公路经过此地，1962年中印边境战争后一直由中国控制。印度认为属于拉达克。"),
    ("arunachal", 1950, None, "Arunachal Pradesh / South Tibet", "阿鲁纳恰尔邦 / 藏南",
     {"ne": [f"{DA}:BRK_NAME=Arunachal Pradesh", f"{DA}:BRK_NAME=Tirpani Valleys", f"{DA}:BRK_NAME=Bara Hotii Valleys", f"{DA}:BRK_NAME=Samdu Valleys", f"{DA}:BRK_NAME=Demchok"]},
     "India", "印度", "China (as South Tibet)", "中国（称藏南）",
     "The McMahon Line drawn at the 1914 Simla Conference put this land in British India; Chinese governments have never accepted it. India took over Tawang in 1951.",
     "1914年西姆拉会议划出的麦克马洪线把此地划入英属印度，中国历届政府均不承认。印度1951年接管达旺。"),
    ("kashmir-india", 1947, None, "Jammu and Kashmir, Ladakh", "印控克什米尔", {"ne": f"{DA}:BRK_NAME=Jammu and Kashmir"},
     "India", "印度", "Pakistan", "巴基斯坦",
     "The princely state of Jammu and Kashmir acceded to India in 1947; wars in 1947, 1965 and 1999 left it divided along the Line of Control.",
     "1947年克什米尔土邦加入印度，经1947、1965、1999年数次冲突，沿实际控制线分治。"),
    ("kashmir-pakistan", 1947, None, "Azad Kashmir, Gilgit-Baltistan", "巴控克什米尔", {"ne": [f"{DA}:BRK_NAME=Azad Kashmir", f"{DA}:BRK_NAME=Gilgit-Baltistan"]},
     "Pakistan", "巴基斯坦", "India", "印度",
     "Held by Pakistan since the 1947–48 war; India claims all of the former princely state.",
     "1947至1948年战争后由巴基斯坦控制；印度主张整个原土邦。"),
    ("shaksgam", 1963, None, "Shaksgam Valley", "沙克斯干河谷", {"ne": f"{DA}:BRK_NAME=Shaksam Valley"},
     "China", "中国", "India", "印度",
     "Pakistan recognised it as Chinese in the 1963 boundary agreement; India, which claims all of Kashmir, does not.",
     "1963年中巴边界协定中巴基斯坦承认其属中国；主张整个克什米尔的印度不承认。"),
    ("siachen", 1984, None, "Siachen Glacier", "锡亚琴冰川", {"ne": f"{DA}:BRK_NAME=Siachen Glacier"},
     "India", "印度", "Pakistan", "巴基斯坦",
     "India has held the glacier since 1984; Pakistan claims it.", "印度自1984年起控制该冰川，巴基斯坦主张主权。"),
    ("kurils", 1945, None, "Southern Kurils / Northern Territories", "南千岛群岛 / 北方四岛", {"ne": f"{DA}:BRK_NAME=Kuril Is."},
     "Russia (USSR until 1991)", "俄罗斯（1991年前为苏联）", "Japan", "日本",
     "Taken by the Soviet Union in 1945. Japan claims the four southern islands, and the two countries have still not signed a peace treaty.",
     "1945年被苏联占领。日本主张南部四岛主权，两国至今未签订和约。"),
    ("diaoyu", 1971, None, "Diaoyu / Senkaku Islands", "钓鱼岛 / 尖阁诸岛", {"circle": [123.55, 25.75, 0.2]},
     "Japan (as Senkaku)", "日本（称尖阁诸岛）", "People's Republic of China and Taiwan (as Diaoyu / Diaoyutai)", "中华人民共和国、台湾（称钓鱼岛、钓鱼台）",
     "Administered by the US with Okinawa until 1972, then by Japan. China and Taiwan have claimed them since 1971.",
     "1972年前随冲绳由美国管理，此后由日本控制。中国大陆和台湾自1971年起主张主权。"),
    ("dokdo", 1954, None, "Dokdo / Takeshima", "独岛 / 竹岛", {"circle": [131.87, 37.24, 0.12]},
     "South Korea (as Dokdo)", "韩国（称独岛）", "Japan (as Takeshima)", "日本（称竹岛）",
     "South Korea has stationed police on the islets since 1954; Japan claims them.", "韩国自1954年起在岛上驻警，日本主张主权。"),
    ("paracels", 1974, None, "Paracel Islands", "西沙群岛", {"circle": [111.9, 16.4, 0.45]},
     "China", "中国", "Vietnam, Taiwan", "越南、台湾",
     "China took the whole group from South Vietnam in 1974; Vietnam and Taiwan also claim it.", "1974年中国从南越手中夺取全部西沙群岛；越南和台湾亦主张主权。"),
    ("spratlys", 1946, None, "Spratly Islands", "南沙群岛", {"circle": [114.3, 10.0, 1.1]},
     "Split among China, Taiwan, Vietnam, the Philippines and Malaysia", "中国、台湾、越南、菲律宾、马来西亚分别占据部分岛礁",
     "China, Taiwan and Vietnam claim all of them; the Philippines, Malaysia and Brunei claim parts", "中国、台湾、越南主张全部，菲律宾、马来西亚、文莱主张部分",
     "Reefs and islets held by several countries, with overlapping claims to the surrounding sea. A 2016 arbitral tribunal ruled against China's historic-rights claim; China rejects the ruling.",
     "多国分别占据岛礁，对周边海域的主张互相重叠。2016年南海仲裁案裁决否定中国的历史性权利主张，中国不接受该裁决。"),
    ("scarborough", 2012, None, "Scarborough Shoal", "黄岩岛", {"circle": [117.75, 15.15, 0.15]},
     "China (since 2012)", "中国（2012年起）", "Philippines, Taiwan", "菲律宾、台湾",
     "China has controlled the shoal since a 2012 standoff with the Philippines.", "2012年中菲对峙后由中国控制。"),
    ("crimea", 2014, None, "Crimea", "克里米亚", {"ne": f"{DA}:BRK_NAME=Crimea"},
     "Russia", "俄罗斯", "Ukraine", "乌克兰",
     "Russia annexed Crimea in 2014; Ukraine and most countries do not recognise the annexation.", "2014年俄罗斯吞并克里米亚，乌克兰和多数国家不承认。"),
    ("donbas", 2014, None, "Donetsk and Luhansk", "顿涅茨克、卢甘斯克", {"ne": [f"{DA}:BRK_NAME=Donetsk People's Republic", f"{DA}:BRK_NAME=Luhansk People's Republic"]},
     "Russian-backed authorities, annexed by Russia in 2022", "俄罗斯支持的当局，2022年被俄罗斯宣布吞并", "Ukraine", "乌克兰",
     "Drawn here at the 2014–2022 front line. Since the 2022 invasion Russia also occupies more of Donetsk, Luhansk, Zaporizhzhia and Kherson; most countries recognise none of it as Russian.",
     "图中为2014至2022年的控制线。2022年全面入侵后，俄罗斯还占领了顿涅茨克、卢甘斯克、扎波罗热和赫尔松的更多地区；多数国家不承认其为俄罗斯领土。"),
    ("transnistria", 1992, None, "Transnistria", "德涅斯特河沿岸", {"ne": f"{DA}:BRK_NAME=Transnistria"},
     "Self-governing, with Russian troops", "自行治理，驻有俄军", "Moldova", "摩尔多瓦",
     "Broke away from Moldova in the 1992 war; recognised by no UN member.", "1992年战争后脱离摩尔多瓦控制，未获任何联合国成员国承认。"),
    ("abkhazia", 1993, None, "Abkhazia", "阿布哈兹", {"ne": f"{DA}:BRK_NAME=Abkhazia"},
     "Self-governing, backed by Russia", "自行治理，受俄罗斯支持", "Georgia", "格鲁吉亚",
     "Broke away from Georgia in 1992–93; Russia recognised it after the 2008 war, as only a few states have.", "1992至1993年战争后脱离格鲁吉亚；2008年战争后俄罗斯等少数国家承认其独立。"),
    ("south-ossetia", 1992, None, "South Ossetia", "南奥塞梯", {"ne": f"{DA}:BRK_NAME=South Ossetia"},
     "Self-governing, backed by Russia", "自行治理，受俄罗斯支持", "Georgia", "格鲁吉亚",
     "Broke away from Georgia in 1991–92; Russia recognised it after the 2008 war.", "1991至1992年冲突后脱离格鲁吉亚；2008年战争后俄罗斯承认其独立。"),
    ("artsakh", 1994, 2023, "Nagorno-Karabakh", "纳戈尔诺-卡拉巴赫", {"ne": f"{DA}:BRK_NAME=Artsakh"},
     "Republic of Artsakh, backed by Armenia", "阿尔察赫共和国，受亚美尼亚支持", "Azerbaijan", "阿塞拜疆",
     "Held by Armenian forces after the 1988–94 war; Azerbaijan retook much of the area in 2020 and the rest in 2023, when most Armenians left.",
     "1988至1994年战争后由亚美尼亚族武装控制；阿塞拜疆2020年收复大部，2023年收复全部，大多数亚美尼亚族居民出走。"),
    ("north-cyprus", 1974, None, "Northern Cyprus", "北塞浦路斯", {"ne": f"{DA}:BRK_NAME=N. Cyprus"},
     "Turkish Cypriot administration, recognised only by Turkey", "土族塞人当局，仅获土耳其承认", "Republic of Cyprus", "塞浦路斯共和国",
     "Divided since Turkey's 1974 invasion; UN peacekeepers patrol the buffer zone.", "1974年土耳其出兵后分治，联合国维和部队驻守缓冲区。"),
    ("kosovo", 2008, None, "Kosovo", "科索沃", {"ne": f"{DA}:BRK_NAME=Kosovo"},
     "Republic of Kosovo", "科索沃共和国", "Serbia", "塞尔维亚",
     "Under UN administration from 1999; declared independence in 2008, recognised by about half the UN members but not by Serbia, Russia or China.",
     "1999年起由联合国托管，2008年宣布独立，约半数联合国成员国承认，塞尔维亚、俄罗斯、中国等不承认。"),
    ("western-sahara", 1975, None, "Western Sahara", "西撒哈拉", {"ne": f"{C0}:ADMIN=Western Sahara"},
     "Morocco (most of it); the Polisario Front (the east)", "摩洛哥（大部分）、波利萨里奥阵线（东部）", "Sahrawi Arab Democratic Republic; Morocco", "撒哈拉阿拉伯民主共和国；摩洛哥",
     "Spain left in 1975; Morocco took most of the territory. The UN lists it as a non-self-governing territory awaiting a referendum.",
     "1975年西班牙撤离后，摩洛哥控制大部分地区。联合国将其列为待举行公投的非自治领土。"),
    ("somaliland", 1991, None, "Somaliland", "索马里兰", {"ne": f"{C0}:ADMIN=Somaliland"},
     "Republic of Somaliland", "索马里兰共和国", "Somalia", "索马里",
     "Declared independence in 1991 and governs itself; no UN member recognises it.", "1991年宣布独立并自行治理，未获任何联合国成员国承认。"),
    ("west-bank", 1967, None, "West Bank and East Jerusalem", "约旦河西岸和东耶路撒冷",
     {"ne": [f"{DA}:BRK_NAME=West Bank", f"{DA}:BRK_NAME=East Jerusalem", f"{DA}:BRK_NAME=No Man's Land (Jerusalem)", f"{DA}:BRK_NAME=Mount Scopus", f"{DA}:BRK_NAME=No Man's Land (Fort Latrun)"]},
     "Israel; the Palestinian Authority governs parts since 1994", "以色列；1994年起巴勒斯坦民族权力机构治理部分地区", "Palestine", "巴勒斯坦",
     "Occupied by Israel in 1967. Under the Oslo Accords the Palestinian Authority runs the towns, while Israel controls most of the land; the UN regards it as occupied Palestinian territory. Israel annexed East Jerusalem.",
     "1967年被以色列占领。依据奥斯陆协议，巴勒斯坦民族权力机构管理城镇，以色列控制大部分土地；联合国视其为被占领的巴勒斯坦领土。以色列已宣布吞并东耶路撒冷。"),
    ("gaza", 1967, None, "Gaza Strip", "加沙地带", {"ne": f"{DA}:BRK_NAME=Gaza", "grow": 0.03},
     "Israel until 2005; Hamas from 2007", "2005年前为以色列，2007年起为哈马斯", "Palestine", "巴勒斯坦",
     "Occupied by Israel in 1967; Israel withdrew its settlers in 2005 but kept control of the borders. Hamas took over in 2007. The war that began in 2023 devastated the strip.",
     "1967年被以色列占领；2005年以色列撤出定居者，但仍控制边境。2007年起哈马斯控制。2023年爆发的战争使加沙遭到严重破坏。"),
    ("golan", 1967, None, "Golan Heights", "戈兰高地", {"ne": [f"{DA}:BRK_NAME=Golan Heights", f"{DA}:BRK_NAME=Shebaa Farms"]},
     "Israel", "以色列", "Syria (Shebaa Farms: Lebanon)", "叙利亚（沙巴农场：黎巴嫩）",
     "Taken from Syria in 1967 and annexed by Israel in 1981; only the United States recognises the annexation.", "1967年以色列从叙利亚夺取，1981年宣布吞并，仅美国承认。"),
    ("sinai", 1967, 1982, "Sinai", "西奈半岛", {"box": [32.2, 27.7, 34.95, 31.35], "land": True},
     "Israel", "以色列", "Egypt", "埃及",
     "Occupied by Israel in 1967 and returned to Egypt under the 1979 peace treaty, the last part in 1982.", "1967年被以色列占领，依据1979年和约归还埃及，1982年全部交还。"),
    ("east-timor", 1975, 1999, "East Timor", "东帝汶", {"ne": f"{C0}:ADMIN=East Timor"},
     "Indonesia", "印度尼西亚", "East Timorese independence movement; the UN regarded Portugal as administering power", "东帝汶独立运动；联合国仍视葡萄牙为管理国",
     "Invaded and annexed by Indonesia in 1975–76, without UN recognition; it voted for independence in 1999 and became independent in 2002.",
     "1975至1976年被印度尼西亚入侵并吞并，未获联合国承认；1999年公投选择独立，2002年正式独立。"),
    ("falklands", 1833, None, "Falkland Islands / Malvinas", "福克兰群岛 / 马尔维纳斯群岛", {"ne": f"{DA}:BRK_NAME=Falkland Is.", "grow": 0.05},
     "United Kingdom", "英国", "Argentina", "阿根廷",
     "British since 1833; Argentina claims them and invaded in 1982, starting the Falklands War.", "1833年起由英国控制；阿根廷主张主权，1982年出兵引发马岛战争。"),
    ("gibraltar", 1713, None, "Gibraltar", "直布罗陀", {"circle": [-5.35, 36.14, 0.08]},
     "United Kingdom", "英国", "Spain", "西班牙",
     "Ceded to Britain by the Treaty of Utrecht in 1713; Spain seeks its return.", "1713年《乌得勒支和约》割让英国，西班牙要求归还。"),
    ("essequibo", 1966, None, "Guayana Esequiba", "埃塞奎博地区", {"ne": f"{DA}:BRK_NAME=West of Essequibo River"},
     "Guyana", "圭亚那", "Venezuela", "委内瑞拉",
     "Awarded to British Guiana by an 1899 arbitration that Venezuela later repudiated; it has pressed its claim since Guyana's independence.", "1899年仲裁判归英属圭亚那，委内瑞拉后来不予承认，自圭亚那独立以来一直主张主权。"),
    ("halaib", 1958, None, "Hala'ib Triangle", "哈拉伊卜三角区", {"ne": f"{DA}:BRK_NAME=Halayib Triangle"},
     "Egypt", "埃及", "Sudan", "苏丹",
     "Claimed by both since 1958; Egypt has controlled it since the 1990s.", "1958年起埃及、苏丹均主张主权，1990年代起由埃及控制。"),
    ("abyei", 2011, None, "Abyei", "阿卜耶伊", {"ne": f"{DA}:BRK_NAME=Abyei"},
     "Sudan and South Sudan, with UN peacekeepers", "苏丹、南苏丹共管，联合国维和部队驻守", "Sudan and South Sudan", "苏丹、南苏丹",
     "Its status was left open when South Sudan became independent in 2011.", "2011年南苏丹独立时，阿卜耶伊归属悬而未决。"),
]


def ne_geom(spec):
    f, cond = spec.split(":", 1)
    k, v = cond.split("=", 1)
    path = P("tools/.cache/ne", f + ".geojson")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(NE.format(f), path)
    d = CACHE.get(path) or CACHE.setdefault(path, json.load(open(path)))
    gs = [shape(x["geometry"]).buffer(0) for x in d["features"] if str(x["properties"].get(k)) == v]
    assert gs, spec
    return shapely.union_all(gs)


CACHE = {}
LAND = None


def geom(a):
    global LAND
    if "ne" in a:
        g = shapely.union_all([ne_geom(s) for s in ([a["ne"]] if isinstance(a["ne"], str) else a["ne"])])
    elif "world" in a:
        y, name = a["world"]
        d = json.load(open(P("data/world", f"{y}.json")))
        g = shapely.union_all([shape(f["geometry"]).buffer(0) for f in d["features"] if f["properties"]["name"] == name])
    elif "circle" in a:
        x, y, r = a["circle"]
        g = Point(x, y).buffer(r, 24)
    elif "box" in a:
        g = shapely.box(*a["box"])
    if a.get("land"):
        if LAND is None:
            LAND = shapely.union_all([shape(f["geometry"]).buffer(0) for f in json.load(open(P("data/geo/land.geojson")))["features"]])
        g = g.intersection(LAND)
    if a.get("grow"): g = g.buffer(a["grow"])
    return g.simplify(0.01, preserve_topology=True)


def main():
    feats = []
    for (i, y0, y1, name, zh, a, ctl, ctl_zh, clm, clm_zh, note, note_zh) in D:
        g = geom(a)
        assert not g.is_empty, i
        c = max(getattr(g, "geoms", [g]), key=lambda p: p.area).representative_point()
        feats.append({"type": "Feature", "geometry": mapping(g), "properties": {
            "id": i, "from": y0, "to": y1 if y1 is not None else 9999, "name": name, "name_zh": zh,
            "control": ctl, "control_zh": ctl_zh, "claim": clm, "claim_zh": clm_zh, "note": note, "note_zh": note_zh,
            "label": [round(c.x, 2), round(c.y, 2)]}})
    out = json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":"))
    out = re.sub(r"(\d+\.\d{3})\d+", r"\1", out)
    open(P("data/disputes.json"), "w").write(out)
    print(len(feats), "disputed areas,", len(out) // 1024, "KB")


if __name__ == "__main__":
    main()
