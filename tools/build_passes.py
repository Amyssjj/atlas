"""Write data/passes.json: famous passes (关隘) with the years they stood, what they guarded and battles fought there.
Drafted from general knowledge for the prototype (AI-written, not source-checked); founding years are approximate.
Fields: name/name_zh, lon/lat, from/to (to null = still standing in 1912), circa, kind (pass | wall | gate),
guards/guards_zh (what the pass controls), summary/summary_zh, battles [[year, en, zh]], source (Wikipedia title)."""
import json
P = []
def p(id, name, zh, lon, lat, frm, to, kind, guards, guards_zh, summary, summary_zh, battles=(), source=None, circa=True):
    P.append(dict(id=id, name=name, name_zh=zh, lon=lon, lat=lat, **{"from": frm}, to=to, circa=circa, kind=kind,
                  guards=guards, guards_zh=guards_zh, summary=summary, summary_zh=summary_zh,
                  battles=[{"year": y, "name": n, "name_zh": z} for y, n, z in battles], source="https://en.wikipedia.org/wiki/" + (source or name).replace(" ", "_")))

# Guanzhong, the "land within the passes"
p("hangu-qin", "Hangu Pass (Qin)", "函谷关（秦）", 110.92, 34.63, -550, None, "pass", "Eastern gate of Qin and Guanzhong", "秦国东大门、关中门户",
  "A narrow defile in the loess between the Yellow River and the Qinling hills; for a century the eastern states' armies broke against it. After the Han moved the pass east (114 BCE) and Tong Pass took over (196), the old site remained a famous landmark.",
  "黄河与崤山之间的深谷窄道，“一夫当关，万夫莫开”。相传老子西出函谷关，应关令尹喜之请著《道德经》。战国时东方诸国多次合纵攻秦，都止步于此。汉代关址东移、东汉末潼关兴起后，旧关成为名胜古迹。",
  [(-500, "Laozi writes the Daodejing for the gatekeeper Yin Xi (legend)", "老子出关，为尹喜著《道德经》（传说）"), (-318, "Coalition of five states repulsed", "五国合纵攻秦，败于函谷"), (-241, "Last coalition against Qin fails", "最后一次合纵攻秦失败")], "Hangu Pass")
p("hangu-han", "Hangu Pass (Han)", "函谷关（汉）", 112.13, 34.72, -114, 907, "pass", "Eastern approach to Luoyang and Chang'an", "洛阳以西、关中东出要道",
  "Moved east to Xin'an in 114 BCE, it is said because a general wanted his home to count as 'within the pass'.",
  "公元前114年东移至新安，相传因楼船将军杨仆耻为“关外民”而请迁。东汉为洛阳八关之一。", [], "Hangu Pass")
p("tongguan", "Tong Pass", "潼关", 110.25, 34.54, 196, None, "pass", "Main gate between the North China Plain and Guanzhong", "关中东大门",
  "Built at the end of the Eastern Han where the Yellow River turns east; from then on the key to Chang'an from the east.",
  "东汉末年设于黄河拐弯处，取代函谷关成为关中东门。“潼关失则长安危”。",
  [(211, "Cao Cao defeats Ma Chao", "曹操破马超（潼关之战）"), (756, "Geshu Han's army destroyed; An Lushan takes Chang'an", "哥舒翰出关兵败，长安失守"),
   (1643, "Li Zicheng breaks the Ming defence", "李自成破潼关，孙传庭战死")], "Tong Pass")
p("wuguan", "Wu Pass", "武关", 110.61, 33.58, -650, None, "pass", "Southeast gate of Guanzhong, toward Chu", "关中东南门户、通南阳与楚地",
  "On the Dan River route from Guanzhong to Nanyang and the middle Yangtze; one of the 'four passes' of Qin.",
  "秦“四塞”之一，扼丹江谷道，通南阳、荆楚。",
  [(-299, "King Huai of Chu lured to Wu Pass and seized", "楚怀王被诱入武关遭扣留"), (-207, "Liu Bang enters Guanzhong through Wu Pass", "刘邦由武关入关中")], "Wu Pass")
p("xiaoguan", "Xiao Pass", "萧关", 106.25, 36.00, -300, 1400, "pass", "Northwest gate of Guanzhong against the steppe", "关中西北门户、防北方游牧",
  "Guarded the Jing River road from the Ordos and Gansu into Guanzhong; one of the 'four passes'.",
  "秦“四塞”之一，扼泾水河谷，防匈奴等南下关中。唐诗多咏萧关。",
  [(-166, "Xiongnu break through and raid toward Chang'an", "匈奴老上单于入萧关，烽火通甘泉")], "Xiao Pass")
p("dasan", "Dasan Pass", "大散关", 106.95, 34.30, -500, None, "pass", "Southwest gate of Guanzhong, road to Hanzhong and Shu", "关中西南门户、通汉中巴蜀",
  "Where the Chencang road crosses the Qinling to Hanzhong; one of the 'four passes'.",
  "秦“四塞”之一，陈仓道越秦岭入汉中处。陆游“铁马秋风大散关”。",
  [(-206, "Han Xin's secret march by Chencang", "暗度陈仓"), (1131, "Wu Jie halts the Jin at Heshangyuan", "吴玠和尚原大破金兵")], "Dasan Pass")
p("pujin", "Pujin Pass", "蒲津关", 110.30, 34.83, -300, None, "gate", "Yellow River crossing between Shanxi and Guanzhong", "晋陕之间黄河渡口",
  "A fortified crossing of the Yellow River; under the Tang an iron-chain pontoon bridge held by giant iron oxen spanned it here.",
  "黄河重要渡口。唐开元年间铸铁牛系浮桥，铁牛今已出土。", [], "Pujin Ferry")

# Luoyang
p("hulao", "Hulao Pass", "虎牢关", 113.22, 34.83, -700, None, "pass", "Eastern gate of Luoyang", "洛阳东大门",
  "Also called Sishui Pass; a loess bluff above the Yellow River on the road from the plain to Luoyang.",
  "又名汜水关、成皋，扼黄河南岸东西大道，为洛阳东门。",
  [(-203, "Liu Bang and Xiang Yu stalemate at Chenggao", "楚汉相持成皋"), (621, "Li Shimin captures Dou Jiande", "李世民虎牢之战擒窦建德")], "Hulao Pass")
p("yique", "Yique Pass", "伊阙关", 112.47, 34.56, 184, 900, "pass", "Southern gate of Luoyang", "洛阳南大门",
  "The 'gate' cut by the Yi River south of Luoyang, one of the eight passes set in 184 against the Yellow Turbans; the Longmen caves line its cliffs.",
  "伊水两山对峙如阙，东汉为防黄巾设“洛阳八关”之一。龙门石窟即开凿于此。",
  [(-293, "Bai Qi destroys the Han-Wei army", "白起伊阙之战大破韩魏")], "Yique")

# Sichuan and the Han River
p("jianmen", "Jianmen Pass", "剑门关", 105.56, 32.20, 221, None, "pass", "Northern gate of Sichuan", "蜀地北门",
  "A cleft in the sheer cliffs of the Jianmen range on the Shu road; 'one man guards it, ten thousand cannot pass' (Li Bai).",
  "大小剑山间断崖如门，诸葛亮设阁道守之。李白“一夫当关，万夫莫开”。",
  [(263, "Jiang Wei holds Zhong Hui at Jiange", "姜维据剑阁拒钟会")], "Jianmen Pass")
p("yangping", "Yangping Pass", "阳平关", 106.62, 33.15, 190, None, "pass", "Western gate of Hanzhong", "汉中西门",
  "Key to the Hanzhong basin from the west and north; the contest for Hanzhong turned on it.",
  "汉中盆地西部门户，三国时争夺汉中的关键。",
  [(215, "Cao Cao defeats Zhang Lu", "曹操阳平关破张鲁"), (219, "Liu Bei takes Hanzhong (Mount Dingjun nearby)", "刘备夺汉中，定军山斩夏侯渊")], "Yangping Pass")
p("jiangguan", "Qutang Pass", "瞿塘关（江关）", 109.55, 31.04, -280, None, "gate", "Upper Yangtze gorge between Shu and Chu", "长江三峡入蜀门户",
  "At Kuimen, the entrance of the Three Gorges; whoever held it controlled the river route between Sichuan and the middle Yangtze.",
  "夔门天下雄，扼长江三峡西口，为川楚水路咽喉。", [(222, "Liu Bei retreats to Baidi after Yiling", "夷陵败后刘备退守白帝城")], "Qutang Gorge")
p("wusheng", "Wusheng Pass", "武胜关", 114.07, 31.73, 500, None, "pass", "Road between the Huai plain and the Han River", "中原与江汉之间要道",
  "One of the 'three passes of Yiyang' through the Dabie and Tongbai hills, on the main road from Henan to Wuhan.",
  "“义阳三关”之一，扼大别山、桐柏山之间南北孔道。", [], "Wusheng Pass")

# Taihang and the north
p("jingxing", "Jingxing Pass", "井陉关", 114.20, 38.05, -300, None, "pass", "Taihang crossing between Shanxi and the Hebei plain", "太行八陉之一、晋冀通道",
  "One of the eight passages (陉) through the Taihang; also called Tumen Pass.",
  "太行八陉之第五陉，又称土门关，连通山西与河北平原。", [(-204, "Han Xin's battle with his back to the river", "韩信背水之战破赵")], "Jingxing")
p("tianjing", "Tianjing Pass", "天井关", 112.85, 35.48, -200, None, "pass", "Taihang crossing from Shangdang to Luoyang", "太行陉、上党通洛阳",
  "On the Taihang road from the Shangdang uplands down to the Yellow River and Luoyang.",
  "又名太行关，自上党南下河内、洛阳的要道。", [], "Taihang Mountains")
p("niangzi", "Niangzi Pass", "娘子关", 113.95, 37.97, 620, None, "pass", "Eastern gate of Shanxi", "山西东大门",
  "Said to be named for Princess Pingyang, sister of Tang Taizong, whose 'Lady's Army' held it.",
  "相传因唐平阳公主率“娘子军”驻守得名，为晋东门户。", [], "Niangzi Pass")
p("yanmen", "Yanmen Pass", "雁门关", 112.88, 39.19, -300, None, "wall", "Northern gate of Shanxi against the steppe", "晋北门户、防北方游牧",
  "Guarding the Juzhu mountains between Datong and Taiyuan; 'the first pass of the world' to the Tang.",
  "扼勾注山，自大同南下太原必经之地，号“天下九塞，雁门为首”。",
  [(615, "Emperor Yang of Sui besieged by the Turks", "隋炀帝雁门被围"), (986, "Yang Ye's last campaign against the Liao", "杨业抗辽")], "Yanmen Pass")
p("pingxing", "Pingxing Pass", "平型关", 113.92, 39.33, 1400, None, "wall", "Inner Great Wall between Shanxi and Hebei", "内长城关口、晋冀之间",
  "A gate in the Ming inner Great Wall on the road east from Datong.", "明内长城关口，扼大同东去要道。", [], "Pingxing Pass")
p("ningwu", "Ningwu Pass", "宁武关", 112.30, 39.00, 1450, None, "wall", "One of the 'outer three passes' of Shanxi", "明“外三关”之一",
  "Ming fortress between Yanmen and Pianguan; with them the 'outer three passes'.", "明代与雁门、偏关合称“外三关”。",
  [(1644, "Zhou Yuji's last stand against Li Zicheng", "周遇吉死守宁武关")], "Ningwu Pass")
p("pianguan", "Pianguan", "偏关", 111.50, 39.44, 1390, None, "wall", "Where the Great Wall meets the Yellow River", "长城与黄河交汇处",
  "Westernmost of the outer three passes, where the Wall comes down to the Yellow River bend.", "外三关之一，长城在此临黄河。", [], "Pianguan County")
p("shahu", "Shahu Pass", "杀虎口", 112.43, 40.33, 1544, None, "wall", "Great Wall gate to Mongolia (later a trade gate)", "长城关口、走西口通道",
  "Ming 'Kill the Hu' gate; under the Qing a customs post on the road of Shanxi migrants 'going west' to Inner Mongolia.",
  "明称杀胡口，清改杀虎口，成为“走西口”通道和税关。", [], "Shahukou")
p("zhangjiakou", "Zhangjiakou", "张家口", 114.88, 40.84, 1429, None, "wall", "Great Wall gate on the tea road to Mongolia", "长城关口、张库大道起点",
  "Ming fort and horse market; later the start of the tea caravans to Kyakhta.", "明设堡与马市，清为张库商道起点。", [], "Zhangjiakou")

# Beijing's passes
p("juyong", "Juyong Pass", "居庸关", 116.07, 40.29, -300, None, "wall", "Northwest gate of Beijing", "北京西北门户",
  "A 20-km gorge through the Jundu hills, the main road from the Mongolian plateau to Beijing.", "军都山中长约二十公里的关沟，北京西北屏障。",
  [(1213, "Mongols break through to Zhongdu", "蒙古破居庸关围中都"), (1644, "Li Zicheng enters, Beijing falls", "李自成入居庸关，北京陷落")], "Juyong Pass")
p("zijing", "Zijing Pass", "紫荆关", 115.17, 39.43, 960, None, "wall", "One of Beijing's 'inner three passes'", "明“内三关”之一",
  "With Juyong and Daoma, one of the inner three passes shielding Beijing from the west.", "与居庸、倒马合称“内三关”。",
  [(1449, "Esen breaks through after Tumu", "土木之变后也先破紫荆关逼北京")], "Zijing Pass")
p("daoma", "Daoma Pass", "倒马关", 114.65, 39.03, 960, None, "wall", "Inner three passes, southwest of Beijing", "明“内三关”之一",
  "'Horse-tumbling pass', so steep that horses fell on it.", "山路险峻，马行至此常跌倒，故名。", [], "Daoma Pass")
p("gubeikou", "Gubeikou", "古北口", 117.15, 40.69, 555, None, "wall", "Northeast gate of Beijing toward Rehe", "北京东北门户",
  "Gate in the wall on the road from Beijing to the Rehe uplands and Manchuria.", "北京通往热河、东北的要口。",
  [(1550, "Altan Khan raids to Beijing (Gengxu crisis)", "庚戌之变，俺答由古北口入犯")], "Gubeikou")
p("xifengkou", "Xifengkou", "喜峰口", 118.40, 40.40, 1400, None, "wall", "Great Wall gate on the Luan River", "滦河河谷长城关口",
  "Where the Luan River valley cuts the wall, a route between the Hebei plain and the Liao lands.", "滦河穿长城处，通辽西、蒙古。",
  [(1629, "Hong Taiji raids through the wall to Beijing", "己巳之变，皇太极破长城入关")], "Xifengkou")
p("shanhai", "Shanhai Pass", "山海关", 119.75, 40.01, 1381, None, "wall", "Where the Great Wall meets the sea; gate to Manchuria", "长城东端、东北门户",
  "Built by Xu Da in 1381 between the Yan hills and the Bohai: 'the first pass under heaven'.", "1381年徐达所筑，依山傍海，号“天下第一关”。",
  [(1644, "Wu Sangui lets the Qing through; Li Zicheng defeated", "吴三桂引清兵入关，一片石之战败李自成")], "Shanhai Pass")
p("waqiao", "Waqiao Pass", "瓦桥关", 116.10, 39.00, 959, 1127, "gate", "Song frontier against the Liao", "宋辽边界“三关”之一",
  "One of the three river passes Emperor Shizong of Later Zhou took from the Liao; under the Song, the front line held with flooded paddies.",
  "后周世宗北伐收复的“三关”之一，北宋以塘泺水网据守防辽。", [(959, "Later Zhou retakes the three passes", "周世宗北伐取三关")], "Xiongxian")

# The northwest
p("yumen", "Jade Gate", "玉门关", 93.86, 40.35, -110, 1000, "gate", "Han gate to the Western Regions (northern road)", "汉通西域门户（北道）",
  "Westernmost gate of the Han wall, through which jade from Khotan came; the Tang gate later moved east near Guazhou.",
  "汉长城西端关口，西域和田玉由此入关；唐代关址东移至瓜州附近。王之涣“春风不度玉门关”。",
  [(102, "Ban Chao asks to return 'alive through the Jade Gate'", "班超“但愿生入玉门关”")], "Yumen Pass")
p("yangguan", "Yang Pass", "阳关", 94.07, 39.93, -110, 1000, "gate", "Han gate to the Western Regions (southern road)", "汉通西域门户（南道）",
  "South of the Jade Gate, the start of the southern Silk Road along the Kunlun.", "玉门关之南，丝路南道起点。王维“西出阳关无故人”。", [], "Yangguan")
p("jiayu", "Jiayu Pass", "嘉峪关", 98.22, 39.80, 1372, None, "wall", "Western end of the Ming Great Wall", "明长城西端",
  "Built in 1372 in the Hexi Corridor's narrowest point; the end of China proper for Ming travellers.", "1372年建于河西走廊最窄处，明长城西起点，号“天下雄关”。", [], "Jiayu Pass")
p("tiemen", "Iron Gate Pass", "铁门关", 86.20, 41.85, 630, 900, "gate", "Gorge on the Silk Road north of Korla", "丝路中道峡谷关口",
  "A Tang pass in the Konqi River gorge between Karashahr and Korla.", "唐设于孔雀河峡谷，焉耆与库尔勒之间。", [], "Tiemenguan")

# The south
p("meiguan", "Mei Pass", "梅关", 114.30, 25.27, 716, None, "pass", "Dayu ridge road between Jiangxi and Guangdong", "赣粤间大庾岭商道",
  "Zhang Jiuling cut a road over the Dayu ridge in 716; the Song built the gate. The main road to Guangzhou for a thousand years.",
  "716年张九龄开凿大庾岭路，宋代立关。此后千年为岭南通中原主道。", [], "Meiguan")
p("xianxia", "Xianxia Pass", "仙霞关", 118.62, 28.32, 878, None, "pass", "Mountain road between Zhejiang and Fujian", "浙闽之间山道",
  "Huang Chao's rebels cut a road through the Xianxia hills into Fujian in 878.", "878年黄巢军开仙霞岭路入闽，为浙闽咽喉。", [], "Xianxia Pass")
p("kunlun", "Kunlun Pass", "昆仑关", 108.55, 23.06, 1000, None, "pass", "Northern gate of Yongzhou (Nanning)", "邕州（南宁）北门",
  "Guarding the road into the Nanning basin.", "扼邕州北面通道。", [(1053, "Di Qing's night attack defeats Nong Zhigao", "狄青夜袭昆仑关破侬智高")], "Kunlun Pass")
p("zhennan", "Zhennan Pass", "镇南关", 106.75, 22.01, 1100, None, "gate", "Border gate to Vietnam", "中越边关",
  "On the road from Guangxi to Hanoi; today's Friendship Pass.", "广西通安南的边关，今友谊关。", [(1885, "Feng Zicai defeats the French", "冯子材镇南关大捷")], "Friendship Pass")

out = "data/passes.json"
json.dump(P, open(out, "w"), ensure_ascii=False, indent=0)
print(len(P), "passes ->", out)
