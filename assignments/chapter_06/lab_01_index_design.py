"""Measure document scans before and after adding workload-specific indexes."""
import random


def exercise(client, collection):
    logs = collection("logs")
    rng = random.Random(61)
    logs.insert_many([{
        "level": rng.choice(["info"] * 18 + ["warn", "error"]),
        "service": rng.choice(["api", "web", "billing", "jobs"]),
        "status": rng.choice([200] * 35 + [404, 500]),
        "duration": rng.randrange(50, 1000),
    } for _ in range(50_000)])
    queries = [
        ("API errors", {"level": "error", "service": "api"}, [("level", 1), ("service", 1)]),
        ("404 requests", {"status": 404}, [("status", 1)]),
        ("Slow billing", {"service": "billing", "duration": {"$gt": 980}}, [("service", 1), ("duration", 1)]),
    ]

    def explain(query, hint=None):
        cursor = logs.find(query)
        if hint:
            cursor = cursor.hint(hint)
        stats = cursor.explain()["executionStats"]
        return {key: stats[key] for key in ("nReturned", "totalDocsExamined", "totalKeysExamined")}

    before = [explain(query) for _, query, _ in queries]
    results = []
    for (title, query, keys), baseline in zip(queries, before):
        index = logs.create_index(keys)
        results.append({"query": title, "index": index, "before": baseline,
                        "with_index_hint": explain(query, index)})
    return {"passed": all(row["with_index_hint"]["totalDocsExamined"] < row["before"]["totalDocsExamined"]
                          for row in results), "workloads": results}
