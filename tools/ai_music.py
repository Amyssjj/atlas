"""Generate background music for each period with Google Lyria (tools/music_prompts.json: {"<region>/<period>": prompt}).

Usage: python3 tools/ai_music.py OUT_DIR [key ...]
Reads GOOGLE_API_KEY. Writes OUT_DIR/<region>__<period>.mp3 (about 90 s, 44.1 kHz stereo); existing files are skipped.
Lyria 3.5 costs about $0.08 a track; each call's usage goes to OUT_DIR/usage.jsonl (tools/usage.py)."""
import base64, json, os, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from usage import record
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MODEL = "lyria-3.5"

def generate(prompt, tries=4):
    req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/interactions",
                                 json.dumps({"model": MODEL, "input": prompt}).encode(),
                                 {"Content-Type": "application/json", "x-goog-api-key": os.environ["GOOGLE_API_KEY"]})
    for k in range(tries):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=600))
            for step in r.get("steps", []):
                for c in step.get("content") or []:
                    if c.get("type") == "audio": return base64.b64decode(c["data"]), r.get("usage") or {}
            raise RuntimeError("no audio in response: " + json.dumps(r)[:200])
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 503) or k == tries - 1: raise
            time.sleep(20 * (k + 1))

def main():
    out, keys = sys.argv[1], sys.argv[2:]
    prompts = json.load(open(os.path.join(ROOT, "tools/music_prompts.json")))
    os.makedirs(out, exist_ok=True)
    def one(key):
        path = os.path.join(out, key.replace("/", "__") + ".mp3")
        if os.path.exists(path): return
        try:
            data, u = generate(prompts[key])
            record(out, MODEL, key, u.get("total_input_tokens", 0), u.get("total_output_tokens", 0))
            open(path, "wb").write(data); print("ok", key, flush=True)
        except Exception as e:
            print("FAIL", key, (e.read().decode()[:200] if hasattr(e, "read") else str(e))[:200], flush=True)
    with ThreadPoolExecutor(4) as ex: list(ex.map(one, keys or list(prompts)))

if __name__ == "__main__": main()
