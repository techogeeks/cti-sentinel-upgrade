"""Lab 7.1 - Analyze a production schema (threat-intelligence platform).

Run:  python -m labs.lab71
Also used by the API (route/lab71_routes.py) so the web UI shows the same results.
"""
import statistics
import time

from backend.config.connection import BSON_LIMIT, banner, ensure_indexes, get_db

MIN_RELIABILITY = 75  # a source at or above this score is treated as trustworthy


# --------------------------------------------------------------------------
# Task 1 + 2: which relationships embed, which reference, and why
# --------------------------------------------------------------------------
def relationship_report(db):
    n_threats = db.threats.count_documents({})
    n_sources = db.sources.count_documents({})
    n_actors = db.threat_actors.count_documents({})

    agg = list(db.threats.aggregate([
        {"$project": {"n": {"$size": {"$ifNull": ["$indicators", []]}}}},
        {"$group": {"_id": None, "avg": {"$avg": "$n"}, "max": {"$max": "$n"}}},
    ]))
    ind = agg[0] if agg else {"avg": 0, "max": 0}
    per_source = round(n_threats / n_sources, 1) if n_sources else 0
    with_actor = db.threats.count_documents({"actor_id": {"$ne": None}})

    return [
        {
            "relationship": "threat -> indicators (IOCs)", "pattern": "Embedded", "field": "threats.indicators[]",
            "why": "Indicators are always read with their threat, have no life of their own, and the list is small and bounded.",
            "evidence": f"avg {ind['avg']:.1f} and max {ind['max']} indicators per threat.",
            "alternative": None,
        },
        {
            "relationship": "threat -> classification", "pattern": "Embedded", "field": "threats.classification{}",
            "why": "A verdict is one-to-one with the threat and is shown on every list row. History is capped at 20 entries ($slice), so the array can never grow without bound.",
            "evidence": "classification.history is limited to the last 20 changes.",
            "alternative": None,
        },
        {
            "relationship": "threat -> source", "pattern": "Referenced", "field": "threats.source_id -> sources._id",
            "why": "Many threats share one source (a one-to-many relationship), and a source's reliability is edited independently. Embedding copies the source into every threat, so one reliability change means rewriting many documents and risks copies disagreeing.",
            "evidence": f"{n_sources} sources serve {n_threats} threats (about {per_source} threats per source).",
            "alternative": {"source": {"name": "Unit 42", "website": "https://unit42.paloaltonetworks.com", "type": "Vendor", "reliability": 90, "tier": "A"},
                            "assessment": {"actual_threat": True}},
        },
        {
            "relationship": "threat -> actor", "pattern": "Referenced", "field": "threats.actor_id -> threat_actors._id",
            "why": "Actors are shared across many threats and carry their own growing profile (aliases, motivation, techniques). Embedding would duplicate that profile and make actor edits expensive.",
            "evidence": f"{n_actors} actors referenced by {with_actor} of {n_threats} threats.",
            "alternative": {"actor": {"name": "Silent Heron", "aliases": ["SH-01"], "motivation": "Espionage"}},
        },
    ]


# --------------------------------------------------------------------------
# Task 3: average document size with $bsonSize
# --------------------------------------------------------------------------
def size_stats(db):
    out = []
    for name in ["threats", "sources", "threat_actors", "threats_embedded", "security_reports"]:
        if name not in db.list_collection_names():
            continue
        res = list(db[name].aggregate([
            {"$project": {"size": {"$bsonSize": "$$ROOT"}}},
            {"$group": {"_id": None, "avg": {"$avg": "$size"}, "max": {"$max": "$size"},
                        "min": {"$min": "$size"}, "total": {"$sum": "$size"}, "count": {"$sum": 1}}},
        ]))
        if not res:
            continue
        r = res[0]
        pct = r["max"] / BSON_LIMIT * 100
        out.append({
            "collection": name, "documents": r["count"], "avgBytes": round(r["avg"], 1),
            "minBytes": r["min"], "maxBytes": r["max"], "totalBytes": r["total"],
            "percentOfLimit": round(pct, 4),
            "status": "OK" if pct < 50 else "WARNING: approaching the 16 MB limit",
        })
    return out


# --------------------------------------------------------------------------
# Activity 7.1: embed the source (and decide which source is an actual threat)
# --------------------------------------------------------------------------
def _actual_threat_expr(min_rel=MIN_RELIABILITY):
    return {"$and": [{"$eq": ["$classification.verdict", "Malicious"]},
                     {"$gte": ["$source.reliability", min_rel]}]}


def build_embedded(db, min_rel=MIN_RELIABILITY):
    """Rebuild `threats_embedded`: every threat carries a copy of its source."""
    list(db.threats.aggregate([
        {"$lookup": {"from": "sources", "localField": "source_id", "foreignField": "_id", "as": "src"}},
        {"$unwind": {"path": "$src", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"source": {"name": "$src.name", "website": "$src.website", "type": "$src.type",
                                    "reliability": {"$ifNull": ["$src.reliability", 0]}, "tier": "$src.tier"}}},
        {"$addFields": {"assessment": {"actual_threat": _actual_threat_expr(min_rel)}}},
        {"$project": {"src": 0, "source_id": 0}},
        {"$out": "threats_embedded"},
    ]))
    ensure_indexes(db)
    return db.threats_embedded.count_documents({})


def _time(fn, runs):
    fn()  # warm-up so the first run does not pay for cold caches
    times, n = [], 0
    for _ in range(runs):
        t = time.perf_counter()
        res = fn()
        times.append((time.perf_counter() - t) * 1000)
        n = len(res)
    return {"medianMs": round(statistics.median(times), 3), "results": n}


def benchmark(db, runs=30, min_rel=MIN_RELIABILITY):
    """Compare three ways to answer: 'which malicious threats come from trusted sources?'"""
    if db.threats_embedded.count_documents({}) == 0:
        build_embedded(db, min_rel)

    def referenced_lookup():
        return list(db.threats.aggregate([
            {"$match": {"classification.verdict": "Malicious"}},
            {"$lookup": {"from": "sources", "localField": "source_id", "foreignField": "_id", "as": "s"}},
            {"$unwind": "$s"},
            {"$match": {"s.reliability": {"$gte": min_rel}}},
        ]))

    def referenced_two_step():
        ids = [s["_id"] for s in db.sources.find({"reliability": {"$gte": min_rel}}, {"_id": 1})]
        return list(db.threats.find({"classification.verdict": "Malicious", "source_id": {"$in": ids}}))

    def embedded():
        return list(db.threats_embedded.find({"assessment.actual_threat": True}))

    reads = {
        "Referenced with $lookup": _time(referenced_lookup, runs),
        "Referenced, two queries": _time(referenced_two_step, runs),
        "Embedded (single find)": _time(embedded, runs),
    }

    # Write cost: change one source's reliability.
    src = db.sources.find_one(sort=[("reliability", -1)])
    orig = src["reliability"]
    new = orig - 1 if orig > 0 else orig + 1

    t = time.perf_counter()
    db.sources.update_one({"_id": src["_id"]}, {"$set": {"reliability": new}})
    ref_ms = (time.perf_counter() - t) * 1000

    def emb_update(value):
        return db.threats_embedded.update_many(
            {"source.name": src["name"]},
            [{"$set": {"source.reliability": value}},
             {"$set": {"assessment.actual_threat": _actual_threat_expr(min_rel)}}])

    t = time.perf_counter()
    res = emb_update(new)
    emb_ms = (time.perf_counter() - t) * 1000
    db.sources.update_one({"_id": src["_id"]}, {"$set": {"reliability": orig}})  # restore
    emb_update(orig)

    return {
        "minReliability": min_rel, "runs": runs, "reads": reads,
        "writes": {"source": src["name"],
                   "referenced": {"documentsTouched": 1, "ms": round(ref_ms, 3)},
                   "embedded": {"documentsTouched": res.modified_count, "ms": round(emb_ms, 3)}},
        "faster": ["Listing threats with their source (no join or second query).",
                   "Filtering threats by source reliability or by the stored 'actual_threat' flag, using one compound index.",
                   "Showing a threat detail page: one document read."],
        "harder": ["Changing a source's reliability means updating every embedded copy (and recomputing the flag).",
                   "Copies can go stale or disagree if an update is missed.",
                   "Documents are larger (each repeats the source fields), so fewer fit in the cache."],
    }


# --------------------------------------------------------------------------
def main():
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:  # keep the script usable without rich
        Console = Table = None

    db = get_db()
    if db.threats.count_documents({}) == 0:
        print("No data found. Run:  python -m scripts.seed")
        return
    banner("Lab 7.1 - Analyze a production schema")

    print("\n[1] Embedding vs referencing")
    for r in relationship_report(db):
        print(f"\n  {r['relationship']}  ->  {r['pattern'].upper()}  ({r['field']})")
        print(f"    why: {r['why']}")
        print(f"    evidence: {r['evidence']}")
        if r["alternative"]:
            print(f"    embedded alternative would add: {r['alternative']}")

    print("\n[2] Document sizes ($bsonSize)")
    stats = size_stats(db)
    if Console:
        t = Table()
        for c in ["Collection", "Docs", "Avg B", "Max B", "% of 16MB", "Status"]:
            t.add_column(c)
        for s in stats:
            t.add_row(s["collection"], str(s["documents"]), str(s["avgBytes"]), str(s["maxBytes"]), f"{s['percentOfLimit']}%", s["status"])
        Console().print(t)
    else:
        for s in stats:
            print(" ", s)

    print("\n[3] Activity: embed the source and decide which source is an actual threat")
    n = build_embedded(db)
    print(f"  threats_embedded rebuilt with {n} documents")
    b = benchmark(db)
    for name, r in b["reads"].items():
        print(f"  {name:<28} {r['medianMs']:>8} ms  ({r['results']} results)")
    w = b["writes"]
    print(f"  Update one source ({w['source']}): referenced touches {w['referenced']['documentsTouched']} doc, embedded touches {w['embedded']['documentsTouched']} docs")
    print("  Faster :", *b["faster"], sep="\n    - ")
    print("  Harder :", *b["harder"], sep="\n    - ")


if __name__ == "__main__":
    main()
