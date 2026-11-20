"""Lab 7.2 - Working set analysis.

Run:  python -m labs.lab72 [--count 100000] [--reads 5000]
Inserts ~2 KB security-report documents, reads WiredTiger cache metrics with
serverStatus, then performs random reads and shows how the cache hit ratio moves.
"""
import argparse
import random
import time

import bson

from backend.config.connection import banner, get_db

COLLECTION = "security_reports"
TARGET_BYTES = 2048

VENDORS = ["CrowdStrike", "Mandiant", "Unit 42", "Microsoft", "Cisco Talos", "Kaspersky", "ESET", "SentinelOne",
           "Sophos", "Check Point", "Fortinet", "IBM X-Force", "Verizon", "Recorded Future", "Trend Micro",
           "Palo Alto Networks", "Google TAG", "Proofpoint", "Elastic", "Rapid7"]
TOPICS = ["Global Threat", "Ransomware", "Phishing", "Cloud Security", "Vulnerability", "Identity Attack", "Incident Response"]


def _filler_length():
    probe = {"seq": 0, "title": "x" * 40, "vendor": "x" * 12, "year": 2025, "topic": "x" * 12,
             "url": "https://reports.example/" + "x" * 40, "tags": ["report", "annual"], "summary": ""}
    return max(0, TARGET_BYTES - len(bson.encode(probe)) - 8)


def make_doc(i, filler):
    vendor, topic = VENDORS[i % len(VENDORS)], TOPICS[i % len(TOPICS)]
    year = 2018 + (i % 9)
    return {"seq": i, "title": f"{vendor} {year} {topic} Report #{i}", "vendor": vendor, "year": year, "topic": topic,
            "url": f"https://reports.example/{vendor.lower().replace(' ', '-')}/{year}/{i}",
            "tags": ["report", "annual", topic.lower()], "summary": filler}


def load_reports(db, count=100_000, batch=5000, progress=None):
    """Replace the collection with `count` documents of about 2 KB each."""
    filler = ("threat-intelligence report body text " * 80)[:_filler_length()]
    db.drop_collection(COLLECTION)
    coll = db[COLLECTION]
    start = time.perf_counter()
    for lo in range(0, count, batch):
        coll.insert_many([make_doc(i, filler) for i in range(lo, min(lo + batch, count))], ordered=False)
        if progress:
            progress(min(lo + batch, count))
    elapsed = time.perf_counter() - start
    coll.create_index("seq", name="seq")
    avg = list(coll.aggregate([{"$group": {"_id": None, "avg": {"$avg": {"$bsonSize": "$$ROOT"}}}}]))
    return {"count": count, "seconds": round(elapsed, 1), "docsPerSec": round(count / elapsed),
            "avgDocBytes": round(avg[0]["avg"]) if avg else 0}


def cache_snapshot(db=None, coll=COLLECTION):
    """Read the WiredTiger cache counters used by this lab from serverStatus."""
    db = db if db is not None else get_db()
    c = db.command("serverStatus")["wiredTiger"]["cache"]
    g = lambda key: c.get(key, 0)
    snap = {
        "ts": time.time(),
        "maxBytes": g("maximum bytes configured"),
        "usedBytes": g("bytes currently in the cache"),
        "dirtyBytes": g("tracked dirty bytes in the cache"),
        "pagesRequested": g("pages requested from the cache"),
        "pagesRead": g("pages read into cache"),
        "pagesEvictedByApp": g("pages evicted by application threads"),
    }
    snap["usedPercent"] = round(snap["usedBytes"] / snap["maxBytes"] * 100, 2) if snap["maxBytes"] else 0
    snap["hitRatio"] = hit_ratio(None, snap)
    try:
        cs = db.command("collStats", coll)
        cached = cs.get("wiredTiger", {}).get("cache", {}).get("bytes currently in the cache", 0)
        data = cs.get("size", 0)
        snap.update(dataBytes=data, indexBytes=cs.get("totalIndexSize", 0), collectionCachedBytes=cached,
                    collectionCachedPercent=round(min(cached / data * 100, 100), 1) if data else 0)
    except Exception:
        pass
    return snap


def hit_ratio(prev, cur):
    """Percent of page requests served from memory. 'pages read into cache' are the misses."""
    req = cur["pagesRequested"] - (prev["pagesRequested"] if prev else 0)
    miss = cur["pagesRead"] - (prev["pagesRead"] if prev else 0)
    return round((1 - miss / req) * 100, 2) if req > 0 else None


def random_reads(db, total=5000, chunk=500):
    coll = db[COLLECTION]
    n = coll.estimated_document_count()
    if n == 0:
        raise RuntimeError("security_reports is empty - load the documents first")
    rng = random.Random()
    prev, points, done = cache_snapshot(db), [], 0
    while done < total:
        t = time.perf_counter()
        for _ in range(chunk):
            coll.find_one({"seq": rng.randrange(n)})
        ms = (time.perf_counter() - t) * 1000
        done += chunk
        cur = cache_snapshot(db)
        points.append({"reads": done, "msPerRead": round(ms / chunk, 3), "intervalHitRatio": hit_ratio(prev, cur),
                       "cumulativeHitRatio": cur["hitRatio"], "cacheUsedPercent": cur["usedPercent"]})
        prev = cur
    return {"documents": n, "points": points, "final": prev}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=100_000)
    ap.add_argument("--reads", type=int, default=5000)
    args = ap.parse_args()
    db = get_db()
    banner("Lab 7.2 - Working set analysis")

    print(f"Inserting {args.count:,} documents of about 2 KB ...")
    r = load_reports(db, args.count, progress=lambda n: print(f"  {n:,}", end="\r"))
    print(f"\nInserted in {r['seconds']}s ({r['docsPerSec']:,} docs/s), average {r['avgDocBytes']} bytes per document")

    s = cache_snapshot(db)
    mb = lambda b: f"{b / 1024 / 1024:,.1f} MB"
    print("\nWiredTiger cache (serverStatus)")
    print(f"  cache size configured : {mb(s['maxBytes'])}")
    print(f"  currently in cache    : {mb(s['usedBytes'])} ({s['usedPercent']}% of cache)")
    print(f"  dirty bytes           : {mb(s['dirtyBytes'])}")
    if "dataBytes" in s:
        print(f"  collection data       : {mb(s['dataBytes'])}, indexes {mb(s['indexBytes'])}")
        print(f"  collection data cached: {s['collectionCachedPercent']}%")

    print(f"\nRandom reads ({args.reads:,} reads across the whole collection)")
    print(f"  {'reads':>7} {'ms/read':>9} {'interval hit %':>15} {'cumulative hit %':>17} {'cache used %':>13}")
    for p in random_reads(db, args.reads)["points"]:
        print(f"  {p['reads']:>7} {p['msPerRead']:>9} {str(p['intervalHitRatio']):>15} {str(p['cumulativeHitRatio']):>17} {p['cacheUsedPercent']:>13}")
    print("\nTip: if the whole collection fits in cache the hit ratio stays near 100%.")
    print("To watch it drop, start mongod with a small cache, e.g.  mongod --wiredTigerCacheSizeGB 0.25")


if __name__ == "__main__":
    main()
