"""One-off: copy Atlas's files on R2 from the bucket's top level into atlas/, the folder Atlas owns.

Usage: python3 tools/r2_migrate.py [--delete-old]
Same ATLAS_R2_* environment as tools/upload_assets.py. For each of ai/, music/, narration/ and tiles/, every object is
copied inside the bucket (no download) to atlas/<same key>, keeping its content type and cache header. Objects already
there with the same size and ETag are skipped, so the script can be rerun. Nothing is deleted: the top-level copies stay
until they are removed by hand once the site has read from atlas/ for a while. Ends with a count per folder and any
mismatch, and lists top-level prefixes it doesn't know (left alone).
--delete-old then deletes each top-level object whose atlas/ copy has the same size and ETag (done 2026-10-06).
It never deletes under atlas/, apps/ or any other folder."""
import os, sys
from concurrent.futures import ThreadPoolExecutor
import boto3
s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['ATLAS_R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                  aws_access_key_id=os.environ["ATLAS_R2_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["ATLAS_R2_SECRET_ACCESS_KEY"],
                  region_name="auto")
BUCKET, DEST, SETS = os.environ["ATLAS_R2_BUCKET"], "atlas/", ["ai/", "music/", "narration/", "tiles/"]

def listing(prefix):
    out = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefix):
        out.update((o["Key"], (o["Size"], o["ETag"])) for o in page.get("Contents", []))
    return out

tops = {p["Prefix"] for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Delimiter="/")
        for p in page.get("CommonPrefixes", [])}
bad = []
for prefix in SETS:
    src, dst = listing(prefix), listing(DEST + prefix)
    todo = [k for k in sorted(src) if dst.get(DEST + k) != src[k]]
    def copy(k):
        s3.copy_object(Bucket=BUCKET, Key=DEST + k, CopySource={"Bucket": BUCKET, "Key": k}, MetadataDirective="COPY")
    with ThreadPoolExecutor(16) as ex: list(ex.map(copy, todo))
    dst = listing(DEST + prefix)
    miss = [k for k in src if dst.get(DEST + k) != src[k]]
    bad += miss
    print(f"{prefix:11} {len(src)} files, {len(todo)} copied, {len(src) - len(miss)} match at {DEST}{prefix}")
    if "--delete-old" in sys.argv:
        gone = [k for k in src if dst.get(DEST + k) == src[k]]
        for i in range(0, len(gone), 1000):
            s3.delete_objects(Bucket=BUCKET, Delete={"Objects": [{"Key": k} for k in gone[i:i + 1000]], "Quiet": True})
        print(f"{'':11} {len(gone)} top-level copies deleted, {len(listing(prefix))} left")
for k in bad[:20]: print("MISMATCH", k)
other = sorted(tops - set(SETS) - {DEST, "apps/"})
if other: print("left alone (unknown top-level folders):", ", ".join(other))
sys.exit(1 if bad else 0)
