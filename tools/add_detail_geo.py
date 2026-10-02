"""Add finer landscape names to data/geo/features.json: smaller ranges, famous peaks, basins and plains that appear
from `minzoom` on (zoomed in). `vertical` names run top to bottom along north-south ranges. Idempotent: entries
already present (same name_zh) are replaced."""
import json
P = "data/geo/features.json"
D = [  # kind, name, name_zh, lon, lat, minzoom, vertical
 ("mountain", "Lüliang Mts", "吕梁山", 111.35, 37.9, 5.5, True), ("mountain", "Zhongtiao Mts", "中条山", 111.2, 35.0, 6, False),
 ("mountain", "Taiyue Mts", "太岳山", 112.1, 36.6, 6, True), ("mountain", "Wangwu Mt", "王屋山", 112.25, 35.2, 6.5, False),
 ("mountain", "Xiao Mts", "崤山", 111.3, 34.55, 6, False), ("mountain", "Xiong'er Mts", "熊耳山", 111.6, 34.05, 6.5, False),
 ("mountain", "Funiu Mts", "伏牛山", 112.1, 33.6, 6, False), ("mountain", "Waifang Mts", "外方山", 112.6, 34.15, 6.5, False),
 ("mountain", "Mount Song", "嵩山", 113.03, 34.48, 6, False), ("mountain", "Tongbai Mts", "桐柏山", 113.4, 32.4, 6, False),
 ("mountain", "Wudang Mts", "武当山", 111.0, 32.45, 6, False), ("mountain", "Dabie Mts", "大别山", 115.8, 31.1, 5.5, False),
 ("mountain", "Liupan Mts", "六盘山", 106.2, 35.7, 5.5, True), ("mountain", "Long Mts", "陇山", 106.6, 34.95, 6.5, True),
 ("mountain", "Helan Mts", "贺兰山", 105.9, 38.8, 5.5, True), ("mountain", "Mount Taibai", "太白山", 107.77, 33.96, 6.5, False),
 ("mountain", "Mount Hua", "华山", 110.08, 34.48, 6.5, False), ("mountain", "Zhongnan Mts", "终南山", 108.85, 33.95, 6.5, False),
 ("mountain", "Mount Heng (north)", "恒山", 113.7, 39.65, 6, False), ("mountain", "Wutai Mts", "五台山", 113.6, 38.95, 6, False),
 ("mountain", "Jundu Mts", "军都山", 116.1, 40.45, 6.5, False), ("mountain", "Daqing Mts", "大青山", 111.4, 40.85, 6, False),
 ("mountain", "Lang Mts", "狼山", 107.6, 41.2, 6, False), ("mountain", "Yimeng Mts", "沂蒙山", 118.0, 35.8, 6, False),
 ("mountain", "Mount Huang", "黄山", 118.17, 30.13, 6.5, False), ("mountain", "Tianmu Mts", "天目山", 119.4, 30.35, 6.5, False),
 ("mountain", "Xuefeng Mts", "雪峰山", 110.6, 27.5, 6, True), ("mountain", "Wuling Mts", "武陵山", 109.4, 28.9, 5.5, False),
 ("mountain", "Dalou Mts", "大娄山", 107.0, 28.1, 6, False), ("mountain", "Wumeng Mts", "乌蒙山", 104.0, 26.8, 6, False),
 ("mountain", "Ailao Mts", "哀牢山", 101.3, 23.9, 6, True), ("mountain", "Cang Mts", "苍山", 100.1, 25.7, 6.5, True),
 ("mountain", "Daliang Mts", "大凉山", 102.8, 27.9, 6, False), ("mountain", "Qionglai Mts", "邛崃山", 102.9, 30.8, 6, True),
 ("mountain", "Min Mts", "岷山", 103.7, 33.0, 6, True), ("mountain", "Micang Mts", "米仓山", 106.8, 32.6, 6.5, False),
 ("mountain", "Wu Mts", "巫山", 109.8, 31.15, 6, False), ("mountain", "Luoxiao Mts", "罗霄山", 114.0, 26.6, 6, True),
 ("mountain", "Mount Lu", "庐山", 115.98, 29.55, 6.5, False), ("mountain", "Mount Heng (south)", "衡山", 112.65, 27.25, 6.5, False),
 ("mountain", "Mount Emei", "峨眉山", 103.33, 29.52, 6.5, False), ("mountain", "Qianshan Mts", "千山", 123.0, 40.6, 6.5, False),
 ("plain", "Nanyang Basin", "南阳盆地", 112.4, 32.85, 6, False), ("plain", "Hanzhong Basin", "汉中盆地", 107.1, 33.1, 6.5, False),
 ("plain", "Yuncheng Basin", "运城盆地", 110.9, 35.1, 6.5, False), ("plain", "Taiyuan Basin", "太原盆地", 112.4, 37.45, 6.5, False),
 ("plain", "Shangdang Basin", "上党盆地", 113.05, 36.2, 6.5, False), ("plain", "Yinchuan Plain", "银川平原", 106.25, 38.35, 6, False),
 ("plain", "Jianghan Plain", "江汉平原", 113.0, 30.45, 6, False), ("plain", "Chengdu Plain", "成都平原", 103.9, 30.75, 6.5, False),
 ("plain", "Yangtze Delta", "长江三角洲", 120.6, 31.3, 6, False), ("plain", "Pearl River Delta", "珠江三角洲", 113.3, 22.75, 6.5, False),
 ("plain", "Luoyang Basin", "洛阳盆地", 112.5, 34.7, 6.5, False), ("plain", "Huaibei Plain", "淮北平原", 116.5, 33.5, 6, False),
]
L = json.load(open(P))
new = {d[2] for d in D}
L = [f for f in L if f["name_zh"] not in new]
for f in L:  # long north-south ranges read better upright
    if f["name_zh"] in ("太行山", "横断山", "大兴安岭"): f["vertical"] = True
for kind, name, zh, lon, lat, mz, vert in D:
    f = {"kind": kind, "name": name, "name_zh": zh, "lon": lon, "lat": lat, "minzoom": mz}
    if vert: f["vertical"] = True
    L.append(f)
json.dump(L, open(P, "w"), ensure_ascii=False, indent=1)
print(len(L), "features")
