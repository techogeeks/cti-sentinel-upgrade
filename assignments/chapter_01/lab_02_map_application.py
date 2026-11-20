"""Map access patterns to database models."""
def exercise(client, collection):
    domains = collection("domains")
    examples = [
        ("Ride-sharing", "Profiles", "Flexible fields retrieved together", "document"),
        ("Ride-sharing", "Ride history", "Time ranges per rider", "wide-column"),
        ("Ride-sharing", "Live coordinates", "Latest location by driver ID", "key-value"),
        ("Ride-sharing", "Payments", "Transactional ledger with consistency constraints", "relational"),
        ("Social analytics", "Posts", "Filter flexible content and metadata", "document"),
        ("Social analytics", "Counters", "Frequent increments by post ID", "key-value"),
        ("Social analytics", "Interactions", "Time ranges over partitioned events", "wide-column"),
        ("Social analytics", "Connections", "Traverse followers and mutual links", "graph"),
    ]
    domains.insert_many([{"application": app, "domain": domain, "access_pattern": pattern, "family": family}
                         for app, domain, pattern, family in examples])
    rows = list(domains.find({}, {"_id": 0}).sort([("application", 1), ("domain", 1)]))
    return {"passed": len(rows) == 8, "recommendations": rows}
