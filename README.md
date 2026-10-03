<p align="center"><img src="docs/img/logo.svg" width="112" alt="Atlas logo"></p>

<h1 align="center">Atlas</h1>

**An interactive 3D history map, from 3000 BCE to today.** Pick a year and the map shows that moment's borders,
cities and events. Take guided tours, read the stories behind events, and switch on layers for armies, roads, faith,
inventions and more. It works in English and Chinese.

**[Open the atlas → atlas.daiyip.com](https://atlas.daiyip.com)**

![The atlas in 221 BCE, when Qin unifies China](docs/img/atlas.jpg)

- **The whole world, 3000 BCE to 2010.** Borders come from historical-basemaps. The timeline follows the
  civilisation you are looking at: over Europe it shows Europe's periods, over India India's.
- **China in depth.** It covers Xia to Qing, with 1,654 events, rulers, people, battles, roads, walls and 104 guided
  tours.
- **3D terrain and satellite imagery** are bundled with the site, so it needs no API keys or tile servers.
- **An engine for your own history.** Any site can show its own periods, events, tours, map layers and plugins on the
  atlas, and embed the result.

## Use it with your own data

Put your history in a **data pack**, a folder of JSON files with a `manifest.json`, and point the atlas at it:

```
https://atlas.daiyip.com/?pack=https://example.org/atlas/manifest.json&packonly=1
```

The atlas provides the map, terrain, borders, timeline, tours and search. Your pack provides:

| | |
| --- | --- |
| **Periods, events and tours** | `eras.json`, `events.json`, `tours.json`. See [docs/custom-data.md](docs/custom-data.md). |
| **Map layers** | GeoJSON roads, regions or sites that appear and disappear with the years. No code needed. See [docs/plugins.md](docs/plugins.md#layers). |
| **Plugins** | JavaScript modules that get the map and the atlas's events, for animations and anything interactive. See [docs/plugins.md](docs/plugins.md#plugins). |

![A pack with its own layers and a journey playback plugin](docs/img/pack-demo.jpg)

[`examples/demo-pack/`](examples/demo-pack/) is a complete pack: Paul's journeys, Roman roads and churches as
layers, and a plugin that animates each leg of a journey. To try it, open
`/?pack=examples/demo-pack/manifest.json&packonly=1#tour=paul-first&s=1` on a local copy.

### Embed it in your app

The atlas is a plain web page, so it embeds with an `iframe`:

```html
<iframe id="atlas" style="width: 100%; height: 600px; border: 0" allow="fullscreen"
  src="https://atlas.daiyip.com/?pack=https://example.org/atlas/manifest.json&packonly=1#tour=paul-first&s=1&l=en">
</iframe>

<script>
  // Move the embedded atlas: change the hash and it reloads at that place.
  const atlas = document.getElementById("atlas");
  const base = atlas.src.split("#")[0];
  function showTour(id, step) { atlas.src = `${base}#tour=${id}&s=${step}&l=en`; }
  function showYear(year, lon, lat, zoom = 6) { atlas.src = `${base}#y=${year}&c=${lon},${lat},${zoom},45,0&l=en`; }
</script>
```

| Address | Effect |
| --- | --- |
| `?pack=<manifest URL>` | Loads your pack. Add `&packonly=1` to hide the atlas's own data. |
| `?lang=en` / `zh` | Interface language. |
| `#y=<year>&c=<lon>,<lat>,<zoom>,<pitch>,<bearing>` | Opens at a year and camera. Negative years are BCE. |
| `#tour=<id>&s=<step>` | Starts a tour at a step (counting from 1). |
| `#e=<event id>` | Opens an event's story. |

Your pack's map layers and plugins come along automatically, because they are part of the pack.

**Allowed sites.** The atlas puts pack text into its page and runs pack plugins, so on atlas.daiyip.com it loads packs
only from the sites in `PACK_ORIGINS` in [`app.js`](app.js). To use your own site, either open a pull request that
adds it, or self-host the atlas: it is a static site, and a pack on the same site always loads. Your files need
`Access-Control-Allow-Origin` (GitHub Pages sends it). See
[docs/custom-data.md](docs/custom-data.md#hosting-and-the-allowlist).

## Run it locally

It is a static site with no build step:

```sh
git clone https://github.com/daiyip/atlas && cd atlas
python3 -m http.server 8000
# open http://localhost:8000
```

Opening `index.html` straight from disk won't work, because browsers block `fetch()` of local files.

## Docs

- [docs/custom-data.md](docs/custom-data.md): the data pack format, hosting and links.
- [docs/plugins.md](docs/plugins.md): map layers and the plugin API.
- [docs/internals.md](docs/internals.md): how the built-in data is organised and built, data sources and known limits.

## Credits

Borders: [historical-basemaps](https://github.com/aourednik/historical-basemaps) (GPL-3.0). Terrain: Mapzen / AWS
Terrain Tiles. Imagery: Sentinel-2 cloudless mosaic 2020, contains modified Copernicus Sentinel data processed by
Sentinel Hub (CC BY 4.0). Rivers and lakes: Natural Earth. Map rendering: [MapLibre GL JS](https://maplibre.org).
Events, stories, tours and Chinese translations were drafted with an AI model and have not been checked line by line
against sources. See [docs/internals.md](docs/internals.md#data-sources-and-known-limits).

## License

The code is released under the [MIT License](LICENSE). Bundled third-party data keeps its own licence: the border
maps derived from historical-basemaps are GPL-3.0, the satellite imagery is CC BY 4.0, and illustrations from
Wikimedia Commons carry the licence shown under each image.
