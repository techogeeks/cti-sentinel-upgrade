"""Classify products by database family."""
def exercise(client, collection):
    products = collection("products")
    examples = [
        ("MongoDB", "document", "Flexible application records"),
        ("Couchbase", "document", "Application profiles"),
        ("Elasticsearch", "document", "Full-text search"),
        ("Redis", "key-value", "Session lookup"),
        ("Memcached", "key-value", "Cache"),
        ("Cassandra", "wide-column", "Partitioned events"),
        ("HBase", "wide-column", "Sparse tables"),
        ("ScyllaDB", "wide-column", "High-volume events"),
        ("Neo4j", "graph", "Relationship traversal"),
        ("JanusGraph", "graph", "Large connected datasets"),
    ]
    products.insert_many([{"name": name, "family": family, "use_case": use}
                          for name, family, use in examples])
    families = list(products.aggregate([
        {"$sort": {"name": 1}},
        {"$group": {"_id": "$family", "products": {"$push": "$$ROOT"}}},
        {"$project": {"products._id": 0}},
        {"$sort": {"_id": 1}},
    ]))
    return {"passed": len(families) == 4, "families": families, "try_it": [
        {"product": "DynamoDB", "hint": "Primary-key access with structured attributes",
         "classification": "key-value and document"},
        {"product": "InfluxDB", "hint": "Timestamped metric ranges", "classification": "time-series"},
        {"product": "OrientDB", "hint": "Documents with relationship traversal",
         "classification": "document and graph"},
    ]}
