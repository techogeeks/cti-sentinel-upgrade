"""Join orders with customers and find products with no orders."""
def exercise(client, collection):
    orders, customers, products = (collection(name) for name in ("orders", "customers", "products"))
    customers.insert_many([
        {"_id": 1, "name": "Mira", "tier": "gold", "city": "Pune"},
        {"_id": 2, "name": "Dev", "tier": "standard", "city": "Mumbai"},
    ])
    products.insert_many([{"_id": code, "name": name}
                          for code, name in [("A", "Book"), ("B", "Pen"), ("C", "Bag")]])
    orders.insert_many([
        {"_id": 1, "customer_id": 1, "product_ids": ["A", "B"]},
        {"_id": 2, "customer_id": 2, "product_ids": ["A"]},
        {"_id": 3, "customer_id": 1, "product_ids": []},
    ])
    joined = list(orders.aggregate([
        {"$lookup": {"from": customers.name, "localField": "customer_id",
                     "foreignField": "_id", "as": "customer"}},
        {"$unwind": "$customer"}, {"$sort": {"_id": 1}},
    ]))
    unused = list(products.aggregate([
        {"$lookup": {"from": orders.name, "localField": "_id",
                     "foreignField": "product_ids", "as": "orders"}},
        {"$match": {"orders": {"$size": 0}}}, {"$project": {"orders": 0}},
    ]))
    with_products = list(orders.aggregate([
        {"$lookup": {"from": products.name, "localField": "product_ids",
                     "foreignField": "_id", "as": "products"}},
        {"$sort": {"_id": 1}},
    ]))
    return {"passed": len(joined) == 3 and [p["_id"] for p in unused] == ["C"],
            "customer_orders": joined, "never_ordered": unused, "orders_with_products": with_products}
