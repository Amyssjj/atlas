"""Write data/roads.json: major official roads (官道) — imperial highways, post roads and trade roads — with the years
they were in use and the towns they ran through. Drafted from general knowledge (AI-written, not source-checked):
routes follow the main stations only, so the lines are schematic, and the years are approximate.
Fields: id, name/name_zh, kind (imperial | post | trade), from/to, via [[lon, lat, town_zh]], summary/summary_zh, source."""
import json
T = {  # towns: lon, lat
 "咸阳": (108.71, 34.33), "长安": (108.94, 34.27), "云阳": (108.70, 34.70), "九原": (109.85, 40.58),
 "华州": (109.76, 34.51), "潼关": (110.25, 34.54), "陕州": (111.20, 34.77), "洛阳": (112.45, 34.62), "荥阳": (113.38, 34.79),
 "汴州": (114.31, 34.80), "宋州": (115.65, 34.44), "定陶": (115.57, 35.07), "临淄": (118.31, 36.85), "琅琊": (119.75, 35.60),
 "邯郸": (114.49, 36.61), "蓟": (116.38, 39.90), "北京": (116.40, 39.91), "武关": (110.61, 33.58), "南阳": (112.53, 33.00),
 "襄阳": (112.14, 32.04), "江陵": (112.24, 30.33), "岳州": (113.13, 29.37), "长沙": (112.94, 28.23), "衡阳": (112.57, 26.90),
 "郴州": (113.01, 25.77), "韶州": (113.60, 24.81), "广州": (113.26, 23.13), "南昌": (115.89, 28.68), "吉州": (114.99, 27.11),
 "虔州": (114.93, 25.83), "梅关": (114.30, 25.27), "南雄": (114.31, 25.12), "宜宾": (104.62, 28.77), "昭通": (103.72, 27.34),
 "曲靖": (103.80, 25.50), "汉中": (107.02, 33.07), "宁强": (106.25, 32.83), "广元": (105.84, 32.44), "剑门": (105.56, 32.20),
 "梓潼": (105.16, 31.64), "绵州": (104.73, 31.47), "成都": (104.07, 30.67), "郿县": (107.75, 34.27), "褒城": (106.98, 33.18),
 "陇县": (106.85, 34.90), "天水": (105.72, 34.58), "兰州": (103.83, 36.06), "凉州": (102.64, 37.93), "甘州": (100.45, 38.93),
 "肃州": (98.50, 39.73), "敦煌": (94.66, 40.14), "徐州": (117.18, 34.26), "扬州": (119.40, 32.40), "孟州": (112.80, 34.90),
 "泽州": (112.85, 35.50), "潞州": (113.10, 36.20), "太原": (112.55, 37.87), "雁门": (112.88, 39.19), "大同": (113.30, 40.08),
 "西宁": (101.78, 36.62), "日月山": (101.10, 36.43), "玛多": (98.20, 34.90), "玉树": (97.00, 33.00), "那曲": (92.05, 31.47),
 "拉萨": (91.13, 29.65), "雅安": (103.00, 29.98), "康定": (101.96, 30.05), "理塘": (100.27, 30.00), "巴塘": (99.10, 30.00),
 "昌都": (97.17, 31.14), "林芝": (94.36, 29.65), "普洱": (100.97, 22.79), "大理": (100.23, 25.60), "丽江": (100.23, 26.87),
 "德钦": (98.90, 28.48), "西昌": (102.26, 27.89), "保山": (99.17, 25.11), "保定": (115.46, 38.87), "正定": (114.57, 38.15),
 "安阳": (114.35, 36.10), "开封": (114.31, 34.80), "许州": (113.85, 34.04), "信阳": (114.07, 32.13), "武昌": (114.30, 30.55),
 "德州": (116.36, 37.43), "济南": (117.00, 36.67), "南京": (118.78, 32.06), "苏州": (120.62, 31.30), "杭州": (120.16, 30.27),
 "衢州": (118.87, 28.94), "建宁": (118.32, 27.04), "福州": (119.30, 26.08), "居庸关": (116.07, 40.29), "上都": (116.18, 42.36),
 "山海关": (119.75, 40.01), "锦州": (121.13, 41.10), "沈阳": (123.43, 41.80), "平阳": (111.52, 36.08), "西安": (108.94, 34.27),
 "桂林": (110.29, 25.27), "柳州": (109.41, 24.33), "南宁": (108.37, 22.82), "贵阳": (106.71, 26.58), "昆明": (102.71, 25.04),
 "沅州": (109.72, 27.45), "常德": (111.69, 29.03), "镇远": (108.43, 27.05), "哈密": (93.51, 42.82), "吐鲁番": (89.19, 42.95),
 "乌鲁木齐": (87.62, 43.83), "旬邑": (108.33, 35.11), "子午岭": (108.75, 35.80), "甘泉": (109.35, 36.27), "鄂尔多斯": (109.78, 39.61),
 "邢州": (114.50, 37.07), "幽州": (116.38, 39.90),
}
R = []
def road(id, name, zh, kind, frm, to, towns, summary, summary_zh, source=None):
    R.append(dict(id=id, name=name, name_zh=zh, kind=kind, **{"from": frm}, to=to,
                  via=[[*T[t], t] for t in towns], summary=summary, summary_zh=summary_zh,
                  source="https://en.wikipedia.org/wiki/" + (source or name).replace(" ", "_")))

road("zhidao", "Qin Straight Road", "秦直道", "imperial", -212, 220, ["云阳", "旬邑", "子午岭", "甘泉", "鄂尔多斯", "九原"],
     "Built by Meng Tian for the First Emperor: some 700 km nearly due north along the Ziwu ridge, so troops could reach the Xiongnu frontier in days.",
     "秦始皇命蒙恬修筑，自云阳沿子午岭几乎笔直北上九原，约七百公里，可迅速调兵至匈奴边境。", "Qin Straight Road")
road("chidao-east", "Qin Imperial Highway (east)", "秦驰道·东方道", "imperial", -220, -100, ["咸阳", "潼关", "洛阳", "荥阳", "定陶", "临淄", "琅琊"],
     "The First Emperor's 'speedways', fifty paces wide and lined with pines, ran from Xianyang to the old eastern states and the sea.",
     "秦始皇修驰道，“道广五十步，三丈而树”，自咸阳东出直达齐地海滨。", "Qin Imperial Highways")
road("chidao-north", "Qin Imperial Highway (Yan–Zhao)", "秦驰道·燕赵道", "imperial", -220, -100, ["洛阳", "孟州", "邯郸", "邢州", "正定", "蓟"],
     "North from the Luoyang region through Handan to Ji (Beijing), the old Zhao and Yan lands.", "自洛阳北渡黄河，经邯郸至蓟，贯通赵、燕故地。", "Qin Imperial Highways")
road("chidao-south", "Qin Imperial Highway (south)", "秦驰道·南方道", "imperial", -220, -100, ["咸阳", "武关", "南阳", "襄阳", "江陵"],
     "Southeast through Wu Pass to Nanyang and Jiangling, the road into the old Chu lands.", "出武关经南阳、襄阳至江陵，通楚地。", "Qin Imperial Highways")
road("wuchi", "Five-Foot Road", "五尺道", "imperial", -220, 900, ["宜宾", "昭通", "曲靖"],
     "A narrow mountain road, only five feet wide, cut by Qin from Sichuan into Yunnan.", "秦开凿的入滇山道，路宽仅五尺，自僰道（宜宾）通往滇东。", "Wuchi Road")
road("jinniu", "Jinniu Road (Shu Road)", "金牛道（蜀道）", "post", -316, None, ["汉中", "宁强", "广元", "剑门", "梓潼", "绵州", "成都"],
     "The main Shu road from Hanzhong over the mountains to Chengdu; legend says Qin tricked Shu into building it to fetch 'gold-dropping stone oxen'.",
     "汉中翻山入成都的蜀道主干。传说秦以“粪金石牛”诱蜀开路，“五丁开山”。李白“蜀道难，难于上青天”。", "Shu Roads")
road("baoxie", "Baoxie Road", "褒斜道", "post", -300, 1600, ["郿县", "褒城", "汉中"],
     "Plank roads hung on cliffs along the Bao and Xie rivers, the shortest way from Guanzhong over the Qinling to Hanzhong.",
     "沿褒水、斜水河谷凿崖架设栈道，是关中越秦岭至汉中的捷径。", "Baoxie Road")
road("liangjing", "Chang'an–Luoyang Road", "两京大道", "post", -206, 1127, ["长安", "华州", "潼关", "陕州", "洛阳"],
     "The busiest road of Han and Tang China, linking the two capitals through Tong Pass.", "汉唐最繁忙的官道，经潼关连接长安、洛阳两京。", "Chang'an")
road("hexi", "Hexi Post Road", "河西驿道", "post", -110, None, ["长安", "陇县", "天水", "兰州", "凉州", "甘州", "肃州", "敦煌"],
     "The Han road through the Hexi Corridor to Dunhuang, start of the Silk Road to the Western Regions.", "汉通西域开河西四郡后修筑的驿道，经河西走廊至敦煌，丝绸之路东段。", "Hexi Corridor")
road("bianhe", "Bian Canal Road", "汴河驿道", "post", 605, 1127, ["洛阳", "荥阳", "汴州", "宋州", "徐州", "扬州"],
     "Road along the Sui Grand Canal from Luoyang to Yangzhou, the empire's grain artery.", "沿隋唐大运河通济渠的陆路，洛阳至扬州，漕运命脉。", "Grand Canal (China)")
road("hedong", "Hedong Road", "河东道（太行驿路）", "post", -300, None, ["洛阳", "孟州", "泽州", "潞州", "太原", "雁门", "大同"],
     "From Luoyang over the Taihang via Tianjing Pass to Taiyuan and the northern frontier.", "自洛阳北越太行天井关，经上党至太原、雁门、大同。", "Taihang Mountains")
road("lingnan", "Hunan–Lingnan Road", "湘粤驿道", "post", -214, None, ["襄阳", "江陵", "岳州", "长沙", "衡阳", "郴州", "韶州", "广州"],
     "Opened when Qin conquered the south; up the Xiang River and over the Nanling to Guangzhou.", "秦平岭南时开辟，溯湘江越南岭至番禺（广州）。", "Lingnan")
road("dayu", "Dayu Ridge Road", "大庾岭道（梅岭古道）", "post", 716, None, ["南昌", "吉州", "虔州", "梅关", "南雄", "韶州", "广州"],
     "Zhang Jiuling's 716 road over Meiling became the main route between the Yangtze and Guangzhou for a thousand years.", "716年张九龄开凿大庾岭路，此后千年为长江流域通广州的主道。", "Meiguan")
road("tangbo", "Tang–Tibet Road", "唐蕃古道", "post", 641, 900, ["长安", "天水", "兰州", "西宁", "日月山", "玛多", "玉树", "那曲", "拉萨"],
     "The road Princess Wencheng took in 641 to marry the Tibetan king; envoys travelled it for two centuries.", "641年文成公主入藏所经之路，此后二百余年唐蕃使节往来不绝。", "Tang–Tibet Ancient Road")
road("shendu", "Southwest Silk Road", "灵关道—博南道（蜀身毒道）", "trade", -110, None, ["成都", "雅安", "西昌", "大理", "保山"],
     "Zhang Qian heard of Sichuan cloth reaching India this way; the Han opened it to Yunnan and Burma.", "张骞在大夏见蜀布邛竹杖，知有蜀身毒道。汉开西南夷，经越嶲、永昌通缅甸、天竺。", "Southern Silk Road")
road("chama-sc", "Tea Horse Road (Sichuan)", "茶马古道·川藏道", "trade", 1000, None, ["雅安", "康定", "理塘", "巴塘", "昌都", "林芝", "拉萨"],
     "Porters carried Sichuan brick tea to Tibet in exchange for horses, under Song, Ming and Qing tea-horse offices.", "宋明清设茶马司，以川茶换藏马；背夫负茶砖翻越横断山入藏。", "Tea Horse Road")
road("chama-yn", "Tea Horse Road (Yunnan)", "茶马古道·滇藏道", "trade", 1000, None, ["普洱", "大理", "丽江", "德钦", "昌都"],
     "Mule caravans took Pu'er tea north through Dali and Lijiang to Tibet.", "马帮驮普洱茶经大理、丽江北上入藏。", "Tea Horse Road")
road("yuan-shangdu", "Dadu–Shangdu Post Road", "两都驿路", "post", 1263, 1368, ["北京", "居庸关", "上都"],
     "The Yuan emperors moved yearly between Dadu and the summer capital Shangdu along this post road.", "元帝每年往返大都与上都之间巡幸，沿途设站赤（驿站）。", "Xanadu")
road("guanma-south", "Imperial Road South (Beijing–Guangzhou)", "官马南路（京—广）", "post", 1271, None, ["北京", "保定", "正定", "邯郸", "安阳", "开封", "许州", "信阳", "武昌", "长沙", "衡阳", "郴州", "韶州", "广州"],
     "The north–south trunk post road of the Yuan, Ming and Qing from the capital through Wuchang to Guangzhou.", "元明清自京师经河南、湖广至广州的南北干线驿路。", "Yizhan")
road("guanma-east", "Imperial Road East (Beijing–Fuzhou)", "官马东路（京—闽）", "post", 1271, None, ["北京", "德州", "济南", "徐州", "南京", "苏州", "杭州", "衢州", "建宁", "福州"],
     "Through Shandong and the Yangtze delta to Hangzhou and over the hills to Fujian.", "经山东、江南至杭州，越仙霞岭入福建。", "Yizhan")
road("guanma-west", "Imperial Road West (Beijing–Xi'an–Chengdu)", "官马西路（京—陕—川）", "post", 1271, None, ["北京", "保定", "正定", "太原", "平阳", "潼关", "西安", "汉中", "剑门", "成都"],
     "Via Taiyuan and Tong Pass to Xi'an, then the Shu road to Chengdu.", "经太原、潼关至西安，再循蜀道入成都。", "Yizhan")
road("guanma-nw", "Imperial Road Northwest (to Xinjiang)", "官马西北路（陕—甘—新）", "post", 1759, None, ["西安", "天水", "兰州", "凉州", "甘州", "肃州", "哈密", "吐鲁番", "乌鲁木齐"],
     "Extended across the Gansu corridor to Hami and Urumqi after the Qing conquest of Xinjiang.", "清平定新疆后，驿路自河西延伸至哈密、迪化（乌鲁木齐）。", "Yizhan")
road("guanma-ne", "Imperial Road Northeast (to Mukden)", "官马北路（京—盛京）", "post", 1644, None, ["北京", "山海关", "锦州", "沈阳"],
     "The Qing road from Beijing through Shanhai Pass to the old capital Mukden (Shenyang).", "清代自京师出山海关至盛京（沈阳）的驿路。", "Yizhan")
road("guanma-sw", "Imperial Road Southwest (Hunan–Guizhou–Yunnan)", "滇黔驿道", "post", 1382, None, ["武昌", "岳州", "常德", "沅州", "镇远", "贵阳", "曲靖", "昆明"],
     "Ming post road built after the conquest of Yunnan, through western Hunan and Guizhou.", "明平云南后修筑，经湘西、贵州至昆明，沿线设卫所驿站。", "Yizhan")
road("xianggui", "Hunan–Guangxi Road", "湘桂驿道", "post", -214, None, ["衡阳", "桂林", "柳州", "南宁"],
     "Over the Lingqu canal pass into Guangxi, opened with Qin's southern conquest.", "随秦平岭南、开灵渠而通，经桂林至邕州（南宁）。", "Lingqu")

json.dump(R, open("data/roads.json", "w"), ensure_ascii=False, separators=(",", ":"))
print(len(R), "roads")
