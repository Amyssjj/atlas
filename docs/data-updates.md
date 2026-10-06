# Updating pictures and map data

The atlas keeps two kinds of data in two places.

| Kind | Where | Examples |
| --- | --- | --- |
| Hand-edited source data, small and worth reviewing as diffs | git, served by GitHub Pages with the page | `data/events.json`, `data/tours.json`, the prompts in `tools/ai_prompts.json`, and the indexes `data/ai-illustrations.json`, `data/tiles.json`, `data/illustrations.json` |
| Large generated binaries that can be rebuilt | the Cloudflare R2 bucket served at `https://data.atlas.daiyip.com`, never git | AI pictures (`atlas/ai/…webp`), elevation and imagery packs (`atlas/tiles/…png`), background music (`atlas/music/…m4a`), tour narration (`atlas/narration/…`) |

Keeping the binaries out of git stops the repository growing by the full size of every regenerated file (git keeps old
versions forever) and keeps the site well under the GitHub Pages size limit. The Wikimedia thumbnails
(`data/img/*.json`, about 13 MB) are still in git; see [internals.md](internals.md#illustrations).

## Changing the shape of the data

Adding events, tours or pictures doesn't change the data format. When a change would make an older page misread the
data or a pack (a new required field, a renamed key, a new file packs rely on), raise the format: bump `FORMAT` in
`app.js` and `"atlas"` in `data/manifest.json`, add an `UPGRADES` step if older files need converting, and add a row
to the table in [custom-data.md](custom-data.md#versions) with the app version (`?v=`) that brings it.
`python3 tools/validate.py` then checks `data/` against the new rules (teach it the new fields too). It runs on
every pull request that touches `data/` (the **Validate data** workflow); see
[Checking a pack](custom-data.md#checking-a-pack).

## Layout on R2

The bucket is shared by Atlas and the apps built on it (bible.daiyip.com, gallery.daiyip.com, …). Each top-level
folder has one owner, and nothing else writes there:

```
atlas/           Atlas's own files: ai/, music/, narration/, tiles/pack/, tiles/sat/
apps/<app-id>/   one folder per app, named after its subdomain (apps/bible/, apps/gallery/), laid out as it likes
```

Each owner keeps the index of its live files in its own repository (for Atlas, the indexes below). A cleanup job may
only delete under one owner's folder, and only files none of that owner's indexes has named in the last 30 days, so a
visitor offline with an older cached index still finds its files. It never touches a folder it doesn't own. `app.js`
builds every R2 address from `R2` (`DATA_URL + "/atlas"`), and `tools/upload_assets.py` writes under `atlas/`.

Until 2026-10 Atlas's files sat at the top level (`ai/`, `music/`, `tiles/`). `tools/r2_migrate.py` copied them into
`atlas/` and, on 2026-10-06, deleted the top-level copies (`--delete-old`).

## How names and caching work

Every file on R2 has a hash of its contents in its name: `atlas/ai/xuanzang-3c41a2bd.webp`,
`atlas/tiles/sat/5-3-1-6f3274a0.png`. A file that changes gets a new name. The small index files in git say which name is
current:

- `data/ai-illustrations.json` maps `a:<event id>` to a picture and its file name.
- `data/tiles.json` maps each pack (`pack/4-0-0`, `sat/5-3-1`) to its current file name.

So the files can be cached for a year (`Cache-Control: public, max-age=31536000, immutable`) by Cloudflare, by the
browser and by the service worker, with no cache to purge after an update. The indexes are fetched fresh whenever the
visitor is online, like `app.js` and `events.json`, so a deploy takes effect at once. Offline, the cached index and
the cached files still match each other.

Once the app has loaded an index, it deletes the files the service worker kept that the index no longer names
(`pruneKept()` in `app.js`), so old versions don't pile up on visitors' devices.

The other rule still holds: bump `?v=` on `style.css` and `app.js` in `index.html` when they change.

## One-time setup

**Credentials.** Uploading needs an R2 API token with *Object Read & Write* on the bucket. Put its values in
`~/.zshrc` (never in the repository). The `ATLAS_` prefix keeps them apart from other projects' R2 credentials:

```sh
export ATLAS_R2_ACCOUNT_ID=…        # 32 hex characters, the <id> in https://<id>.r2.cloudflarestorage.com
export ATLAS_R2_ACCESS_KEY_ID=…
export ATLAS_R2_SECRET_ACCESS_KEY=…
export ATLAS_R2_BUCKET=…
```

AI pictures also need `OPENAI_API_KEY` (and `GOOGLE_API_KEY` for the Gemini option). Downloading needs nothing,
because the files are public.

**Cloudflare settings** (already in place; listed here so they can be rebuilt):

1. R2 bucket → Settings → Custom Domains: `data.atlas.daiyip.com`. Don't use the `r2.dev` development URL: it is
   rate-limited and not cached.
2. R2 bucket → Settings → CORS policy: `GET` and `HEAD` from `https://atlas.daiyip.com` and `http://localhost:8765`.
3. Rules → Response Header Transform Rule on hostname `data.atlas.daiyip.com`: set `Access-Control-Allow-Origin: *`.
   This one matters. Without it, the first copy Cloudflare caches comes from whoever asked first. If that request
   had no `Origin` header (a crawler, a link opened directly), the cached copy has no CORS header, and from then on
   the app's `fetch()` of that pack fails for everyone served by that cache.
4. Caching → Tiered Cache → Smart Tiered Cache (optional). Fewer requests reach R2.

R2 charges for reads only on cache misses. The free allowance (10 million reads and 1 million writes a month, 10 GB)
is far above what the site uses, and R2 doesn't charge for downloads.

**A fresh clone** has no `tiles/` or `data/ai/`. The site doesn't need them, since it reads from R2. The build
tools do (`tools/terrain_grid.py`, `tools/pack_tiles.py` output), so fetch them first:

```sh
python3 tools/fetch_assets.py tiles     # tiles/pack and tiles/sat, from data/tiles.json
python3 tools/fetch_assets.py ai        # data/ai/*.webp, from data/ai-illustrations.json
```

## AI pictures for events

The pictures are generated from `tools/ai_prompts.json`: one English scene per event id. Shown in the app, they always
carry the "AI" badge and the caption 「AI 生成的示意图，非史料」 / "AI-generated illustration, not a historical
source". The full-size originals (1536×1024) live outside the repository, in `~/Pictures/atlas-ai/openai/` on the
machine that made them.

### Writing prompts

Each prompt describes one concrete scene of the event (year, place, setting, clothing, objects, scale) and ends with
a painting style of that place and period (Han tomb mural, Dunhuang mural, Song handscroll, Persian miniature,
ukiyo-e, Maya mural, …). `tools/ai_illustrate.py` appends the fixed rules to every prompt: no text, nothing
anachronistic, no gore, no close-up portraits. Write prompts that already respect them:

- **One scene only.** Words like "and in a second view", "later", "an inset" or "registers" make the model draw
  panels. About two-thirds of the rejected pictures came from this.
- **Spell out period details the model gets wrong.** No ridden cavalry before the late Warring States in China (or
  any horses in Yayoi Japan); no stirrups before about 320 CE; Sui and Tang palaces are not the Forbidden City (no
  yellow tiles or white marble railings); Ming men wear no queues.
- **Violence by distance or aftermath** (smoke over a city, an empty courtyard), never bodies.
- **Real people small, from behind or in a crowd.** Never depict living people or the Prophet Muhammad.
- **Writing rendered illegible.** Steles, books and exam papers get blank or "tiny unreadable marks".
- Avoid words the provider's safety filter misreads as nudity (life-size human figures, painted ceilings of nudes).

### Generating

Up to a few dozen pictures: generate directly. The script retries when rate-limited (this account allows 20 images a
minute) and skips ids that already have a picture.

```sh
python3 tools/ai_illustrate.py ~/Pictures/atlas-ai openai <event id> …      # GPT Image 2, about $0.04 each
```

Hundreds: use the OpenAI Batch API at half price (results within 24 hours, in practice within an hour).

```sh
python3 tools/ai_batch.py submit ~/Pictures/atlas-ai [<event id> …]  # default: every prompt without a picture
python3 tools/ai_batch.py collect ~/Pictures/atlas-ai                # rerun until every batch reads "collected"
```

A request the safety filter rejects is printed as `FAIL <id>`. Reword that prompt and generate it directly.

To redo a picture: move its file out of `~/Pictures/atlas-ai/openai/` (the scripts skip ids that already have one),
fix its prompt, generate again.

### Reviewing

Look at every new picture before publishing, for example on contact sheets of 20 thumbnails labelled with their ids.
Reject:

- split panels or insets
- anachronisms
- prominent fake writing
- blood or bodies
- recognisable faces in close-up
- a picture that doesn't show the event

A picture that can't be fixed can be left out by adding its event id to `data/ai-illustrations-skip.json`.

### Publishing

```sh
python3 tools/pack_ai_illustrations.py ~/Pictures/atlas-ai/openai   # 960×640 WebP in data/ai/, rewrites data/ai-illustrations.json
python3 tools/upload_assets.py ai                                   # sends only the files R2 doesn't have
git add data/ai-illustrations.json tools/ai_prompts.json && git commit
```

Upload before you push the index, so it never names a file that isn't on R2 yet. Old files can stay on R2; nothing
names them any more.

## Background music

One quiet instrumental track per period of every region (220), made with Google Lyria 3.5 from the prompts in
`tools/music_prompts.json` (`"<region>/<period>": prompt`; about $0.08 a track). The app plays the track of the period on
screen during tours and timeline playback when the music switch is on (off by default), crossfading through Web Audio.

```sh
python3 tools/ai_music.py ~/Pictures/atlas-ai/music [<region>/<period> …]   # MP3 originals; skips existing ones
python3 tools/pack_music.py ~/Pictures/atlas-ai/music                       # 96 kbps AAC in data/music/, rewrites data/music.json
python3 tools/upload_assets.py music
git add data/music.json tools/music_prompts.json && git commit
```

Lyria rejects some prompts as "sensitive" (place names such as Cairo or Bukhara, words like "rival" or "rebel");
describe instruments and mood plainly instead. Prompts must stay instrumental and avoid anachronistic instruments.

## Elevation and satellite tiles

The bundled tiles are packs of tiles: one archive per zoom for zooms 0–3, one per 8×8 block from zoom 4. The live
sources take over beyond the bundled zooms. What each pack holds and how to rebuild the tiles from the sources is in
[internals.md](internals.md#how-it-is-put-together) (`tiles/pack/` and `tiles/sat/` rows).

```sh
python3 tools/fetch_assets.py tiles                         # start from the current packs
# …rebuild the tiles, then pack them:
python3 tools/pack_tiles.py <dir of z/x/y.png> tiles/pack           # elevation
python3 tools/pack_tiles.py <dir of z/x/y.jpg> tiles/sat --all      # imagery
python3 tools/upload_assets.py tiles                        # uploads changed packs as <name>-<hash>.png, rewrites data/tiles.json
git add data/tiles.json && git commit
```

Only packs whose content changed get a new name and are uploaded. Visitors get the new packs on their next visit,
and their old copies are deleted.

## Working locally

`python3 -m http.server 8000` (any port) serves the page. It reads pictures and tiles from R2 like the live site;
the Transform Rule's `Access-Control-Allow-Origin: *` lets any local origin read them. To work offline, or to try new packs or pictures before uploading them, serve
a local mirror and point the app at it from the browser console:

```js
localStorage["atlas-data-url"] = "http://localhost:8766"   // a server with ai/ and tiles/ laid out as on R2, sending Access-Control-Allow-Origin
delete localStorage["atlas-data-url"]                      // back to R2
```

## Checking

`python3 tools/check_assets.py` asks R2 for every file the two indexes name and expects each to be there, with the
right content type and an `Access-Control-Allow-Origin` header. It takes about a minute for 2,800 files and exits 1
with a list of failures. The **Assets** workflow (`.github/workflows/assets.yml`) runs it on GitHub whenever
`data/tiles.json` or `data/ai-illustrations.json` changes on `main`, every Monday (in case a Cloudflare setting
changed), and by hand. A red run usually means an index was pushed before its upload.

## Troubleshooting

- **Pictures and terrain missing on one machine only:** its DNS may still remember an old answer for
  `data.atlas.daiyip.com`. On a Mac, run `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`. Also check
  the router's DNS, or use `1.1.1.1`.
- **A pack fails with a CORS error:** check the Transform Rule above. `curl -sD - -o /dev/null -H "Origin:
  https://atlas.daiyip.com" https://data.atlas.daiyip.com/atlas/tiles/<file>` must show `access-control-allow-origin`,
  including on `cf-cache-status: HIT`.
- **The app asks for a file R2 doesn't have:** the index was pushed before the upload. Run `tools/upload_assets.py`.
