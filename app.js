// Dynasty Atlas: a data-driven 3D history map.
// Everything historical lives in data/: eras.json (time ranges + border snapshots per era),
// events.json (dated, located events), places.json (cities with the years they matter) and
// details/<era>.json (the longer story behind each event, loaded when the era is opened) and
// layers/<era>.json (map overlays for one era: rulers by polity, the armies of each battle, routes, people and
// capitals) and overlays.json (overlays that build up over time: population, religion & thought, inventions).
// Adding an era or an event means editing those files, not this code.
// Years are integers; negative years are BCE. Text fields come in pairs: `x` (English) and `x_zh`.

const BASE = document.baseURI.replace(/[^/]*([?#].*)?$/, "");
// Elevation tiles are bundled with the page (it may not load images from other sites): zoom 2-6 as PNG files,
// zoom 7 (whole map) and 8 (China proper) packed into archives in tiles/pack/ and served through the
// "atlas" protocol below. Satellite imagery (Sentinel-2, 2020) is packed the same way in tiles/sat/, every zoom.
const TILE_URL = "atlas://{z}/{x}/{y}";
const SAT_URL = "atlas://sat/{z}/{x}/{y}";
const SLIDER_MAX = 1000;

// Timeline zoom: the whole span (nonlinear, one band per dynasty), one dynasty, or a few decades.
// Each level also reveals finer events: an event's `level` is the zoom at which it first appears.
const ZOOMS = ["all", "era", "decades"];

const state = {
  eras: [], events: [], places: [],
  detail: 2, cats: [],   // event detail level shown (1 大事, 2 要事, 3 细目) and category tags (empty: all)
  range: { start: -2070, end: 1912 },
  year: -770,
  era: null,
  snapshot: null,       // borders path currently shown
  selected: "an-lushan",
  reading: false,       // story view open in the ledger
  tab: "events",        // ledger tab: "events" or "rulers"
  rulerPolity: null,    // country shown in the ruler list
  scope: null,          // the reign the timeline is narrowed to: { polity, i, label }
  borders: {},          // borders path -> GeoJSON
  details: {},          // era id -> promise of { event id -> detail }
  scale: [],            // [{era, p0, p1}] slider positions per era (zoom "all")
  zoom: 0,
  win: null,            // [start, end] years shown on the rail when zoomed in
  lang: "zh",
  show3d: true, showSat: true, showNeighbours: true, showPlaces: true, showGeo: true,
  geo: [],              // labels for rivers, lakes, mountains, plains, seas
  layers: {},           // era id -> promise of { rulers, armies, routes }
  layerData: null,      // the current era's overlays once loaded
  show: { rulers: true, armies: true, routes: true, people: true, capitals: false, faith: false, inventions: false, passes: true, roads: true, clans: true, walls: true },
  overlays: { population: [], faith: [], inventions: [] },
  passes: [],           // famous passes (关隘), data/passes.json
  roads: [],            // major official roads (官道), data/roads.json
  clans: [],            // local elite groups (豪族/士人集团), data/clans.json
  walls: [],            // Great Walls (长城) by period, data/walls.json
  playing: null,
};

const $ = (id) => document.getElementById(id);

/* ---------- language ---------- */

const UI = {
  zh: {
    title: "历代地图", events: "事件", hide: "收起", show: "展开", t3d: "3D 地形", sat: "卫星影像", neighbours: "周边政权", cities: "城市", geo: "山川",
    other: "English", map: "地图：", count: (n, era) => `${era} · ${n} 件`, countWin: (n) => `本时段 · ${n} 件`,
    back: "返回列表", prev: "上一件", next: "下一件", why: "历史意义", people: "相关人物", wiki: "维基百科", wikiOther: "English Wikipedia",
    more: "阅读详情 →", loading: "正在载入…", noStory: "这件事的详细介绍还在编写中。",
    note: "疆域为近似示意：取自开源 historical-basemaps 数据集，并参照谭其骧《中国历史地图集》人工修订。地形、海岸线和河流均为现代地理。",
    zooms: ["全部", "朝代", "数十年"], country: "国家", reignLen: (n) => `${n}年`, rulerCount: (n) => `${n} 位`, noRulers: "本时期暂无君主资料", noPeople: "本时期暂无人物资料", peopleHint: "点击人物，地图飞到其居所并显示生平", pgroups: { all: "全部", mil: "军事", pol: "政治", cul: "思想文学", art: "艺术", sci: "科技" }, scopeHint: "点击君主，时间轴缩放到其在位期间", zoomIn: "放大时间轴", zoomOut: "缩小时间轴", earlier: "向前", later: "向后",
    hint: ["点击朝代跳转 · 按 + 放大时间轴", (era) => `${era} · 每一段是一幅地图`, (era) => `${era} · 数十年视图`],
    play: "播放", pause: "暂停", year: "年份", loadError: "地图数据无法载入。",
    detail: "详略", levels: ["大事", "要事", "细目"], allCats: "全部", cat: { war: "战争", politics: "政治", reform: "改革", rebellion: "起义", culture: "文化", economy: "经济", diplomacy: "外交", science: "科技", society: "社会" },
    layers: "图层", g_map: "地图", g_pol: "政治", g_war: "军事", g_move: "交通", g_cul: "人文", rulers: "君主", armies: "军队", routes: "路线", forces: "参战双方", ruler: "在位：",
    reign: (a, b) => `${a}–${b}年在位`, troops: "兵力", unknown: "不详", losses: "伤亡",
    result: { won: "胜", lost: "败", draw: "平" },
    units: { infantry: "步兵", cavalry: "骑兵", chariots: "战车", archers: "弓兵", crossbows: "弩兵", navy: "水军", siege: "攻城", firearms: "火器", artillery: "火炮", elephants: "象兵" },
    kinds: { campaign: "进军", journey: "行程", trade: "商路", canal: "运河", wall: "长城" },
    people_l: "人物", capitals: "都城·人口", faith: "宗教思想", inventions: "发明", passes: "关隘", roads: "官道", walls: "长城", wallBy: "修筑", wallLen: (n) => `约${n.toLocaleString()}公里`, ruin: "已废弃，现为遗迹", clans: "豪族", ckinds: { gentry: "门阀士族", bloc: "地域集团", military: "军事集团", faction: "朋党", merchant: "商帮" }, seats: "郡望/根据地", families: "代表家族", members: "代表人物", drafted: "AI 整理，未经核对", cityEvents: (n) => `城中大事（${n}）· 点击跳转`,  personEvents: (n) => `相关事件（${n}）· 点击跳转`, pranks: { capital: "都城", secondary: "陪都", major: "重要城市", port: "港口", frontier: "军事重镇" }, rkinds: { imperial: "驰道", post: "驿道", trade: "商道" }, via: "途经", inUse: "使用年代",
    fields: { general: "军事家", statesman: "政治家", thinker: "思想家", poet: "诗人", writer: "文学家", historian: "史学家", scientist: "科学家", physician: "医学家", engineer: "工程师", artist: "艺术家", religious: "宗教人物", explorer: "旅行家", scholar: "学者" },
    faiths: { buddhist: "佛教", daoist: "道教", confucian: "儒家", islam: "伊斯兰教", christian: "基督教", thought: "思想", other: "其他" },
    ifields: { craft: "工艺", writing: "文字", printing: "印刷", metallurgy: "冶金", military: "军事", astronomy: "天文", math: "数学", medicine: "医学", agriculture: "农业", navigation: "航海", engineering: "工程", money: "货币" },
    pop: "人口", popOf: (m, y, k) => { const w = Math.round(m * 100); return `${k === "estimate" ? "估计约" : "约"}${w >= 10000 ? (w / 10000).toFixed(1).replace(/\.0$/, "") + "亿" : w + "万"}（${y}）`; },
    capital: "都城", works: "代表作", life: (a, b) => `${a} – ${b}`, inventor: "发明者", pkinds: { pass: "山隘", wall: "长城关口", gate: "关口" }, guards: "扼守", battles: "关前史事", built: (y) => `${y}建`,
  },
  en: {
    title: "Dynasty Atlas", events: "Events", hide: "Hide", show: "Show", t3d: "3D terrain", sat: "Satellite", neighbours: "Neighbours", cities: "Cities", geo: "Landscape",
    other: "中文", map: "Map: ", count: (n, era) => `${n} in ${era}`, countWin: (n) => `${n} in view`,
    back: "All events", prev: "Previous", next: "Next", why: "Why it matters", people: "People", wiki: "Wikipedia", wikiOther: "中文维基百科",
    more: "Read the story →", loading: "Loading…", noStory: "The full story for this event is still being written.",
    note: "Borders are approximate: from the open historical-basemaps dataset, revised by hand after Tan Qixiang's Historical Atlas of China. Terrain, coastlines and rivers are modern.",
    zooms: ["All", "Dynasty", "Decades"], country: "Country", reignLen: (n) => `${n} yr${n > 1 ? "s" : ""}`, rulerCount: (n) => `${n} rulers`, noPeople: "No famous people listed for this period", peopleHint: "Click a person to fly to where they lived and read about them", pgroups: { all: "All", mil: "Military", pol: "Politics", cul: "Thought & letters", art: "Arts", sci: "Science" }, noRulers: "No rulers recorded for this period", scopeHint: "Pick a ruler to narrow the timeline to their reign", zoomIn: "Zoom in", zoomOut: "Zoom out", earlier: "Earlier", later: "Later",
    hint: ["Click a dynasty to jump · + to zoom in", (era) => `${era} · each segment is one map`, (era) => `${era} · decades view`],
    play: "Play timeline", pause: "Pause timeline", year: "Year", loadError: "The map data could not be loaded. ",
    detail: "Detail", levels: ["Key", "Major", "All"], allCats: "All", cat: { war: "War", politics: "Politics", reform: "Reform", rebellion: "Uprising", culture: "Culture", economy: "Economy", diplomacy: "Diplomacy", science: "Science", society: "Society" },
    layers: "Layers", g_map: "Map", g_pol: "Power", g_war: "War", g_move: "Travel", g_cul: "Culture", rulers: "Rulers", armies: "Armies", routes: "Routes", forces: "Forces", ruler: "Ruler: ",
    reign: (a, b) => `r. ${a}–${b}`, troops: "Troops", unknown: "unknown", losses: "Losses",
    result: { won: "Won", lost: "Lost", draw: "Draw" },
    units: { infantry: "Infantry", cavalry: "Cavalry", chariots: "Chariots", archers: "Archers", crossbows: "Crossbows", navy: "Navy", siege: "Siege", firearms: "Firearms", artillery: "Artillery", elephants: "Elephants" },
    kinds: { campaign: "Campaign", journey: "Journey", trade: "Trade route", canal: "Canal", wall: "Wall" },
    people_l: "People", capitals: "Capitals", faith: "Faith", inventions: "Inventions", passes: "Passes", roads: "Roads", walls: "Great Walls", wallBy: "Built by", wallLen: (n) => `about ${n.toLocaleString()} km`, ruin: "Abandoned; ruins remain", clans: "Elites", ckinds: { gentry: "Great clans", bloc: "Regional bloc", military: "Military clique", faction: "Court faction", merchant: "Merchant guild" }, seats: "Home seats", families: "Families", members: "Key figures", drafted: "AI-drafted, not source-checked", cityEvents: (n) => `Events here (${n}) · click to jump`, personEvents: (n) => `Related events (${n}) · click to jump`, pranks: { capital: "Capital", secondary: "Secondary capital", major: "Major city", port: "Port", frontier: "Military stronghold" }, rkinds: { imperial: "Imperial highway", post: "Post road", trade: "Trade road" }, via: "Via", inUse: "In use",
    fields: { general: "Military", statesman: "Statesman", thinker: "Thinker", poet: "Poet", writer: "Writer", historian: "Historian", scientist: "Scientist", physician: "Physician", engineer: "Engineer", artist: "Artist", religious: "Religious figure", explorer: "Traveller", scholar: "Scholar" },
    faiths: { buddhist: "Buddhism", daoist: "Daoism", confucian: "Confucianism", islam: "Islam", christian: "Christianity", thought: "Thought", other: "Other" },
    ifields: { craft: "Craft", writing: "Writing", printing: "Printing", metallurgy: "Metalwork", military: "Military", astronomy: "Astronomy", math: "Mathematics", medicine: "Medicine", agriculture: "Farming", navigation: "Navigation", engineering: "Engineering", money: "Money" },
    pop: "Population", popOf: (m, y, k) => `${k === "estimate" ? "c. " : ""}${m} million (${y})`,
    capital: "Capital", works: "Known works", life: (a, b) => `${a} – ${b}`, inventor: "Inventor", pkinds: { pass: "Mountain pass", wall: "Great Wall gate", gate: "Gate" }, guards: "Guards", battles: "Happened here", built: (y) => `built ${y}`,
  },
};
const t = (k) => UI[state.lang][k];
const zh = () => state.lang === "zh";
// Pick the field for the current language, falling back to the other one.
const tx = (o, k) => (zh() ? o[k + "_zh"] || o[k] : o[k] || o[k + "_zh"]) || "";
const titleOf = (o) => (zh() ? o.title_zh || o.title : o.title);
const nameOf = (o) => (zh() ? o.name_zh || o.name : o.name);

function fmtYear(y, circa) {
  const n = y === 0 ? 1 : Math.abs(y);
  if (zh()) return `${circa ? "约" : ""}${y < 0 ? "前" : ""}${n}年`;
  return `${circa ? "c. " : ""}${n}${y < 0 ? " BCE" : ""}`;
}
function fmtYearParts(y) {
  const n = String(y === 0 ? 1 : Math.abs(y));
  if (zh()) return y < 0 ? ["前" + n, "年"] : [n, "年"];
  return [n, y < 0 ? "BCE" : "CE"];
}
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function applyLang() {
  document.documentElement.lang = zh() ? "zh-CN" : "en";
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  $("lang").querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === state.lang)));
  $("zoom-in").setAttribute("aria-label", t("zoomIn"));
  $("zoom-out").setAttribute("aria-label", t("zoomOut"));
  $("pan-prev").setAttribute("aria-label", t("earlier"));
  $("pan-next").setAttribute("aria-label", t("later"));
  $("slider").setAttribute("aria-label", t("year"));
  $("play").setAttribute("aria-label", state.playing ? t("pause") : t("play"));
  $("ledger-toggle").textContent = $("ledger").classList.contains("collapsed") ? t("show") : t("hide");
}

async function setLang(lang) {
  state.lang = lang;
  popup?.remove();
  try { localStorage.setItem("atlas-lang", lang); } catch {}
  applyLang();
  setEra(state.era, true);
  buildRail();
  await setYear(state.year);
  buildEventMarkers();
  renderEventStates();
  renderPolityLabels(state.borders[state.snapshot]);
  renderPlaces();
  renderGeo();
  renderLedger();
}

async function loadJSON(path) {
  // Revalidate, so a browser holding an older data file picks up the new one after a publish.
  const res = await fetch(BASE + path, { cache: "no-cache" });
  if (!res.ok) throw new Error(`Could not load ${path} (${res.status})`);
  return res.json();
}

// Hypsometric tint: sea, lowland plains, loess and hills, plateau, high peaks.
// Plains read green, hills and loess tan, mountains brown, high plateau grey, peaks white.
const RELIEF = [
  "interpolate", ["linear"], ["elevation"],
  -6000, "#3d5a6c", -200, "#6c8f9f", -1, "#9db8bf",
  0, "#a9c98e", 100, "#b6d098", 300, "#d2d6a0", 700, "#dccb94", 1200, "#c9a878",
  2000, "#ad8a64", 3000, "#97795f", 4200, "#8f8582", 5200, "#c9c5c1", 6500, "#f7f5f2",
];

/* ---------- bundled elevation tiles ---------- */

const packs = {};
function loadPack(z, px, py, dir = "pack") {
  const key = `${dir}/${z}-${px}-${py}`;
  if (!(key in packs)) {
    // Each archive is wrapped in a 1x1 PNG (the host serves only standard file types); the archive itself sits in
    // a private "tpAk" chunk: a 4-byte index length, a JSON index {"x/y": [offset, length]}, then the tile PNGs.
    packs[key] = fetch(`${BASE}tiles/${key}.png`)
      .then((r) => (r.ok ? r.arrayBuffer() : null))
      .then((png) => {
        if (!png) return null;
        const v = new DataView(png);
        for (let o = 8; o + 8 <= png.byteLength; o += 12 + v.getUint32(o)) {
          if (String.fromCharCode(v.getUint8(o + 4), v.getUint8(o + 5), v.getUint8(o + 6), v.getUint8(o + 7)) !== "tpAk") continue;
          const start = o + 8, n = v.getUint32(start, true);
          return { buf: png, base: start + 4 + n, idx: JSON.parse(new TextDecoder().decode(new Uint8Array(png, start + 4, n))) };
        }
        return null;
      })
      .catch(() => null);
  }
  return packs[key];
}
async function demTile(z, x, y) {
  if (z <= 6) {
    const r = await fetch(`${BASE}tiles/terrarium/${z}/${x}/${y}.png`).catch(() => null);
    return r?.ok ? r.arrayBuffer() : null;
  }
  const p = await loadPack(z, x >> 3, y >> 3);
  const e = p?.idx[`${x}/${y}`];
  if (e) return p.buf.slice(p.base + e[0], p.base + e[0] + e[1]);
  // Not bundled at this zoom: enlarge a quarter of the parent tile. Nearest-neighbour scaling keeps the
  // colour-encoded elevations intact, where smoothing would mix them into nonsense.
  const parent = await demTile(z - 1, x >> 1, y >> 1);
  if (!parent) return null;
  const bmp = await createImageBitmap(new Blob([parent], { type: "image/png" }));
  const c = new OffscreenCanvas(256, 256);
  const g = c.getContext("2d");
  g.imageSmoothingEnabled = false;
  g.drawImage(bmp, (x & 1) * 128, (y & 1) * 128, 128, 128, 0, 0, 256, 256);
  return (await c.convertToBlob({ type: "image/png" })).arrayBuffer();
}
// Satellite tiles: zooms below 7 are one archive each, 7-8 in 8x8 blocks, 9 (China proper) in 16x16; past the
// bundled zoom, a smoothly
// enlarged quarter of the parent.
async function satTile(z, x, y) {
  if (z < 2) return null;
  const sh = z >= 9 ? 4 : z >= 7 ? 3 : 31;
  const p = await loadPack(z, x >> sh, y >> sh, "sat");
  const e = p?.idx[`${x}/${y}`];
  if (e) return p.buf.slice(p.base + e[0], p.base + e[0] + e[1]);
  if (z <= 2) return null;
  const parent = await satTile(z - 1, x >> 1, y >> 1);
  if (!parent) return null;
  const bmp = await createImageBitmap(new Blob([parent], { type: "image/jpeg" }));
  const c = new OffscreenCanvas(256, 256);
  c.getContext("2d").drawImage(bmp, (x & 1) * 128, (y & 1) * 128, 128, 128, 0, 0, 256, 256);
  return (await c.convertToBlob({ type: "image/jpeg", quality: 0.9 })).arrayBuffer();
}
maplibregl.addProtocol("atlas", async (params) => {
  const sat = params.url.startsWith("atlas://sat/");
  const [z, x, y] = params.url.slice(sat ? "atlas://sat/".length : "atlas://".length).split("/").map(Number);
  const data = await (sat ? satTile(z, x, y) : demTile(z, x, y));
  if (!data) throw new Error(`no ${sat ? "imagery" : "elevation"} tile ${z}/${x}/${y}`);
  return { data };
});

// Two looks: satellite colours with light shading, or the drawn relief map (hypsometric tint, stronger shading).
const SKY = {
  sat: { "sky-color": "#3f86c8", "horizon-color": "#cfe4f2", "fog-color": "#d6e6f0",
         "sky-horizon-blend": 0.5, "horizon-fog-blend": 0.7, "fog-ground-blend": 0.3, "atmosphere-blend": 0.8 },
  relief: { "sky-color": "#a9c4d0", "horizon-color": "#e3ebe8", "fog-color": "#e3ebe8",
            "sky-horizon-blend": 0.6, "horizon-fog-blend": 0.6, "fog-ground-blend": 0.4, "atmosphere-blend": 0.5 },
};
// Relief is exaggerated more as you zoom in, so hills and ranges keep standing out at close range.
const terrainExaggeration = (z) => Math.min(5, 2 + Math.max(0, z - 5) * 0.9);
function setTerrainForZoom() {
  if (!state.show3d) return;
  const e = Math.round(terrainExaggeration(map.getZoom()) * 10) / 10;
  if (e === state.terrainExag) return;
  state.terrainExag = e;
  // Calling setTerrain again would rebuild the terrain and stall tile loading; adjust the live terrain instead.
  if (map.terrain) { map.terrain.exaggeration = e; map.triggerRepaint(); }
  else map.setTerrain({ source: "dem-terrain", exaggeration: e });
}
function applyLook() {
  const sat = state.showSat;
  document.documentElement.classList.toggle("sat", sat);
  if (!map?.getLayer("satellite")) return;
  map.setLayoutProperty("satellite", "visibility", sat ? "visible" : "none");
  map.setLayoutProperty("relief", "visibility", sat ? "none" : "visible");
  map.setPaintProperty("hillshade", "hillshade-exaggeration", sat
    ? ["interpolate", ["linear"], ["zoom"], 3, 0.3, 6, 0.55, 8, 0.8]
    : ["interpolate", ["linear"], ["zoom"], 3, 0.45, 6, 0.6, 8, 0.7]);
  map.setPaintProperty("hillshade", "hillshade-highlight-color", sat
    ? ["rgba(255,244,214,0.5)", "rgba(255,244,214,0.35)", "rgba(255,244,214,0.2)", "rgba(255,244,214,0.35)"] : ["#fffdf5", "#fffdf5", "#fff8e8", "#fffdf5"]);
  map.setPaintProperty("hillshade", "hillshade-shadow-color", sat
    ? ["rgba(8,14,6,0.95)", "rgba(8,14,6,0.8)", "rgba(8,14,6,0.6)", "rgba(8,14,6,0.8)"] : ["#3a3328", "#4a3f33", "#3a3328", "#2e2a24"]);
  map.setPaintProperty("lakes", "fill-opacity", sat ? 0 : 0.9);
  map.setPaintProperty("bg", "background-color", sat ? "#1d4f86" : "#9db8bf");
  map.setSky(SKY[sat ? "sat" : "relief"]);
}

function buildStyle() {
  const dem = { type: "raster-dem", tiles: [TILE_URL], tileSize: 256, encoding: "terrarium", maxzoom: 8, bounds: [60, 10, 145, 55] };
  return {
    version: 8,
    sources: {
      dem, "dem-terrain": { ...dem },
      sat: { type: "raster", tiles: [SAT_URL], tileSize: 256, maxzoom: 9,
             attribution: "Imagery: Sentinel-2 2020, Copernicus/Sentinel Hub (CC BY 4.0)" },
      rivers: { type: "geojson", data: BASE + "data/geo/rivers.geojson" },
      lakes: { type: "geojson", data: BASE + "data/geo/lakes.geojson" },
      borders: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
      routes: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
      roads: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
      clans: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
      walls: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
    },
    sky: SKY.relief,
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#9db8bf" } },
      { id: "relief", type: "color-relief", source: "dem", paint: { "color-relief-color": RELIEF } },
      { id: "satellite", type: "raster", source: "sat", layout: { visibility: "none" },
        paint: { "raster-fade-duration": 150, "raster-contrast": 0.08, "raster-saturation": 0.05 } },
      // Light from several directions so ranges read clearly whichever way they run.
      { id: "hillshade", type: "hillshade", source: "dem", paint: {
          "hillshade-method": "multidirectional",
          "hillshade-highlight-color": ["#fffdf5", "#fffdf5", "#fff8e8", "#fffdf5"],
          "hillshade-shadow-color": ["#3a3328", "#4a3f33", "#3a3328", "#2e2a24"],
          "hillshade-illumination-direction": [270, 315, 0, 45],
          "hillshade-illumination-altitude": [30, 30, 30, 30],
          "hillshade-exaggeration": ["interpolate", ["linear"], ["zoom"], 3, 0.45, 6, 0.6, 8, 0.7] } },
      // Modern rivers and lakes (Natural Earth); minor rivers appear as you zoom in.
      { id: "lakes", type: "fill", source: "lakes", paint: { "fill-color": "#86afc2", "fill-opacity": 0.9 } },
      { id: "rivers-minor", type: "line", source: "rivers", minzoom: 4.5, filter: [">", ["get", "rank"], 5],
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": "#4a82a0", "line-opacity": 0.85,
                 "line-width": ["interpolate", ["linear"], ["zoom"], 4.5, 0.5, 8, 2.2] } },
      { id: "rivers", type: "line", source: "rivers", filter: ["<=", ["get", "rank"], 5],
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": "#4f86a3", "line-opacity": 0.9,
                 "line-width": ["interpolate", ["linear"], ["zoom"], 3, ["case", ["<=", ["get", "rank"], 3], 1.2, 0.6], 8, ["case", ["<=", ["get", "rank"], 3], 4.5, 3]] } },
      { id: "neighbour-fill", type: "fill", source: "borders", filter: ["!", ["get", "focus"]],
        paint: { "fill-color": ["coalesce", ["get", "color"], "#6b5a7a"],
                 "fill-opacity": ["case", ["!=", ["get", "name_zh"], ""], 0.2, 0.07] } },
      { id: "neighbour-line", type: "line", source: "borders", filter: ["!", ["get", "focus"]],
        paint: { "line-color": "#4b4058", "line-width": 1, "line-opacity": 0.55, "line-dasharray": [3, 2] } },
      // States that carry their own colour (e.g. the Warring States) get it; dynasties use jade.
      { id: "focus-fill", type: "fill", source: "borders", filter: ["get", "focus"],
        paint: { "fill-color": ["coalesce", ["get", "color"], "#2c7a68"],
                 "fill-opacity": ["case", ["has", "color"], 0.34, 0.2] } },
      { id: "focus-casing", type: "line", source: "borders", filter: ["get", "focus"],
        paint: { "line-color": "#f6f3e8", "line-width": 5, "line-opacity": 0.7, "line-blur": 1 } },
      { id: "focus-line", type: "line", source: "borders", filter: ["get", "focus"],
        paint: { "line-color": "#b93a26", "line-width": ["case", ["has", "color"], 1.4, 2.2] } },
      // Elite groups (豪族/士人集团): a soft tint over their home region with a dashed edge, coloured by kind.
      { id: "clan-fill", type: "fill", source: "clans", paint: { "fill-color": ["get", "color"], "fill-opacity": 0.3 } },
      { id: "clan-line", type: "line", source: "clans", layout: { "line-join": "round" },
        paint: { "line-color": ["get", "color"], "line-width": 2, "line-opacity": 0.95, "line-dasharray": [2, 1.5] } },
      // Great Walls (长城): manned walls as a dark line with battlement ticks; abandoned ones as faint dashes.
      { id: "wall-ruin", type: "line", source: "walls", filter: ["==", ["get", "ruin"], true],
        paint: { "line-color": "#6b5a48", "line-opacity": 0.45, "line-width": 1.6, "line-dasharray": [2, 2] } },
      { id: "wall-casing", type: "line", source: "walls", filter: ["!=", ["get", "ruin"], true], layout: { "line-join": "round", "line-cap": "round" },
        paint: { "line-color": "#efe2c2", "line-opacity": 0.85, "line-width": ["interpolate", ["linear"], ["zoom"], 3, 5, 8, 10] } },
      { id: "wall-line", type: "line", source: "walls", filter: ["!=", ["get", "ruin"], true], layout: { "line-join": "round", "line-cap": "round" },
        paint: { "line-color": "#5a4030", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 2.5, 8, 5] } },
      { id: "wall-crenel", type: "line", source: "walls", filter: ["!=", ["get", "ruin"], true],
        paint: { "line-color": "#3a2a1e", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 5, 8, 10], "line-dasharray": [0.4, 1.2] } },
      { id: "wall-hit", type: "line", source: "walls", paint: { "line-color": "#000", "line-opacity": 0, "line-width": 14 } },
      // Official roads (官道): a pale casing with a dark brown line; trade roads dotted.
      { id: "road-casing", type: "line", source: "roads", layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": "#f3e9cf", "line-opacity": 0.75, "line-width": ["interpolate", ["linear"], ["zoom"], 3, 4, 8, 8] } },
      { id: "road-line", type: "line", source: "roads", layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": ["match", ["get", "kind"], "imperial", "#8a2f1c", "trade", "#7a5a1e", "#4a3424"],
                 "line-width": ["interpolate", ["linear"], ["zoom"], 3, 2, 8, 4.5],
                 "line-dasharray": ["match", ["get", "kind"], "trade", ["literal", [1, 1.5]], ["literal", [1, 0]]] } },
      { id: "road-hit", type: "line", source: "roads", paint: { "line-color": "#000", "line-opacity": 0, "line-width": 14 } },
      // Routes: campaigns and journeys dashed, trade routes, canals and walls solid.
      { id: "route-casing", type: "line", source: "routes", layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": "#f6f3e8", "line-opacity": 0.8, "line-width": ["match", ["get", "kind"], "wall", 7, 6] } },
      { id: "route-solid", type: "line", source: "routes", filter: ["in", ["get", "kind"], ["literal", ["trade", "canal", "wall"]]],
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": ["match", ["get", "kind"], "trade", "#b8862b", "canal", "#2a7fb0", "#5a4636"],
                 "line-width": ["match", ["get", "kind"], "wall", 4, 3] } },
      { id: "route-dashed", type: "line", source: "routes", filter: ["in", ["get", "kind"], ["literal", ["campaign", "journey"]]],
        layout: { "line-join": "round" },
        paint: { "line-color": ["match", ["get", "kind"], "campaign", "#b93a26", "#2f5f8a"], "line-width": 3, "line-dasharray": [2, 1.2] } },
    ],
  };
}

let map;
const markers = { events: new Map(), places: [], polities: [], polityEls: [], armies: [], routes: [] };

/* ---------- time scale ---------- */

// Zoom "all": each era gets slider width by the square root of its length.
function buildScale() {
  const w = state.eras.map((e) => Math.sqrt(e.end - e.start + 1));
  const total = w.reduce((a, b) => a + b, 0);
  let p = 0;
  state.scale = state.eras.map((era, i) => {
    const p0 = p;
    p += (w[i] / total) * SLIDER_MAX;
    return { era, p0, p1: p };
  });
}
// Zoomed in, the rail is linear over state.win; year y covers [y, y + 1).
function yearToPos(y) {
  if (state.zoom > 0) {
    const [a, b] = state.win;
    return ((Math.max(a, Math.min(b + 1, y)) - a) / (b + 1 - a)) * SLIDER_MAX;
  }
  const s = state.scale.find((s) => y >= s.era.start && y <= s.era.end) || state.scale[state.scale.length - 1];
  return s.p0 + ((y - s.era.start) / (s.era.end + 1 - s.era.start)) * (s.p1 - s.p0);
}
function posToYear(p) {
  if (state.zoom > 0) {
    const [a, b] = state.win;
    return Math.min(b, Math.floor(a + (p / SLIDER_MAX) * (b + 1 - a)));
  }
  const s = state.scale.find((s) => p >= s.p0 && p < s.p1) || state.scale[state.scale.length - 1];
  return Math.min(s.era.end, Math.floor(s.era.start + ((p - s.p0) / (s.p1 - s.p0)) * (s.era.end + 1 - s.era.start)));
}

// The decades window is a quarter of the dynasty, kept between 12 and 60 years.
function decadesSpan(era) {
  return Math.max(12, Math.min(60, Math.round((era.end - era.start + 1) / 4)));
}
function windowFor(zoom, year) {
  const era = eraFor(year);
  if (zoom === 1) return [era.start, era.end];
  const span = decadesSpan(era);
  let a = Math.round(year - span / 2);
  a = Math.max(state.range.start, Math.min(state.range.end - span + 1, a));
  return [a, a + span - 1];
}
const inWindow = (y) => state.zoom === 0 || (y >= state.win[0] && y <= state.win[1]);

function setZoom(z, year = state.year) {
  z = Math.max(0, Math.min(ZOOMS.length - 1, z));
  if (z === state.zoom && z !== 2) return;
  state.zoom = z;
  state.scope = null;
  state.win = z ? windowFor(z, year) : null;
  if (z && !inWindow(state.year)) setYear(Math.max(state.win[0], Math.min(state.win[1], year)));
  refreshTimeline();
}
function pan(dir) {
  if (!state.zoom) return;
  stop();
  state.scope = null;
  const [a, b] = state.win;
  if (state.zoom === 1) {
    const i = state.eras.indexOf(eraFor(a)) + dir;
    if (!state.eras[i]) return;
    state.win = [state.eras[i].start, state.eras[i].end];
    setYear(state.eras[i].start);
  } else {
    const span = b - a;
    const step = Math.max(1, Math.round((span + 1) / 2)) * dir;
    const na = Math.max(state.range.start, Math.min(state.range.end - span, a + step));
    state.win = [na, na + span];
    setYear(Math.max(na, Math.min(na + span, state.year + step)));
  }
  refreshTimeline();
}
function refreshTimeline() {
  buildRail();
  $("slider").value = yearToPos(state.year);
  buildEventMarkers();
  renderEventStates();
  if (!state.reading) renderLedger();
}

function eraFor(year) {
  return state.eras.find((e) => year >= e.start && year <= e.end) || state.eras[state.eras.length - 1];
}
function snapshotFor(era, year) {
  let snap = era.snapshots[0];
  for (const s of era.snapshots) if (year >= s.from) snap = s;
  return snap;
}

async function setYear(year, opts = {}) {
  state.year = Math.max(state.range.start, Math.min(state.range.end, Math.round(year)));
  const era = eraFor(state.year);
  const eraChanged = era !== state.era;
  if (eraChanged) setEra(era, true);
  // Keep the zoomed window around the current year.
  if ((state.zoom && !inWindow(state.year)) || (eraChanged && state.zoom === 1)) {
    state.scope = null;
    state.win = windowFor(state.zoom, state.year);
    refreshTimeline();
  } else if (eraChanged) {
    buildRail();
    buildEventMarkers();
    if (!state.reading) renderLedger();
  }
  const [num, suffix] = fmtYearParts(state.year);
  $("year").textContent = num;
  $("year-suffix").textContent = suffix;
  if (!opts.fromSlider) $("slider").value = yearToPos(state.year);
  const snap = snapshotFor(era, state.year);
  const label = tx(snap, "label");
  $("era-snap").textContent = label ? t("map") + label : "";
  $("era-snap").hidden = !label;
  document.querySelectorAll(".band.snap").forEach((b) => b.classList.toggle("current", b.dataset.path === snap.borders && +b.dataset.from === snap.from));
  if (snap.borders !== state.snapshot) await setSnapshot(snap.borders);
  renderEventStates();
  renderPlaces();
  renderOverlays();
}

function setEra(era, quiet) {
  state.era = era;
  const seal = $("era-glyph");
  seal.textContent = era.glyph;
  seal.classList.toggle("double", era.glyph.length > 1);
  $("era-name").textContent = zh() ? era.name_zh : era.name;
  $("era-zh").textContent = `${zh() ? era.name : era.name_zh} · ${fmtYear(era.start)} – ${fmtYear(era.end)}`;
  $("era-summary").textContent = tx(era, "summary");
  const note = tx(era, "note");
  $("era-note").textContent = note;
  $("era-note").hidden = !note;
  document.querySelectorAll(".band.era-band").forEach((b) => b.classList.toggle("current", b.dataset.era === era.id));
  $("scale-hint").textContent = hintText();
  loadDetails(era);
  state.layerData = null;
  popup?.remove();
  loadLayers(era).then((d) => { if (state.era === era) { state.layerData = d; renderOverlays(); if (state.tab === "events" && !state.reading) renderLedger(); } });
  if (!quiet) {
    buildEventMarkers();
    if (!state.reading) renderLedger();
  }
}

async function setSnapshot(path) {
  state.snapshot = path;
  const gj = state.borders[path] || (state.borders[path] = await loadJSON(path));
  if (state.snapshot !== path) return; // a newer request won
  map.getSource("borders")?.setData(gj);
  renderPolityLabels(gj);
}

function renderPolityLabels(gj) {
  scheduleDeclutter();
  markers.polities.forEach((m) => m.remove());
  markers.polities = [];
  markers.polityEls = [];
  if (!gj) return;
  for (const f of gj.features) {
    const p = f.properties;
    // Neighbours with a Chinese name are labelled even when small; others only when large.
    const minArea = p.kind === "state" ? 2 : p.name_zh ? 3 : 20;
    if (!p.focus && (p.area < minArea || !state.showNeighbours || p.nolabel)) continue;
    const el = document.createElement("div");
    el.className = "mk-polity" + (p.focus ? " focus" : p.name_zh ? " neighbour" : "") +
      (p.kind === "state" ? " state" : "") + (p.minor ? " minor" : "");
    if (zh()) el.innerHTML = p.name_zh ? esc(p.name_zh) : `<small>${esc(p.name)}</small>`;
    else el.innerHTML = `<span>${esc(p.name)}</span>` + (p.name_zh ? `<small lang="zh-CN">${esc(p.name_zh)}</small>` : "");
    markers.polities.push(new maplibregl.Marker({ element: el }).setLngLat(p.label).addTo(map));
    markers.polityEls.push({ el, name: p.name, focus: p.focus, state: p.kind === "state" });
  }
  updateRulers();
}

/* ---------- overlay layers: rulers, armies, routes ---------- */

function loadLayers(era) {
  if (!state.layers[era.id]) state.layers[era.id] = loadJSON(`data/layers/${era.id}.json`).catch(() => ({}));
  return state.layers[era.id];
}

function rulerAt(name, year) {
  // In a handover year two reigns overlap; the newer ruler wins.
  return (state.layerData?.rulers?.[name] || []).findLast((r) => year >= r.from && year <= r.to);
}
// The name a learner knows (汉武帝, 冒顿单于), plus the personal name when the title doesn't already contain it.
function rulerText(r) {
  if (zh()) return [r.title_zh || r.name_zh, r.title_zh && !r.title_zh.includes(r.name_zh) ? r.name_zh : ""];
  return [r.title || r.name, r.title && !r.title.includes(r.name) ? r.name : ""];
}

function renderOverlays() {
  scheduleDeclutter();
  if (state.tab !== "events") renderLedger();
  updateRulers();
  renderArmies();
  renderRoutes();
  renderPeople();
  renderCapitals();
  renderFaith();
  renderInventions();
  renderPasses();
  renderRoads();
  renderClans();
  renderWalls();
  renderPopulation();
}

/* People, capitals, religion & thought, inventions: small markers that open a card. */

let popup;
function showCard(lngLat, html) {
  popup?.remove();
  popup = new maplibregl.Popup({ className: "atlas-pop", maxWidth: "300px", offset: 14, focusAfterOpen: false })
    .setLngLat(lngLat).setHTML(html).addTo(map);
  // Event lists open at the city's current period and jump to that moment when clicked.
  const list = popup.getElement().querySelector(".pc-events"), now = list?.querySelector(".now");
  if (now) list.scrollTop = now.parentElement.offsetTop - list.offsetTop - 4;
  popup.getElement().querySelectorAll("[data-ev]").forEach((b) => b.addEventListener("click", () => {
    popup?.remove();
    state.reading = false;
    selectEvent(b.dataset.ev);
  }));
}
function wikiA(url) {
  return url ? `<a href="${esc(wikiLink(url))}" target="_blank" rel="noopener">${t("wiki")} ↗</a>` : "";
}
function pointMarkers(key, items, make) {
  (markers[key] || []).forEach((m) => m.remove());
  markers[key] = [];
  for (const it of items) {
    const { el, card, anchor } = make(it);
    el.dataset.name = nameOf(it);
    if (card) el.addEventListener("click", (e) => { e.stopPropagation(); showCard([it.lon, it.lat], card()); });
    markers[key].push(new maplibregl.Marker({ element: el, anchor: anchor || "center" }).setLngLat([it.lon, it.lat]).addTo(map));
  }
}

function renderPeople() {
  const list = state.show.people ? (state.layerData?.people || []) : [];
  // Alive this year; a person with no birth year shows for the 40 years before death.
  const alive = list.filter((p) => state.year >= personSpan(p)[0] && state.year <= personSpan(p)[1]);
  pointMarkers("people", alive, (p) => {
    const el = document.createElement("div");
    el.className = "mk-person f-" + p.field;
    const nm = nameOf(p);
    el.innerHTML = `<i>${esc((p.name_zh || p.name).slice(0, 1))}</i><span>${esc(nm)}<small>${esc(t("fields")[p.field] || "")}</small></span>`;
    return { el, anchor: "left", card: () => personCard(p) };
  });
}
function personLife(p) {
  return p.died != null ? t("life")(p.born != null ? fmtYear(p.born, p.circa) : "?", fmtYear(p.died, p.circa)) : (zh() ? "生卒不详" : "dates unknown");
}
function personCard(p) {
  const works = (p.works || []).map((w) => zh() ? `《${esc(w.title_zh || w.title)}》` : `<i>${esc(w.title)}</i>`).join(zh() ? "" : ", ");
  const line = p.line_zh ? `<blockquote><span lang="zh-CN">${esc(p.line_zh)}</span>${!zh() && p.line_en ? `<em>${esc(p.line_en)}</em>` : ""}</blockquote>` : "";
  return `<div class="pc-kind">${esc(t("fields")[p.field] || p.field)} · ${personLife(p)}</div>
    <h4>${esc(nameOf(p))} <span lang="${zh() ? "en" : "zh-CN"}">${esc(zh() ? p.name : p.name_zh)}</span></h4>
    <p>${esc(tx(p, "known_for"))}</p>${works ? `<p class="pc-works"><b>${t("works")}</b> ${works}</p>` : ""}${line}
    ${personEventList(p)}<p class="pc-meta">${esc(tx(p, "place"))} ${wikiA(p.source)}</p>`;
}
function personEventList(p) {
  const evs = personEvents(p);
  if (!evs.length) return "";
  // Highlight the latest event up to the current year, so the list opens there.
  const last = evs.filter((ev) => ev.year <= state.year).pop() || evs[0];
  return `<p class="pc-works"><b>${t("personEvents")(evs.length)}</b></p>${eventButtons(evs, (ev) => ev === last)}`;
}
// Years a person's marker is on the map: their life, or the 40 years before death when the birth year is unknown.
const personSpan = (p) => p.show ? p.show : [p.born ?? p.died - 40, p.died];

function renderCapitals() {
  const list = state.show.capitals ? (state.layerData?.capitals || []) : [];
  const now = list.filter((c) => state.year >= c.from && state.year <= c.to);
  pointMarkers("capitals", now, (c) => {
    const el = document.createElement("div");
    el.className = "mk-capital";
    el.innerHTML = `<i>★</i><span>${esc(nameOf(c))}<small>${esc(zh() ? (c.polity_zh || c.polity) + "都" : c.polity)}</small></span>`;
    return { el, anchor: "left", card: () => `<div class="pc-kind">${t("capital")} · ${esc(zh() ? c.polity_zh || c.polity : c.polity)}</div>
      <h4>${esc(nameOf(c))}${c.modern_zh ? ` <span>${zh() ? "今" : "modern "}${esc(c.modern_zh)}</span>` : ""}</h4>
      <p class="pc-meta">${fmtYear(c.from)} – ${fmtYear(c.to)}</p>${tx(c, "note") ? `<p>${esc(tx(c, "note"))}</p>` : ""}${capitalEvents(c)}` };
  });
}

// Faith sites and inventions: those of the current era up to this year (in the decades view, of the window).
function cumulative(key, items, cls, glyph, kindLabel) {
  const start = state.zoom === 2 ? state.win[0] : state.era.start;
  const shown = items.filter((x) => x.year <= state.year && x.year >= start);
  pointMarkers(key, shown, (x) => {
    const recent = x.year >= state.era.start;
    const el = document.createElement("div");
    el.className = `${cls} k-${x.kind || x.field}` + (recent ? "" : " old");
    el.innerHTML = `<i>${glyph(x)}</i>` + (recent ? `<span>${esc(nameOf(x))}</span>` : "");
    el.title = `${fmtYear(x.year, x.circa)} · ${nameOf(x)}`;
    return { el, anchor: recent ? "left" : "center", card: () => `<div class="pc-kind">${esc(kindLabel(x))} · ${fmtYear(x.year, x.circa)}</div>
      <h4>${esc(nameOf(x))} <span lang="${zh() ? "en" : "zh-CN"}">${esc(zh() ? x.name : x.name_zh)}</span></h4>
      <p>${esc(tx(x, "summary"))}</p>${x.inventor ? `<p class="pc-works"><b>${t("inventor")}</b> ${esc(zh() ? x.inventor_zh || x.inventor : x.inventor)}</p>` : ""}
      <p class="pc-meta">${esc(tx(x, "place"))} ${wikiA(x.source)}</p>` };
  });
}
const FAITH_GLYPH = { buddhist: "佛", daoist: "道", confucian: "儒", islam: "伊", christian: "基", thought: "思", other: "宗" };
function renderFaith() {
  cumulative("faith", state.show.faith ? state.overlays.faith : [], "mk-faith", (x) => FAITH_GLYPH[x.kind] || "宗", (x) => t("faiths")[x.kind] || x.kind);
}
// Passes stand from their founding year until abandoned; battles already fought there are listed on the card.
function renderPasses() {
  const list = state.show.passes ? state.passes.filter((x) => state.year >= x.from && (x.to == null || state.year <= x.to)) : [];
  pointMarkers("passes", list, (x) => {
    const el = document.createElement("div");
    el.className = "mk-pass k-" + x.kind;
    el.innerHTML = `<i>关</i><span>${esc(nameOf(x))}</span>`;
    return { el, anchor: "left", card: () => {
      const fought = x.battles.filter((b) => b.year <= state.year);
      return `<div class="pc-kind">${esc(t("pkinds")[x.kind] || "")} · ${esc(t("built")(fmtYear(x.from, x.circa)))}</div>
        <h4>${esc(nameOf(x))} <span lang="${zh() ? "en" : "zh-CN"}">${esc(zh() ? x.name : x.name_zh)}</span></h4>
        <p class="pc-works"><b>${t("guards")}</b> ${esc(tx(x, "guards"))}</p><p>${esc(tx(x, "summary"))}</p>
        ${fought.length ? `<p class="pc-works"><b>${t("battles")}</b></p><ul class="pc-battles">${fought.map((b) =>
          `<li><span>${fmtYear(b.year)}</span> ${esc(zh() ? b.name_zh : b.name)}</li>`).join("")}</ul>` : ""}
        <p class="pc-meta">${wikiA(x.source)}</p>`;
    } };
  });
}
// Roads in use this year: lines on the map, a name label near the middle, and a card with the stations.
function roadCard(r) {
  return `<div class="pc-kind">${esc(t("rkinds")[r.kind] || "")} · ${t("inUse")} ${fmtYear(r.from, true)} – ${r.to == null ? (zh() ? "清末" : "1912") : fmtYear(r.to)}</div>
    <h4>${esc(nameOf(r))} <span lang="${zh() ? "en" : "zh-CN"}">${esc(zh() ? r.name : r.name_zh)}</span></h4>
    <p>${esc(tx(r, "summary"))}</p>
    <p class="pc-works"><b>${t("via")}</b> <span lang="zh-CN">${r.via.map((v) => esc(v[2])).join(" — ")}</span></p>
    <p class="pc-meta">${wikiA(r.source)}</p>`;
}
function renderRoads() {
  const list = state.show.roads ? state.roads.filter((r) => state.year >= r.from && (r.to == null || state.year <= r.to)) : [];
  map.getSource("roads")?.setData({ type: "FeatureCollection", features: list.map((r) => ({
    type: "Feature", properties: { id: r.id, kind: r.kind }, geometry: { type: "LineString", coordinates: r.via.map((v) => [v[0], v[1]]) } })) });
  (markers.roads || []).forEach((m) => m.remove());
  markers.roads = [];
  for (const r of list) {
    const el = document.createElement("div");
    el.className = "mk-road k-" + r.kind;
    el.textContent = nameOf(r);
    el.dataset.name = nameOf(r);
    el.addEventListener("click", (e) => { e.stopPropagation(); showCard(r.via[Math.floor(r.via.length / 2)], roadCard(r)); });
    // Label halfway along, between the two middle stations.
    const i = Math.floor((r.via.length - 1) / 2), a = r.via[i], b = r.via[Math.min(i + 1, r.via.length - 1)];
    markers.roads.push(new maplibregl.Marker({ element: el }).setLngLat([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]).addTo(map));
  }
}
// Elite groups active this year: a tinted area around their home seats and a label with a card.
const CLAN = { gentry: ["#8e5bb5", "族"], bloc: ["#d07a22", "集"], military: ["#b0405f", "军"], faction: ["#2f6fb0", "党"], merchant: ["#a88420", "商"] };
function clanCard(g) {
  return `<div class="pc-kind">${esc(t("ckinds")[g.kind] || "")} · ${fmtYear(g.from, true)} – ${fmtYear(g.to, true)}</div>
    <h4>${esc(nameOf(g))} <span lang="${zh() ? "en" : "zh-CN"}">${esc(zh() ? g.name : g.name_zh)}</span></h4>
    <p>${esc(tx(g, "summary"))}</p>
    <p class="pc-works"><b>${t("families")}</b> ${esc(tx(g, "families"))}</p>
    <p class="pc-works"><b>${t("members")}</b> ${esc(tx(g, "people"))}</p>
    <p class="pc-works"><b>${t("seats")}</b> <span lang="zh-CN">${g.seats.map((v) => esc(v[2])).join("、")}</span></p>
    <p class="pc-meta">${t("drafted")} ${wikiA(g.source)}</p>`;
}
function renderClans() {
  const list = state.show.clans ? state.clans.filter((g) => state.year >= g.from && state.year <= g.to) : [];
  map.getSource("clans")?.setData({ type: "FeatureCollection", features: list.map((g) => ({
    type: "Feature", properties: { id: g.id, color: CLAN[g.kind][0] }, geometry: g.geometry })) });
  pointMarkers("clans", list.map((g) => ({ ...g, lon: g.label[0], lat: g.label[1] })), (g) => {
    const el = document.createElement("div");
    el.className = "mk-clan k-" + g.kind;
    el.style.setProperty("--c", CLAN[g.kind][0]);
    el.innerHTML = `<i>${CLAN[g.kind][1]}</i><span>${esc(nameOf(g))}</span>`;
    return { el, anchor: "left", card: () => clanCard(g) };
  });
}
// Great Walls: those manned this year drawn in full with a label; those abandoned before now as faint ruins.
function wallCard(w) {
  const ruin = state.year > w.to;
  return `<div class="pc-kind">${t("walls")} · ${fmtYear(w.from, true)} – ${fmtYear(w.to, true)}</div>
    <h4>${esc(nameOf(w))} <span lang="${zh() ? "en" : "zh-CN"}">${esc(zh() ? w.name : w.name_zh)}</span></h4>
    <p class="pc-works"><b>${t("wallBy")}</b> ${esc(tx(w, "builder"))} · ${t("wallLen")(w.length_km)}</p>
    <p>${esc(tx(w, "summary"))}</p>${ruin ? `<p class="pc-meta">${t("ruin")}</p>` : ""}
    <p class="pc-meta">${t("drafted")} ${wikiA(w.source)}</p>`;
}
function renderWalls() {
  const list = state.show.walls ? state.walls.filter((w) => state.year >= w.from) : [];
  const feats = [];
  for (const w of list) for (const p of w.paths)
    feats.push({ type: "Feature", properties: { id: w.id, ruin: state.year > w.to }, geometry: { type: "LineString", coordinates: p } });
  map.getSource("walls")?.setData({ type: "FeatureCollection", features: feats });
  (markers.walls || []).forEach((m) => m.remove());
  markers.walls = [];
  for (const w of list.filter((w) => state.year <= w.to)) {
    const el = document.createElement("div");
    el.className = "mk-road mk-wall";
    el.textContent = nameOf(w);
    el.dataset.name = nameOf(w);
    const p = w.paths[0], mid = p[Math.floor(p.length / 2)];
    el.addEventListener("click", (e) => { e.stopPropagation(); showCard(mid, wallCard(w)); });
    markers.walls.push(new maplibregl.Marker({ element: el, anchor: "bottom", offset: [0, -6] }).setLngLat(mid).addTo(map));
  }
}
function renderInventions() {
  cumulative("inventions", state.show.inventions ? state.overlays.inventions : [], "mk-invention", () => "✦", (x) => t("ifields")[x.field] || x.field);
}

// Population: a dot chart in the era card on the same nonlinear scale as the timeline, with the latest figure.
// Dots, not a line: the figures mix censuses of one state, totals and scholars' estimates, so they don't form a series.
function renderPopulation() {
  const box = $("pop-chart");
  const pts = state.overlays.population;
  box.hidden = !state.show.capitals || !pts.length;
  if (box.hidden) return;
  const W = 288, H = 54, max = Math.max(...pts.map((p) => p.millions));
  const sx = (y) => {
    const s = state.scale.find((s) => y >= s.era.start && y <= s.era.end) || state.scale[state.scale.length - 1];
    return ((s.p0 + ((y - s.era.start) / (s.era.end + 1 - s.era.start)) * (s.p1 - s.p0)) / SLIDER_MAX) * W;
  };
  const sy = (m) => H - 4 - (m / max) * (H - 12);
  const last = [...pts].reverse().find((p) => p.year <= state.year);
  const cx = sx(state.year);
  box.innerHTML = `<div class="pop-head"><b>${t("pop")}</b><span>${last ? esc(t("popOf")(last.millions, fmtYear(last.year), last.kind)) + (last.polity_zh && zh() ? " · " + esc(last.polity_zh) : "") : "—"}</span></div>
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${t("pop")}">
      ${pts.map((p) => `<circle class="pop-pt ${esc(p.kind)}${p === last ? " on" : ""}" cx="${sx(p.year).toFixed(1)}" cy="${sy(p.millions).toFixed(1)}" r="${p === last ? 3.5 : 2}"><title>${esc(fmtYear(p.year))} · ${p.millions}${zh() ? "百万" : "M"} ${esc(tx(p, "note"))}</title></circle>`).join("")}
      <line class="pop-now" x1="${cx}" x2="${cx}" y1="0" y2="${H}"/>
    </svg>`;
}

function updateRulers() {
  const focus = [];
  for (const p of markers.polityEls) {
    p.el.querySelector(".ruler")?.remove();
    const r = state.show.rulers && rulerAt(p.name, state.year);
    if (!r) continue;
    if (p.focus) focus.push(r);
    const [title, name] = rulerText(r);
    const span = document.createElement("span");
    span.className = "ruler";
    span.innerHTML = esc(title) + (name ? ` <em>${esc(name)}</em>` : "");
    p.el.appendChild(span);
  }
  // The era card names the ruler when one dynasty holds the map.
  const line = $("era-ruler");
  const single = !markers.polityEls.some((p) => p.focus && p.state) && focus.length === 1 ? focus[0] : null;
  line.hidden = !single;
  if (single) {
    const [title, name] = rulerText(single);
    line.textContent = `${t("ruler")}${title}${name ? (zh() ? " " : " (") + name + (zh() ? "" : ")") : ""} · ${t("reign")(fmtYear(single.from, single.circa).replace(/年$/, ""), fmtYear(single.to).replace(/年$/, ""))}`;
  }
}

function unitsText(units) {
  return (units || []).map((u) => `<span class="unit u-${esc(u)}">${esc(t("units")[u] || u)}</span>`).join("");
}
function sideHTML(sd) {
  const cmd = (sd.commanders || []).map((c) => esc(zh() ? c.name_zh || c.name : c.name)).join(zh() ? "、" : ", ");
  const troops = (zh() ? sd.troops_text_zh || sd.troops_text : sd.troops_text) || (sd.troops ? sd.troops.toLocaleString() : t("unknown"));
  const res = t("result")[sd.result] || "";
  return `<div class="side ${esc(sd.result || "")}">
    <div class="side-head"><b>${esc(zh() ? sd.name_zh || sd.name : sd.name)}</b>${res ? `<span class="res">${res}</span>` : ""}</div>
    ${cmd ? `<div class="cmd">${cmd}</div>` : ""}
    <div class="troops"><span>${t("troops")}</span> ${esc(troops)}</div>
    <div class="units">${unitsText(sd.units)}</div></div>`;
}
// A bar comparing the sides' strength, when every side has a number.
function strengthBar(sides) {
  if (sides.length < 2 || sides.some((s) => !s.troops)) return "";
  return `<div class="strength">${sides.map((s, i) => `<i class="s${i} ${esc(s.result || "")}" style="flex:${s.troops}"></i>`).join("")}</div>`;
}
function armiesHTML(a) {
  const note = zh() ? a.note_zh || a.note : a.note;
  const losses = zh() ? a.losses_zh || a.losses : a.losses;
  return `<div class="sides">${a.sides.map(sideHTML).join("")}</div>${strengthBar(a.sides)}` +
    (losses ? `<p class="army-losses"><span>${t("losses")}</span> ${esc(losses)}</p>` : "") +
    (note ? `<p class="army-note">${esc(note)}</p>` : "");
}

// A marker anchored by its middle or bottom is shifted by -50% / -100% of its own size; when that size has a
// fractional height (line heights like 1.35 x 12px) the card lands between pixels and its text blurs. Round the
// height up to whole pixels once it is laid out.
function crisp(el) {
  requestAnimationFrame(() => {
    el.style.height = "";
    el.style.height = Math.ceil(el.getBoundingClientRect().height) + "px";
  });
}

// Battle cards stand over the war site while the battle is current (or selected); at most three at once.
function renderArmies() {
  markers.armies.forEach((m) => m.remove());
  markers.armies = [];
  const data = state.layerData?.armies;
  if (!state.show.armies || !data || !state.era) return;
  const evs = visibleEvents()
    .filter((ev) => data[ev.id] && ev.year <= state.year && (isActive(ev, state.year) || ev.id === state.selected))
    .sort((a, b) => (b.id === state.selected) - (a.id === state.selected) || b.year - a.year)
    .slice(0, 3);
  for (const ev of evs) {
    const el = document.createElement("div");
    el.className = "mk-army" + (ev.id === state.selected ? " selected" : "");
    el.innerHTML = `<div class="army-title">${esc(titleOf(ev))}<span>${fmtYear(ev.year, ev.circa)}</span></div>` + armiesHTML(data[ev.id]);
    el.addEventListener("click", (e) => { e.stopPropagation(); openStory(ev.id); });
    markers.armies.push(new maplibregl.Marker({ element: el, anchor: "bottom", offset: [0, -16] }).setLngLat([ev.lon, ev.lat]).addTo(map));
    crisp(el);
  }
}

// Campaigns and journeys grow along their path from their first to their last year; the rest show whole.
function partialPath(path, f) {
  if (f >= 1) return path;
  const seg = [];
  let total = 0;
  for (let i = 1; i < path.length; i++) { const d = Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]); seg.push(d); total += d; }
  let left = total * f;
  const out = [path[0]];
  for (let i = 1; i < path.length; i++) {
    if (left >= seg[i - 1]) { out.push(path[i]); left -= seg[i - 1]; continue; }
    const k = left / seg[i - 1];
    out.push([path[i - 1][0] + (path[i][0] - path[i - 1][0]) * k, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * k]);
    break;
  }
  return out;
}
function bearing(a, b) {
  const rad = Math.PI / 180;
  return Math.atan2((b[0] - a[0]) * Math.cos(((a[1] + b[1]) / 2) * rad), b[1] - a[1]) / rad;
}

function renderRoutes() {
  markers.routes.forEach((m) => m.remove());
  markers.routes = [];
  const routes = (state.show.routes && state.layerData?.routes) || [];
  const feats = [];
  for (const r of routes) {
    if (state.year < r.from || state.year > r.to || r.path.length < 2 || r.kind === "wall") continue;
    const moving = r.kind === "campaign" || r.kind === "journey";
    const f = moving && r.to > r.from ? Math.max(0.08, (state.year - r.from + 1) / (r.to - r.from + 1)) : 1;
    const path = moving ? partialPath(r.path, f) : r.path;
    feats.push({ type: "Feature", properties: { kind: r.kind }, geometry: { type: "LineString", coordinates: path } });
    if (moving && path.length > 1) {
      const head = document.createElement("div");
      head.className = "mk-arrow k-" + r.kind;
      markers.routes.push(new maplibregl.Marker({ element: head, rotation: bearing(path[path.length - 2], path[path.length - 1]), rotationAlignment: "map" })
        .setLngLat(path[path.length - 1]).addTo(map));
    }
    const label = document.createElement("div");
    label.className = "mk-route k-" + r.kind;
    label.innerHTML = `<b>${esc(t("kinds")[r.kind] || "")}</b>${esc(nameOf(r))}`;
    label.title = tx(r, "summary");
    if (r.event) label.addEventListener("click", (e) => { e.stopPropagation(); openStory(r.event); });
    else label.classList.add("static");
    const mid = r.path[Math.floor((moving ? 0 : r.path.length / 2))];
    markers.routes.push(new maplibregl.Marker({ element: label, anchor: moving ? "right" : "bottom", offset: moving ? [-8, 0] : [0, -6] })
      .setLngLat(mid).addTo(map));
  }
  map.getSource("routes")?.setData({ type: "FeatureCollection", features: feats });
}

function focusBounds() {
  const gj = state.borders[state.snapshot];
  if (!gj) return null;
  const b = new maplibregl.LngLatBounds();
  const walk = (c) => (typeof c[0] === "number" ? b.extend(c) : c.forEach(walk));
  gj.features.filter((f) => f.properties.focus).forEach((f) => walk(f.geometry.coordinates));
  return b.isEmpty() ? null : b;
}

/* ---------- decluttering ---------- */

// Markers that land on the same spot fold into the most important one, which shows a "+N" badge listing the rest;
// labels that would overlap a more important label hide (hover the icon to see one). Re-run as the map moves,
// so zooming in brings everything back.
const DC_RADIUS = 18;
function dcItems() {
  const out = [];
  const add = (m, kind, prio, opts = {}) => { const el = m.getElement(); if (el.isConnected) out.push({ m, el, kind, prio, ...opts }); };
  for (const m of markers.events.values()) {
    const el = m.getElement();
    add(m, "event", el.classList.contains("active") ? 100 : el.classList.contains("minor") ? 50 : 60);
  }
  (markers.capitals || []).forEach((m) => add(m, "capital", 80));
  (markers.people || []).forEach((m) => add(m, "person", 70));
  (markers.inventions || []).forEach((m) => add(m, "invention", m.getElement().classList.contains("old") ? 30 : 65));
  (markers.passes || []).forEach((m) => add(m, "pass", 62));
  (markers.faith || []).forEach((m) => add(m, "faith", m.getElement().classList.contains("old") ? 29 : 64));
  markers.places.forEach((m) => add(m, "place", m.getElement().classList.contains("capital") ? 75 : m.getElement().classList.contains("r-secondary") ? 48 : m.getElement().classList.contains("r-frontier") ? 63 : 40, { fixed: true }));
  (markers.roads || []).forEach((m) => add(m, "road", 20, { fixed: true, labelOnly: true }));
  (markers.clans || []).forEach((m) => add(m, "clan", 55));
  (markers.walls || []).forEach((m) => add(m, "wall", 22, { fixed: true, labelOnly: true }));
  // Finer landscape names (smaller ranges, basins) only from their zoom on.
  const z = map.getZoom();
  (markers.geo || []).forEach((m) => {
    const el = m.getElement();
    if (el.dataset.minzoom && z < +el.dataset.minzoom) el.classList.add("dc-hide");
    else add(m, "geo", el.dataset.minzoom ? 9 : 10, { fixed: true, labelOnly: true });
  });
  return out.sort((a, b) => b.prio - a.prio);
}
const overlaps = (a, b, pad = 1) => a.left < b.right + pad && b.left < a.right + pad && a.top < b.bottom + pad && b.top < a.bottom + pad;
function declutter() {
  dcTimer = 0;
  document.querySelectorAll(".dc-more").forEach((b) => b.remove());
  document.querySelectorAll(".dc-hide, .dc-nolabel").forEach((el) => el.classList.remove("dc-hide", "dc-nolabel"));
  const items = dcItems();
  // Fold: an item whose icon sits within DC_RADIUS of a kept, more important icon joins that one's group.
  const kept = [];
  for (const it of items) {
    const icon = it.el.querySelector("i") || it.el;
    const r = icon.getBoundingClientRect();
    it.icon = r;
    it.cx = (r.left + r.right) / 2; it.cy = (r.top + r.bottom) / 2;
    if (it.labelOnly || r.width === 0) { kept.push(it); continue; }
    // A city dot under a capital star says the same thing twice.
    if (it.kind === "place" && kept.some((k) => k.kind === "capital" && Math.hypot(k.cx - it.cx, k.cy - it.cy) < DC_RADIUS)) {
      it.el.classList.add("dc-hide"); continue;
    }
    const host = !it.fixed && kept.find((k) => !k.fixed && !k.labelOnly && Math.hypot(k.cx - it.cx, k.cy - it.cy) < DC_RADIUS);
    if (host) { (host.group ||= [host]).push(it); it.el.classList.add("dc-hide"); }
    else kept.push(it);
  }
  // Labels: placed in priority order; battle cards and route labels are already taken space,
  // and the big territory names push away only the landscape names.
  const taken = [...markers.armies, ...markers.routes].map((m) => m.getElement().getBoundingClientRect());
  const polities = markers.polityEls.map((p) => p.el.getBoundingClientRect());
  // A label gives way to labels and icons of more important markers; it may cover a less important icon.
  for (const it of kept) {
    const span = it.labelOnly ? it.el : it.el.querySelector("span");
    const r = span?.getBoundingClientRect();
    if (r?.width) {
      const blocked = taken.some((t) => overlaps(r, t)) || ((it.kind === "geo" || it.kind === "road") && polities.some((t) => overlaps(r, t)));
      if (blocked) it.el.classList.add("dc-nolabel");
      else taken.push(r);
    }
    if (!it.labelOnly && !it.fixed) taken.push(it.icon);
  }
  for (const it of kept) if (it.group) addGroupBadge(it);
}
function addGroupBadge(host) {
  const b = document.createElement("b");
  b.className = "dc-more";
  b.textContent = "+" + (host.group.length - 1);
  b.title = host.group.map((g) => g.el.dataset.name).join(" · ");
  b.addEventListener("click", (e) => {
    e.stopPropagation();
    const kinds = { event: t("events"), capital: t("capitals"), person: t("people_l"), invention: t("inventions"), faith: t("faith"), pass: t("passes") };
    showCard(host.m.getLngLat(), `<div class="pc-kind">${zh() ? `此处 ${host.group.length} 项` : `${host.group.length} here`}</div>
      <ul class="dc-list">${host.group.map((g, i) => `<li><button data-i="${i}"><span class="dc-ico ${esc(g.el.className.replace(/\b(dc|maplibregl)-\S+/g, ""))}">${(g.el.querySelector("i") || {}).outerHTML || ""}</span>
        <span>${esc(g.el.dataset.name || "")}<small>${esc(kinds[g.kind] || "")}</small></span></button></li>`).join("")}</ul>`);
    popup.getElement().querySelectorAll(".dc-list button").forEach((btn) =>
      btn.addEventListener("click", () => host.group[+btn.dataset.i].el.click()));
  });
  host.el.appendChild(b);
}
let dcTimer = 0;
function scheduleDeclutter(delay = 0) {
  if (dcTimer) return;
  dcTimer = delay ? setTimeout(() => requestAnimationFrame(declutter), delay) : requestAnimationFrame(declutter);
}

/* ---------- events ---------- */

// Events on the map and in the list: the current era (zoom all/dynasty) or the window (decades),
// limited to those whose level the zoom reveals.
function visibleEvents() {
  const [a, b] = state.zoom === 2 ? state.win : [state.era.start, state.era.end];
  return state.events.filter((ev) => shownEvent(ev) && ev.year >= a && ev.year <= b);
}
// The detail switch (大事 / 要事 / 细目) sets the finest level shown; tags narrow to some categories.
// The open event always stays visible.
function shownEvent(ev) {
  if (ev.id === state.selected) return true;
  // The country filter belongs to one period; events of other periods ignore it.
  const c = state.country;
  if (c && ev.year >= c.start && ev.year <= c.end && !(ev.states || []).includes(c.key)) return false;
  return (ev.level || 1) <= state.detail && (!state.cats.length || state.cats.includes(ev.category));
}
// Countries of this period that have events (from each event's `states`), main dynasties first, then by event count.
function eventCountries() {
  const pol = state.layerData?.polities || {}, n = new Map();
  for (const ev of state.events) if (ev.year >= state.era.start && ev.year <= state.era.end)
    for (const k of ev.states || []) n.set(k, (n.get(k) || 0) + 1);
  return [...n].filter(([k]) => pol[k]).sort((a, b) => (pol[b[0]].focus - pol[a[0]].focus) || b[1] - a[1])
    .map(([k, count]) => ({ key: k, count, name: zh() ? pol[k].name_zh || k : k }));
}
const CATS = ["war", "politics", "reform", "rebellion", "diplomacy", "economy", "culture", "science", "society"];
function renderEventFilter() {
  const box = $("ev-filter");
  box.hidden = false;
  const cur = state.country && state.country.start === state.era.start ? state.country.key : "";
  const key = `${state.detail}|${state.cats.join()}|${state.lang}|${state.era.id}|${cur}|${state.layerData ? 1 : 0}`;
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  const cs = eventCountries();
  box.innerHTML = (cs.length > 1 ? `<label class="ef-country"><span>${t("country")}</span><select id="ef-country"><option value="">${t("allCats")}</option>${cs.map((c) =>
      `<option value="${esc(c.key)}" ${c.key === cur ? "selected" : ""}>${esc(c.name)}${zh() ? `（${c.count}）` : ` (${c.count})`}</option>`).join("")}</select></label>` : "") +
    `<div class="ef-levels" role="group" aria-label="${t("detail")}">${t("levels").map((l, i) =>
      `<button data-lv="${i + 1}" aria-pressed="${state.detail === i + 1}">${l}</button>`).join("")}</div>
    <div class="ef-cats"><button class="chip" data-cat="" aria-pressed="${!state.cats.length}">${t("allCats")}</button>${CATS.map((c) =>
      `<button class="chip cat-${c}" data-cat="${c}" aria-pressed="${state.cats.includes(c)}">${t("cat")[c]}</button>`).join("")}</div>`;
  box.querySelectorAll("[data-lv]").forEach((b) => b.addEventListener("click", () => setEventFilter(+b.dataset.lv, state.cats)));
  $("ef-country")?.addEventListener("change", (e) => {
    state.country = e.target.value ? { key: e.target.value, start: state.era.start, end: state.era.end } : null;
    setEventFilter(state.detail, state.cats);
  });
  box.querySelectorAll("[data-cat]").forEach((b) => b.addEventListener("click", () => {
    const c = b.dataset.cat;
    setEventFilter(state.detail, !c ? [] : state.cats.includes(c) ? state.cats.filter((x) => x !== c) : [...state.cats, c]);
  }));
}
function setEventFilter(detail, cats) {
  state.detail = detail;
  state.cats = cats;
  try { localStorage.setItem("atlas-events", JSON.stringify({ detail, cats })); } catch {}
  buildEventMarkers();
  refreshTimeline();
  renderLedger();
}

function buildEventMarkers() {
  markers.events.forEach((m) => m.remove());
  markers.events.clear();
  if (!state.era) return;
  for (const ev of visibleEvents()) {
    const el = document.createElement("div");
    el.className = "mk-event" + ((ev.level || 1) > 1 ? " minor" : "");
    el.appendChild(document.createElement("i"));
    el.title = `${fmtYear(ev.year, ev.circa)} · ${titleOf(ev)}`;
    el.dataset.name = `${fmtYear(ev.year, ev.circa)} ${titleOf(ev)}`;
    el.addEventListener("click", (e) => { e.stopPropagation(); openStory(ev.id); });
    markers.events.set(ev.id, new maplibregl.Marker({ element: el }).setLngLat([ev.lon, ev.lat]));
  }
}

// An event stays "active" through its end year, or for a short window scaled to the visible span.
function isActive(ev, y) {
  const len = state.zoom === 2 ? state.win[1] - state.win[0] : state.era.end - state.era.start;
  const span = Math.max(state.zoom === 2 ? 1 : 2, Math.round(len / 60));
  return y >= ev.year && y <= (ev.endYear ?? ev.year + span);
}

function renderEventStates() {
  scheduleDeclutter();
  for (const [id, m] of markers.events) {
    const ev = state.events.find((x) => x.id === id);
    const happened = ev.year <= state.year;
    // Only events current at this year (and the one opened) stay on the map; the list keeps the rest.
    if (isActive(ev, state.year) || id === state.selected) m.addTo(map); else m.remove();
    const el = m.getElement();
    const active = isActive(ev, state.year) || ev.id === state.selected;
    el.classList.toggle("active", active);
    el.classList.toggle("past", happened && !active);
  }
  document.querySelectorAll(".ev").forEach((btn) => {
    const ev = state.events.find((x) => x.id === btn.dataset.id);
    btn.classList.toggle("future", ev.year > state.year);
  });
}

// Names of rivers, mountains, plains and seas; they don't change with the year.
function renderGeo() {
  scheduleDeclutter();
  (markers.geo || []).forEach((m) => m.remove());
  markers.geo = [];
  if (!state.showGeo) return;
  for (const f of state.geo) {
    const el = document.createElement("div");
    el.className = "mk-geo g-" + f.kind + (f.vertical && zh() ? " vertical" : "") + (f.minzoom ? " detail" : "");
    // Upright names: one character per line.
    if (f.vertical && zh()) el.innerHTML = [...nameOf(f)].map(esc).join("<br>");
    else el.textContent = nameOf(f);
    if (f.minzoom) el.dataset.minzoom = f.minzoom;
    markers.geo.push(new maplibregl.Marker({ element: el }).setLngLat([f.lon, f.lat]).addTo(map));
  }
}

// City card: its role and name in this period, the years it held them and today's name.
function placeCard(p) {
  const modern = zh() ? p.modern_zh || p.modern : p.modern;
  const now = modern && modern !== (zh() ? p.name_zh : p.name) ? (zh() ? `今${modern}` : `modern ${modern}`) : "";
  return `<div class="pc-kind">${esc(t("pranks")[p.rank] || "")} · ${fmtYear(p.from, true)} – ${p.to >= 1912 ? (zh() ? "清末" : "1912") : fmtYear(p.to, true)}</div>
    <h4>${esc(nameOf(p))} <span lang="${zh() ? "en" : "zh-CN"}">${esc(zh() ? p.name : p.name_zh)}</span></h4>
    ${now ? `<p class="pc-meta">${esc(now)}</p>` : ""}${tx(p, "note") ? `<p>${esc(tx(p, "note"))}</p>` : ""}
    ${placeEventList(p)}<p class="pc-meta">${t("drafted")}</p>`;
}
// Reverse index from each event's `places` (city ids) and `people` (person ids), filled by tools/link_events.py,
// so city and person cards list their events as soon as new events carry those fields.
const cityId = (p) => p.id.replace(/-\d+$/, "");
function eventIndex(field) {
  const key = "_idx_" + field;
  if (!state[key]) {
    state[key] = new Map();
    for (const ev of state.events) for (const k of ev[field] || []) {
      if (!state[key].has(k)) state[key].set(k, []);
      state[key].get(k).push(ev);
    }
  }
  return state[key];
}
const cityEvents = (p) => eventIndex("places").get(cityId(p)) || [];
const personEvents = (p) => eventIndex("people").get(p.id) || [];
function eventButtons(evs, now) {
  return `<ul class="pc-battles pc-events">${evs.map((ev) =>
    `<li><button type="button" data-ev="${esc(ev.id)}" class="${now(ev) ? "now" : ""}${ev.id === state.selected ? " sel" : ""}"><span>${fmtYear(ev.year)}</span> ${esc(zh() ? ev.title_zh || ev.title : ev.title)}</button></li>`).join("")}</ul>`;
}
// A capital marker lists the events of the city at the same spot (within ~35 km).
function capitalEvents(c) {
  const near = state.places.filter((p) => Math.hypot(p.lon - c.lon, p.lat - c.lat) < 0.35)
    .sort((a, b) => Math.hypot(a.lon - c.lon, a.lat - c.lat) - Math.hypot(b.lon - c.lon, b.lat - c.lat));
  const p = near.find((p) => c.from <= p.to && c.to >= p.from) || near[0];
  return p ? placeEventList({ ...p, from: c.from, to: c.to }) : "";
}
function placeEventList(p) {
  const evs = cityEvents(p);
  if (!evs.length) return "";
  return `<p class="pc-works"><b>${t("cityEvents")(evs.length)}</b></p>${eventButtons(evs, (ev) => ev.year >= p.from && ev.year <= p.to)}`;
}
function renderPlaces() {
  scheduleDeclutter();
  markers.places.forEach((m) => m.remove());
  markers.places = [];
  if (!state.showPlaces) return;
  for (const p of state.places) {
    if (state.year < p.from || state.year > p.to) continue;
    const el = document.createElement("div");
    el.className = "mk-place r-" + p.rank + (p.rank === "capital" ? " capital" : "");
    el.innerHTML = zh() ? `<i></i><span>${esc(p.name_zh)}</span>` : `<i></i><span>${esc(p.name)} <em>${esc(p.name_zh)}</em></span>`;
    el.title = zh() ? `${p.name_zh}（今${p.modern_zh || p.modern}）` : `${p.name} (modern ${p.modern})`;
    el.addEventListener("click", (e) => { e.stopPropagation(); showCard([p.lon, p.lat], placeCard(p)); });
    markers.places.push(new maplibregl.Marker({ element: el, anchor: "left", offset: [-4, 0] }).setLngLat([p.lon, p.lat]).addTo(map));
  }
}

/* ---------- ledger: event list and story view ---------- */

function renderLedger() {
  if (!state.era) return;
  $("ev-filter").hidden = true;
  if (state.reading && state.selected) state.tab = "events";
  for (const k of ["events", "rulers", "people"]) $("tab-" + k).setAttribute("aria-selected", String(state.tab === k));
  $("rulers").hidden = state.tab !== "rulers";
  $("people").hidden = state.tab !== "people";
  if (state.tab !== "events") {
    $("story").hidden = $("ev-list").hidden = true;
    return state.tab === "rulers" ? renderRulers() : renderPeopleTab();
  }
  if (state.reading && state.selected) return renderStory();
  $("story").hidden = true;
  $("ev-list").hidden = false;
  renderList();
}

/* ---------- ledger: rulers of one country; picking one narrows the timeline to the reign ---------- */

function rulerPolities() {
  const L = state.layerData;
  if (!L?.rulers) return [];
  const pol = L.polities || {};
  return Object.keys(L.rulers).filter((n) => L.rulers[n].length)
    .map((n, i) => ({ n, i, focus: !!pol[n]?.focus, zh: pol[n]?.name_zh || "" }))
    .sort((a, b) => b.focus - a.focus || a.i - b.i);
}
function renderRulers() {
  const box = $("rulers");
  const ps = rulerPolities();
  if (!ps.length) {
    box.innerHTML = `<p class="rl-empty">${t("noRulers")}</p>`;
    box.dataset.key = "";
    $("ev-count").textContent = "";
    return;
  }
  if (!ps.some((p) => p.n === state.rulerPolity)) {
    // Default: the main country ruling this year, as in the Five Dynasties the dynasty of the moment.
    state.rulerPolity = (ps.find((p) => p.focus && rulerAt(p.n, state.year)) || ps.find((p) => rulerAt(p.n, state.year)) || ps[0]).n;
  }
  const reigns = state.layerData.rulers[state.rulerPolity];
  $("ev-count").textContent = t("rulerCount")(reigns.length);
  const key = `${state.era.id}|${state.rulerPolity}|${state.lang}`;
  if (box.dataset.key !== key || box._data !== state.layerData) {
    box.dataset.key = key;
    box._data = state.layerData;
    const label = (p) => (zh() ? p.zh || p.n : p.n + (p.zh ? ` · ${p.zh}` : ""));
    box.innerHTML = `<label class="rl-pick"><span>${t("country")}</span><select id="rl-select">${ps.map((p) =>
        `<option value="${esc(p.n)}"${p.n === state.rulerPolity ? " selected" : ""}>${esc(label(p))}</option>`).join("")}</select></label>
      <p class="rl-hint">${t("scopeHint")}</p>
      <ol class="rl-list">${reigns.map((r, i) => {
        const [a, b] = rulerText(r);
        return `<li><button class="rl" data-i="${i}"><span class="rl-years">${fmtYear(r.from, r.circa)}<br>${fmtYear(r.to)}</span>
          <span class="rl-name">${esc(a)}</span>${b ? `<span class="rl-sub">${esc(b)}</span>` : ""}<span class="rl-len">${t("reignLen")(r.to - r.from + 1)}</span></button></li>`;
      }).join("")}</ol>`;
    $("rl-select").addEventListener("change", (e) => { state.rulerPolity = e.target.value; renderRulers(); });
    box.querySelectorAll(".rl").forEach((btn) => btn.addEventListener("click", () => scopeToRuler(state.rulerPolity, +btn.dataset.i)));
    box.dataset.current = "";
  }
  // Mark the reigning ruler and the one the timeline is narrowed to; follow the reigning one as the year moves.
  const cur = reigns.indexOf(rulerAt(state.rulerPolity, state.year));
  box.querySelectorAll(".rl").forEach((btn) => {
    const r = reigns[+btn.dataset.i];
    btn.classList.toggle("current", +btn.dataset.i === cur);
    btn.classList.toggle("future", r.from > state.year);
    btn.classList.toggle("scoped", state.scope?.polity === state.rulerPolity && state.scope.i === +btn.dataset.i);
  });
  if (String(cur) !== box.dataset.current) {
    box.dataset.current = String(cur);
    box.querySelector(".rl.current")?.scrollIntoView({ block: "nearest" });
  }
}
/* ---------- ledger: famous people of the period; picking one flies to where they lived and opens their card ---------- */

const PGROUP = { general: "mil", statesman: "pol", thinker: "cul", poet: "cul", writer: "cul", historian: "cul", scholar: "cul", religious: "cul",
  artist: "art", scientist: "sci", physician: "sci", engineer: "sci", explorer: "sci" };
function renderPeopleTab() {
  const box = $("people");
  const all = [...(state.layerData?.people || [])].sort((a, b) => personSpan(a)[0] - personSpan(b)[0]);
  const g = state.peopleGroup || "all";
  const list = g === "all" ? all : all.filter((p) => PGROUP[p.field] === g);
  $("ev-count").textContent = all.length ? t("rulerCount")(list.length) : "";
  if (!all.length) { box.innerHTML = `<p class="rl-empty">${t("noPeople")}</p>`; box.dataset.key = ""; return; }
  const key = `${state.era.id}|${state.lang}|${g}`;
  if (box.dataset.key !== key || box._data !== state.layerData) {
    box.dataset.key = key;
    box._data = state.layerData;
    box._list = list;
    const groups = ["all", ...["mil", "pol", "cul", "art", "sci"].filter((k) => all.some((p) => PGROUP[p.field] === k))];
    box.innerHTML = `<div class="pp-groups">${groups.map((k) =>
        `<button class="chip" data-g="${k}" aria-pressed="${k === g}">${t("pgroups")[k]}</button>`).join("")}</div>
      <p class="rl-hint">${t("peopleHint")}</p><ol class="rl-list">${list.map((p, i) =>
      `<li><button class="rl pp f-${esc(p.field)}" data-i="${i}"><span class="rl-years">${p.born != null ? fmtYear(p.born, p.circa) : "?"}<br>${p.died != null ? fmtYear(p.died, p.circa) : "?"}</span>
        <span class="rl-name">${esc(nameOf(p))}</span><span class="rl-sub">${esc(tx(p, "known_for"))}</span><span class="rl-len">${esc(t("fields")[p.field] || "")}</span></button></li>`).join("")}</ol>`;
    box.querySelectorAll(".rl").forEach((btn) => btn.addEventListener("click", () => focusPerson(box._list[+btn.dataset.i])));
    box.querySelectorAll("[data-g]").forEach((btn) => btn.addEventListener("click", () => { state.peopleGroup = btn.dataset.g; renderPeopleTab(); }));
    box._fresh = true;
  }
  // Alive this year in normal colour, not yet born dimmed.
  box.querySelectorAll(".rl").forEach((btn) => {
    const [a, b] = personSpan(box._list[+btn.dataset.i]);
    btn.classList.toggle("current", state.year >= a && state.year <= b);
    btn.classList.toggle("future", a > state.year);
  });
  // A new list opens at the people alive this year.
  if (box._fresh) { box._fresh = false; const cur = box.querySelector(".rl.current"); if (cur) box.scrollTop = cur.parentElement.offsetTop - box.querySelector(".rl-list").offsetTop; }
}
async function focusPerson(p) {
  stop();
  // Move the year into their lifetime (nearest year to now, kept inside this period) so their marker shows.
  const [a, b] = personSpan(p);
  const y = Math.min(state.era.end, Math.max(state.era.start, Math.min(b, Math.max(a, state.year))));
  if (y !== state.year) {
    if (state.zoom && (y < state.win[0] || y > state.win[1])) { state.scope = null; state.win = windowFor(state.zoom, y); refreshTimeline(); }
    await setYear(y);
  }
  map.flyTo({ center: [p.lon, p.lat], zoom: Math.min(Math.max(map.getZoom(), 5), 6), pitch: state.show3d ? 45 : 0, duration: 1400, essential: true });
  map.once("moveend", () => showCard([p.lon, p.lat], personCard(p)));
}
async function scopeToRuler(polity, i) {
  stop();
  const r = state.layerData.rulers[polity][i];
  const a = Math.max(state.range.start, r.from), b = Math.min(state.range.end, Math.max(r.from, r.to));
  state.zoom = 2;
  state.win = [a, b];
  state.selected = null;
  state.reading = false;
  await setYear(Math.min(b, Math.max(a, state.era.start)));
  state.scope = { polity, i, label: rulerText(r)[0] };
  refreshTimeline();
}

function renderList() {
  renderEventFilter();
  const list = $("ev-list");
  const evs = visibleEvents();
  $("ev-count").textContent = state.zoom === 2 ? t("countWin")(evs.length) : t("count")(evs.length, nameOf(state.era));
  list.innerHTML = "";
  for (const ev of evs) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.className = "ev" + (ev.year > state.year ? " future" : "") + (ev.id === state.selected ? " selected" : "") + ((ev.level || 1) > 1 ? " minor" : "");
    btn.dataset.id = ev.id;
    btn.innerHTML = `<span class="ev-year">${fmtYear(ev.year, ev.circa)}</span><span class="ev-title">${esc(titleOf(ev))}</span>` +
      `<span class="ev-sub" lang="${zh() ? "en" : "zh-CN"}">${esc(zh() ? ev.title : ev.title_zh)}</span>`;
    if (ev.id === state.selected) {
      const d = document.createElement("div");
      d.className = "ev-detail";
      d.innerHTML = `<p>${esc(tx(ev, "summary"))}</p><span class="ev-more">${t("more")}</span>`;
      btn.appendChild(d);
    }
    btn.addEventListener("click", () => openStory(ev.id));
    li.appendChild(btn);
    list.appendChild(li);
  }
  list.querySelector(".selected")?.scrollIntoView({ block: "nearest" });
}

function loadDetails(era) {
  if (!state.details[era.id]) state.details[era.id] = loadJSON(`data/details/${era.id}.json`).catch(() => ({}));
  return state.details[era.id];
}

async function openStory(id) {
  state.reading = true;
  state.tab = "events";
  $("ledger").classList.remove("collapsed");
  $("ledger-toggle").textContent = t("hide");
  await selectEvent(id);
}

async function renderStory() {
  const ev = state.events.find((e) => e.id === state.selected);
  const box = $("story");
  $("ev-list").hidden = true;
  box.hidden = false;
  const evs = visibleEvents();
  const i = evs.findIndex((e) => e.id === ev.id);
  const prev = evs[i - 1], next = evs[i + 1];
  const when = ev.endYear ? `${fmtYear(ev.year, ev.circa)} – ${fmtYear(ev.endYear)}` : fmtYear(ev.year, ev.circa);
  const cat = t("cat")[ev.category] || ev.category;
  $("ev-count").textContent = i >= 0 ? `${i + 1} / ${evs.length}` : "";
  box.innerHTML = `
    <nav class="story-nav">
      <button class="chip" data-go="back">← ${t("back")}</button>
      <span class="story-step">
        <button class="zbtn" data-go="prev" ${prev ? "" : "disabled"} aria-label="${t("prev")}" title="${prev ? esc(titleOf(prev)) : ""}">‹</button>
        <button class="zbtn" data-go="next" ${next ? "" : "disabled"} aria-label="${t("next")}" title="${next ? esc(titleOf(next)) : ""}">›</button>
      </span>
    </nav>
    <header class="story-head">
      <div class="story-meta"><span class="cat cat-${esc(ev.category)}">${esc(cat)}</span><span class="when">${when}</span></div>
      <h3>${esc(titleOf(ev))}</h3>
      <div class="story-sub" lang="${zh() ? "en" : "zh-CN"}">${esc(zh() ? ev.title : ev.title_zh)}</div>
      <button class="story-place" data-go="map"><i></i>${esc(tx(ev, "place"))}</button>
    </header>
    <p class="story-lede">${esc(tx(ev, "summary"))}</p>
    <div class="story-body"><p class="muted">${t("loading")}</p></div>`;
  box.scrollTop = 0;
  box.onclick = (e) => {
    const go = e.target.closest("[data-go]")?.dataset.go;
    if (go === "back") { state.reading = false; renderLedger(); }
    if (go === "prev" && prev) openStory(prev.id);
    if (go === "next" && next) openStory(next.id);
    if (go === "map") flyToEvent(ev);
    const link = e.target.closest("[data-link]");
    if (link) {
      const it = linkTags.items[+link.dataset.link];
      if (it.field) focusPerson(it);
      else { map.flyTo({ center: [it.lon, it.lat], zoom: Math.max(map.getZoom(), 5), duration: 1200, essential: true }); map.once("moveend", () => showCard([it.lon, it.lat], placeCard(it))); }
    }
  };
  const all = await loadDetails(eraFor(ev.year));
  if (state.selected !== ev.id || !state.reading) return;
  const d = all[ev.id];
  const body = box.querySelector(".story-body");
  const layer = await loadLayers(eraFor(ev.year));
  if (state.selected !== ev.id || !state.reading) return;
  const tags = linkTags(ev, layer);
  if (!d) { body.innerHTML = tags + `<p class="muted">${t("noStory")}</p>` + links(ev, d); return; }
  const story = (zh() ? d.story_zh : d.story) || d.story || [];
  let html = story.map((p) => `<p>${esc(p)}</p>`).join("");
  if (d.quote?.zh) {
    html += `<blockquote><p class="q-zh" lang="zh-CN">${esc(d.quote.zh)}</p>` +
      (!zh() && d.quote.en ? `<p class="q-en">${esc(d.quote.en)}</p>` : "") +
      (d.quote.from ? `<cite>${esc(d.quote.from)}</cite>` : "") + `</blockquote>`;
  }
  const army = layer.armies?.[ev.id];
  if (army) html += `<section class="forces"><h4>${t("forces")}</h4>${armiesHTML(army)}</section>`;
  const why = zh() ? d.why_zh || d.why : d.why;
  if (why) html += `<section class="why"><h4>${t("why")}</h4><p>${esc(why)}</p></section>`;
  if (d.people?.length) {
    html += `<section class="people"><h4>${t("people")}</h4><ul>` + d.people.map((p) =>
      `<li><b>${esc(zh() ? p.name_zh || p.name : p.name)}</b>` +
      `<span>${esc(zh() ? p.role_zh || p.role : p.role)}${!zh() && p.name_zh ? ` · <span lang="zh-CN">${esc(p.name_zh)}</span>` : ""}</span></li>`).join("") +
      `</ul></section>`;
  }
  body.innerHTML = tags + html + links(ev, d);
}
// The event's linked city and people (ev.places / ev.people) as chips that open their cards with all their events.
function linkTags(ev, layer) {
  const people = (ev.people || []).map((id) => (layer.people || []).find((p) => p.id === id)).filter(Boolean);
  const cities = (ev.places || []).map((id) => {
    const all = state.places.filter((p) => cityId(p) === id);
    return all.find((p) => ev.year >= p.from && ev.year <= p.to) || all[0];
  }).filter(Boolean);
  if (!people.length && !cities.length) return "";
  linkTags.items = [...cities, ...people];
  return `<p class="story-tags">${cities.map((p, i) => `<button class="chip tag-city" data-link="${i}">◆ ${esc(nameOf(p))}</button>`).join("")}` +
    people.map((p, i) => `<button class="chip tag-person" data-link="${cities.length + i}">${esc(nameOf(p))}</button>`).join("") + `</p>`;
}

// Wikipedia's search jumps straight to the article when the title exists and falls back to
// search results when it doesn't, so a slightly wrong title still lands somewhere useful.
function wikiLink(url) {
  const m = url && url.match(/^https:\/\/(\w+)\.wikipedia\.org\/wiki\/(.+)$/);
  if (!m) return url;
  const title = decodeURIComponent(m[2]).replace(/_/g, " ");
  return `https://${m[1]}.wikipedia.org/w/index.php?search=${encodeURIComponent(title)}`;
}

function links(ev, d) {
  const zhUrl = wikiLink(d?.source_zh), enUrl = wikiLink(ev.source);
  const main = zh() ? zhUrl || enUrl : enUrl || zhUrl;
  if (!main) return "";
  const other = zhUrl && enUrl ? (zh() ? enUrl : zhUrl) : null;
  return `<p class="story-links"><a href="${esc(main)}" target="_blank" rel="noopener">${t("wiki")} ↗</a>` +
    (other ? `<a href="${esc(other)}" target="_blank" rel="noopener">${t("wikiOther")} ↗</a>` : "") + `</p>`;
}

function flyToEvent(ev) {
  map.flyTo({ center: [ev.lon, ev.lat], zoom: Math.min(Math.max(map.getZoom(), 4.6), 5.5), pitch: state.show3d ? 50 : 0, duration: 1600, essential: true });
}

async function selectEvent(id) {
  stop();
  const ev = state.events.find((e) => e.id === id);
  state.selected = id;
  // An event outside the decades window: move the window to it.
  if (state.zoom === 2 && (ev.year < state.win[0] || ev.year > state.win[1])) {
    state.scope = null;
    state.win = windowFor(state.zoom, ev.year);
    refreshTimeline();
  }
  await setYear(ev.year);
  renderArmies();
  renderLedger();
  flyToEvent(ev);
}

async function goToEra(era) {
  stop();
  state.selected = null;
  state.reading = false;
  state.scope = null;
  if (state.zoom) state.win = windowFor(state.zoom, era.start);
  await setYear(era.start);
  refreshTimeline();
  const b = focusBounds();
  if (b) {
    const cam = map.cameraForBounds(b, { padding: { top: 120, bottom: 140, left: 60, right: innerWidth > 720 ? 380 : 60 } });
    if (cam) map.flyTo({ ...cam, zoom: Math.min(cam.zoom, 5), pitch: state.show3d ? 45 : 0, bearing: -6, duration: 1600, essential: true });
  }
}

/* ---------- timeline rail ---------- */

// Floating tag over the rail while dragging: the period (and map snapshot when zoomed in) and the year.
function showScrubTag(p, y) {
  let tag = $("scrub-tag");
  if (!tag) { tag = document.createElement("div"); tag.id = "scrub-tag"; tag.className = "scrub-tag"; document.querySelector(".track").appendChild(tag); }
  const era = eraFor(y);
  const snap = state.zoom ? [...era.snapshots].reverse().find((s) => s.from <= y) : null;
  tag.innerHTML = `<b>${esc(nameOf(era))}</b> <span>${fmtYear(y)}</span>` + (snap && tx(snap, "label") ? `<small>${esc(tx(snap, "label"))}</small>` : "");
  tag.hidden = false;
  tag.style.left = `clamp(56px, ${(p / SLIDER_MAX) * 100}%, calc(100% - 56px))`;
  document.querySelectorAll(".band.era-band").forEach((b) => b.classList.toggle("scrub", b.dataset.era === era.id));
}
function hideScrubTag() {
  const tag = $("scrub-tag");
  if (tag) tag.hidden = true;
  document.querySelectorAll(".band.scrub").forEach((b) => b.classList.remove("scrub"));
}

function hintText() {
  const h = t("hint")[state.zoom];
  return typeof h === "function" ? h(state.era ? nameOf(state.era) : "") : h;
}

// Era labels sit centred on their band and may spill past it. They are placed current era first, then widest band
// first, skipping any that would overlap one already placed; dragging the rail names the rest.
// Landmark periods named first when space is short (the classic 夏商周 秦汉 唐宋元明清 sequence).
const LANDMARKS = ["tang", "western-han", "ming", "qing", "qin", "northern-song", "yuan", "shang", "western-zhou", "xia", "spring-autumn", "warring-states"];
const rank = (b) => { const i = LANDMARKS.indexOf(b.dataset.era); return i < 0 ? 99 : i; };
function fitBandLabels() {
  const bands = [...document.querySelectorAll("#bands .band")];
  bands.forEach((b) => b.classList.remove("tight"));
  const era = bands.filter((b) => b.classList.contains("era-band"));
  for (const b of bands) if (!era.includes(b)) b.classList.toggle("tight", b.scrollWidth > b.clientWidth + 1);
  if (!era.length) return;
  const track = $("bands").getBoundingClientRect();
  const items = era.map((b) => {
    const r = b.getBoundingClientRect(), w = b.firstElementChild.getBoundingClientRect().width;
    return { b, c: r.left + r.width / 2, w, span: r.width, cur: b.classList.contains("current") };
  }).sort((x, y) => (y.cur - x.cur) || (rank(x.b) - rank(y.b)) || (y.span - x.span));
  // Phones keep wide gaps between names so the rail reads as a few landmarks.
  const gap = innerWidth <= 720 ? 7 : 3, placed = [];
  for (const it of items) {
    const a = it.c - it.w / 2 - gap, z = it.c + it.w / 2 + gap;
    const inside = it.c - it.w / 2 >= track.left - 4 && it.c + it.w / 2 <= track.right + 4;
    const fits = inside && (gap < 5 || it.cur || rank(it.b) < 99) && placed.every(([p, q]) => z <= p || a >= q);
    if (fits) placed.push([a, z]);
    it.b.classList.toggle("tight", !fits);
  }
}
function buildRail() {
  requestAnimationFrame(fitBandLabels);
  const pct = (p) => (p / SLIDER_MAX) * 100;
  const bands = $("bands");
  bands.innerHTML = "";
  if (state.zoom === 0) {
    for (const s of state.scale) {
      const e = s.era;
      const b = document.createElement("button");
      b.className = "band era-band" + (e === state.era ? " current" : "");
      b.dataset.era = e.id;
      b.style.left = pct(s.p0) + "%";
      b.style.width = pct(s.p1 - s.p0) + "%";
      b.innerHTML = `<b>${e.glyph}</b>`;
      b.title = `${nameOf(e)} ${fmtYear(e.start)} – ${fmtYear(e.end)}`;
      b.addEventListener("click", () => goToEra(e));
      bands.appendChild(b);
    }
  } else {
    // Zoomed in: one segment per border snapshot, so each change of the map is one click away.
    const [a, z] = state.win;
    for (const e of state.eras) {
      if (e.end < a || e.start > z) continue;
      e.snapshots.forEach((s, i) => {
        const from = Math.max(s.from, a), to = Math.min((e.snapshots[i + 1]?.from ?? e.end + 1) - 1, z);
        if (to < from) return;
        const b = document.createElement("button");
        b.className = "band snap" + (i === 0 && s.from >= a ? " era-start" : "");
        b.dataset.path = s.borders;
        b.dataset.from = s.from;
        b.style.left = pct(yearToPos(from)) + "%";
        b.style.width = pct(yearToPos(to + 1) - yearToPos(from)) + "%";
        b.innerHTML = (i === 0 && s.from >= a ? `<b>${e.glyph}</b> ` : "") + `<span>${s.from >= a ? "" : "← "}${fmtYear(s.from)}</span>`;
        b.title = tx(s, "label") || `${nameOf(e)} ${fmtYear(e.start)} – ${fmtYear(e.end)}`;
        b.addEventListener("click", () => { stop(); setYear(from); });
        bands.appendChild(b);
      });
    }
  }
  const ticks = $("ticks");
  ticks.innerHTML = "";
  for (const ev of state.events) {
    if (!shownEvent(ev) || !inWindow(ev.year)) continue;
    const tk = document.createElement("button");
    tk.className = "tick l" + (ev.level || 1);
    tk.style.left = pct(state.zoom ? (yearToPos(ev.year) + yearToPos(ev.year + 1)) / 2 : yearToPos(ev.year)) + "%";
    tk.title = `${fmtYear(ev.year, ev.circa)} · ${titleOf(ev)}`;
    tk.tabIndex = -1;
    tk.addEventListener("click", () => openStory(ev.id));
    ticks.appendChild(tk);
  }
  const [a, b] = state.zoom ? state.win : [state.range.start, state.range.end];
  $("scale-start").textContent = fmtYear(a);
  $("scale-end").textContent = fmtYear(b);
  $("scale-hint").textContent = hintText();
  $("zoom-level").textContent = state.scope ? state.scope.label : t("zooms")[state.zoom];
  $("zoom-level").classList.toggle("scoped", !!state.scope);
  $("zoom-in").disabled = state.zoom === ZOOMS.length - 1;
  $("zoom-out").disabled = state.zoom === 0;
  $("pan-prev").hidden = $("pan-next").hidden = state.zoom === 0;
  $("pan-prev").disabled = !!state.zoom && state.win[0] <= state.range.start;
  $("pan-next").disabled = !!state.zoom && state.win[1] >= state.range.end;
  $("app").dataset.zoom = ZOOMS[state.zoom];
}

// Playback moves through each era (or the zoomed window) in roughly the same time.
function play() {
  if (state.playing) return stop();
  if (state.year >= state.range.end) setYear(state.range.start);
  state.selected = null;
  state.reading = false;
  $("play-icon").innerHTML = '<path d="M3 2h4v12H3zM9 2h4v12H9z"/>';
  $("play").setAttribute("aria-label", t("pause"));
  state.playing = setInterval(() => {
    if (state.year >= state.range.end) return stop();
    const era = state.era;
    const len = state.zoom === 2 ? state.win[1] - state.win[0] + 1 : era.end - era.start + 1;
    const step = Math.max(1, Math.round(len / 50));
    let next = Math.min(state.year + step, state.range.end);
    if (next > era.end && era.end >= state.year) next = era.end + 1; // land on the next era's first year
    const hit = state.events.filter((e) => shownEvent(e) && e.year > state.year && e.year <= next).pop();
    if (hit) state.selected = hit.id;
    setYear(next).then(() => { if (hit) renderLedger(); });
  }, state.zoom === 2 ? 450 : 260);
}
function stop() {
  clearInterval(state.playing);
  state.playing = null;
  $("play-icon").innerHTML = '<path d="M4 2l10 6-10 6z"/>';
  $("play").setAttribute("aria-label", t("play"));
}

function toggle(btnId, key, fn) {
  $(btnId).setAttribute("aria-pressed", String(state[key]));
  $(btnId).addEventListener("click", () => {
    state[key] = !state[key];
    $(btnId).setAttribute("aria-pressed", String(state[key]));
    fn();
  });
}

async function init() {
  try { state.lang = localStorage.getItem("atlas-lang") === "en" ? "en" : "zh"; } catch {}
  try { const f = JSON.parse(localStorage.getItem("atlas-events") || "null"); if (f) { state.detail = f.detail || 2; state.cats = f.cats || []; } } catch {}
  try { state.showSat = localStorage.getItem("atlas-look") !== "relief"; } catch {}
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "en" || q === "zh") state.lang = q;
  applyLang();
  const [eras, events, places] = await Promise.all([
    loadJSON("data/eras.json"), loadJSON("data/events.json"), loadJSON("data/places.json"),
  ]);
  state.overlays = await loadJSON("data/overlays.json").catch(() => state.overlays);
  state.passes = await loadJSON("data/passes.json").catch(() => []);
  state.roads = await loadJSON("data/roads.json").catch(() => []);
  state.clans = await loadJSON("data/clans.json").catch(() => []);
  state.walls = await loadJSON("data/walls.json").catch(() => []);
  state.geo = await loadJSON("data/geo/features.json").catch(() => []);
  state.eras = eras.eras;
  state.range = eras.range;
  state.events = events.sort((a, b) => a.year - b.year || (a.level || 1) - (b.level || 1));
  state.places = places;
  buildScale();

  map = new maplibregl.Map({
    container: "map",
    style: buildStyle(),
    center: [108, 33.5], zoom: 3.7, pitch: 52, bearing: -8,
    maxPitch: 65, minZoom: 2.5, maxZoom: 9.5,
    maxBounds: [[45, -5], [165, 62]],
    attributionControl: false,
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-left");
  map.addControl(new maplibregl.AttributionControl({ compact: true,
    customAttribution: "Terrain: Mapzen/AWS Terrain Tiles · Borders: historical-basemaps (GPL-3.0)" }), "bottom-left");
  // MapLibre opens the compact attribution on wide screens; start it folded to the "i" button.
  const foldAttribution = () => document.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show");
  map.once("load", foldAttribution);
  map.once("idle", foldAttribution);
  map.on("move", () => scheduleDeclutter(120));
  map.on("click", "road-hit", (e) => {
    const r = state.roads.find((x) => x.id === e.features[0]?.properties.id);
    if (r) showCard(e.lngLat, roadCard(r));
  });
  map.on("click", "wall-hit", (e) => {
    const w = state.walls.find((x) => x.id === e.features[0]?.properties.id);
    if (w) showCard(e.lngLat, wallCard(w));
  });
  map.on("mouseenter", "wall-hit", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "wall-hit", () => (map.getCanvas().style.cursor = ""));
  map.on("mouseenter", "road-hit", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "road-hit", () => (map.getCanvas().style.cursor = ""));
  map.on("moveend", () => scheduleDeclutter());
  map.on("zoomend", setTerrainForZoom);
  map.on("load", async () => {
    setTerrainForZoom();
    applyLook();
    renderGeo();
    await setYear(state.year);
    buildRail();
    renderLedger();
    const ev = state.events.find((e) => e.id === state.selected);
    if (ev) map.easeTo({ center: [ev.lon - 4, ev.lat - 3], duration: 0 });
  });

  // Dragging the rail (slider, era bands or ticks) shows a tag with the period and year under the finger.
  // On touch screens the map moves when the finger lifts; with a mouse the slider still updates live.
  const coarse = matchMedia("(pointer: coarse)").matches;
  $("slider").addEventListener("input", (e) => {
    stop();
    const y = posToYear(+e.target.value);
    showScrubTag(+e.target.value, y);
    if (!coarse && y !== state.year) setYear(y, { fromSlider: true });
  });
  $("slider").addEventListener("change", (e) => {
    hideScrubTag();
    const y = posToYear(+e.target.value);
    if (y !== state.year) setYear(y, { fromSlider: true });
  });
  const track = document.querySelector(".track");
  let scrub = null;
  const posAt = (x) => { const r = track.getBoundingClientRect(); return Math.max(0, Math.min(SLIDER_MAX - 1e-6, ((x - r.left) / r.width) * SLIDER_MAX)); };
  $("bands").addEventListener("pointerdown", (e) => { scrub = { x: e.clientX, id: e.pointerId, moved: false }; });
  addEventListener("pointermove", (e) => {
    if (!scrub || e.pointerId !== scrub.id) return;
    if (!scrub.moved && Math.abs(e.clientX - scrub.x) < 6) return;
    if (!scrub.moved) { scrub.moved = true; stop(); try { $("bands").setPointerCapture(e.pointerId); } catch {} }
    const p = posAt(e.clientX);
    scrub.year = posToYear(p);
    showScrubTag(p, scrub.year);
  });
  addEventListener("pointerup", (e) => {
    if (!scrub || e.pointerId !== scrub.id) return;
    const s = scrub; scrub = null;
    if (!s.moved) return;
    hideScrubTag();
    // Swallow the click that follows the drag, so the band under the finger doesn't also fire.
    addEventListener("click", (c) => { c.stopPropagation(); c.preventDefault(); }, { capture: true, once: true });
    setTimeout(() => setYear(s.year), 0);
  });
  addEventListener("pointercancel", () => { scrub = null; hideScrubTag(); });
  $("play").addEventListener("click", play);
  $("zoom-in").addEventListener("click", () => setZoom(state.zoom + 1));
  $("zoom-out").addEventListener("click", () => setZoom(state.zoom - 1));
  $("pan-prev").addEventListener("click", () => pan(-1));
  $("pan-next").addEventListener("click", () => pan(1));
  // Scrolling over the rail zooms it, around the year under the pointer when zooming in.
  let wheelAt = 0;
  document.querySelector(".track").addEventListener("wheel", (e) => {
    if (Math.abs(e.deltaY) < Math.abs(e.deltaX)) return;
    e.preventDefault();
    if (Date.now() - wheelAt < 350) return;
    wheelAt = Date.now();
    const r = e.currentTarget.getBoundingClientRect();
    const y = posToYear(((e.clientX - r.left) / r.width) * SLIDER_MAX);
    setZoom(state.zoom + (e.deltaY < 0 ? 1 : -1), e.deltaY < 0 ? y : state.year);
  }, { passive: false });
  $("lang").addEventListener("click", (e) => { const l = e.target.closest("[data-lang]")?.dataset.lang; if (l && l !== state.lang) setLang(l); });
  toggle("t-3d", "show3d", () => {
    state.terrainExag = null;
    if (state.show3d) setTerrainForZoom(); else map.setTerrain(null);
    map.easeTo({ pitch: state.show3d ? 52 : 0, duration: 800 });
  });
  toggle("t-sat", "showSat", () => {
    try { localStorage.setItem("atlas-look", state.showSat ? "sat" : "relief"); } catch {}
    applyLook();
  });
  toggle("t-neighbours", "showNeighbours", () => {
    const v = state.showNeighbours ? "visible" : "none";
    map.setLayoutProperty("neighbour-fill", "visibility", v);
    map.setLayoutProperty("neighbour-line", "visibility", v);
    renderPolityLabels(state.borders[state.snapshot]);
  });
  toggle("t-places", "showPlaces", renderPlaces);
  toggle("t-geo", "showGeo", () => {
    renderGeo();
    for (const id of ["rivers", "rivers-minor", "lakes"]) map.setLayoutProperty(id, "visibility", state.showGeo ? "visible" : "none");
  });
  // Layer choices are remembered per browser.
  try { Object.assign(state.show, JSON.parse(localStorage.getItem("atlas-layers") || "{}")); } catch {}
  for (const k of Object.keys(state.show)) {
    $("l-" + k).setAttribute("aria-pressed", String(state.show[k]));
    $("l-" + k).addEventListener("click", () => {
      state.show[k] = !state.show[k];
      $("l-" + k).setAttribute("aria-pressed", String(state.show[k]));
      try { localStorage.setItem("atlas-layers", JSON.stringify(state.show)); } catch {}
      renderOverlays();
    });
  }
  const collapseLedger = (c) => {
    $("ledger").classList.toggle("collapsed", c);
    $("ledger-toggle").textContent = c ? t("show") : t("hide");
    $("ledger-toggle").setAttribute("aria-expanded", String(!c));
  };
  for (const k of ["events", "rulers", "people"]) $("tab-" + k).addEventListener("click", () => {
    state.tab = k;
    if (k === "events") state.reading = false;
    collapseLedger(false);
    renderLedger();
  });
  $("ledger-toggle").addEventListener("click", () => collapseLedger(!$("ledger").classList.contains("collapsed")));
  const phone = matchMedia("(max-width: 720px)");
  if (phone.matches) collapseLedger(true);
  // Phone: tools and layer switches sit behind one button; the sheet and era bar size themselves to the timeline.
  const openEra = (o) => { $("era-more").setAttribute("aria-expanded", String(o)); document.querySelector(".era").classList.toggle("open", o); };
  $("era-more").addEventListener("click", () => openEra(!document.querySelector(".era").classList.contains("open")));
  map.on("click", () => { if (phone.matches) openEra(false); });
  new ResizeObserver(() => {
    document.documentElement.style.setProperty("--rail-h", document.querySelector(".rail").offsetHeight + "px");
    fitBandLabels();
  }).observe(document.querySelector(".rail"));
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT") return;
    const i = state.eras.indexOf(state.era);
    if (e.key === "ArrowRight") setYear(state.year + 1);
    if (e.key === "ArrowLeft") setYear(state.year - 1);
    if (e.key === "PageDown" && state.eras[i + 1]) goToEra(state.eras[i + 1]);
    if (e.key === "PageUp" && state.eras[i - 1]) goToEra(state.eras[i - 1]);
    if (e.key === "+" || e.key === "=") setZoom(state.zoom + 1);
    if (e.key === "-") setZoom(state.zoom - 1);
    if (e.key === "Escape" && state.reading) { state.reading = false; renderLedger(); }
    if (e.key === " ") { e.preventDefault(); play(); }
  });
}

init().catch((err) => {
  console.error(err);
  $("era-summary").textContent = t("loadError") + err.message;
});
