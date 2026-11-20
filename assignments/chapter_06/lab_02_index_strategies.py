"""Measure index write overhead and compare covered and fetched queries."""
from time import perf_counter


def exercise(client, collection):
    plain, indexed = collection("plain"), collection("indexed")
    for keys in [[("service", 1), ("duration", 1)], [("status", 1)], [("level", 1)],
                 [("seq", 1)], [("duration", 1)]]:
        indexed.create_index(keys)
    rows = [{"seq": i, "service": f"svc{i % 100}", "duration": i % 999,
             "status": 200 if i % 11 else 404, "level": "info", "payload": "request details"}
            for i in range(10_000)]

    def insert(target):
        start = perf_counter()
        target.insert_many([dict(row) for row in rows])
        return perf_counter() - start

    plain_seconds, indexed_seconds = insert(plain), insert(indexed)
    query = {"service": "svc1"}
    covered = {"_id": 0, "service": 1, "duration": 1}
    fetched = {**covered, "payload": 1}

    def compare(projection):
        def cursor():
            return indexed.find(query, projection).hint("service_1_duration_1")
        docs = cursor().explain()["executionStats"]["totalDocsExamined"]
        start = perf_counter()
        for _ in range(1000):
            list(cursor())
        return {"documents_examined": docs, "elapsed_ms": round((perf_counter() - start) * 1000, 2)}

    normal, optimized = compare(fetched), compare(covered)
    return {"passed": optimized["documents_examined"] == 0 < normal["documents_examined"],
            "write_overhead_percent": round((indexed_seconds / plain_seconds - 1) * 100, 2),
            "fetched": normal, "covered": optimized,
            "note": "Timings are from this run and vary with server load and cache state."}
