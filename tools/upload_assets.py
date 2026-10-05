"""Upload generated assets to the Cloudflare R2 bucket served at https://data.atlas.daiyip.com.

Usage: python3 tools/upload_assets.py [ai]
Reads R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_BUCKET from the environment.
  ai: data/ai/*.webp (made by tools/pack_ai_illustrations.py) go to ai/<file>. The local folder is not in git.
Only files the bucket lacks are sent. Names carry a content hash, so they are cached as immutable."""
import os, sys
from concurrent.futures import ThreadPoolExecutor
import boto3
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SETS = {"ai": ("data/ai", "ai/", "image/webp")}

s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                  region_name="auto")
BUCKET = os.environ["R2_BUCKET"]

def existing(prefix):
    keys = set()
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefix):
        keys.update(o["Key"] for o in page.get("Contents", []))
    return keys

for name in sys.argv[1:] or list(SETS):
    folder, prefix, ctype = SETS[name]
    have = existing(prefix)
    todo = [f for f in sorted(os.listdir(os.path.join(ROOT, folder))) if prefix + f not in have]
    def put(f):
        s3.upload_file(os.path.join(ROOT, folder, f), BUCKET, prefix + f,
                       ExtraArgs={"ContentType": ctype, "CacheControl": "public, max-age=31536000, immutable"})
    with ThreadPoolExecutor(16) as ex: list(ex.map(put, todo))
    print(name, ":", len(todo), "uploaded,", len(have), "already there")
