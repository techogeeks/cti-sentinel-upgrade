"""Summarize order revenue, top customers, and order sizes."""
def exercise(client, collection):
    orders = collection("orders")
    orders.insert_many([
        {"category": category, "customer": customer, "total": total}
        for category, customer, total in [
            ("Books", "Mira", 35), ("Electronics", "Dev", 300),
            ("Books", "Dev", 70), ("Electronics", "Mira", 120),
            ("Home", "Ira", 55), ("Home", "Mira", 15),
        ]
    ])
    revenue = list(orders.aggregate([
        {"$group": {"_id": "$category", "revenue": {"$sum": "$total"}}},
        {"$sort": {"revenue": -1, "_id": 1}},
    ]))
    top = list(orders.aggregate([
        {"$group": {"_id": "$customer", "spend": {"$sum": "$total"}}},
        {"$sort": {"spend": -1, "_id": 1}}, {"$limit": 2},
    ]))
    sizes = list(orders.aggregate([
        {"$group": {"_id": {"$switch": {"branches": [
            {"case": {"$lt": ["$total", 50]}, "then": "small"},
            {"case": {"$lt": ["$total", 150]}, "then": "medium"},
        ], "default": "large"}}, "orders": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]))
    return {"passed": sum(row["orders"] for row in sizes) == 6 and revenue[0]["revenue"] == 420,
            "category_revenue": revenue, "top_customers": top, "order_sizes": sizes}
