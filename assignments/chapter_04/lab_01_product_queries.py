"""Run comparison, logical, array, pagination, and regex queries."""
import re


def exercise(client, collection):
    products = collection("products", {
        "bsonType": "object", "required": ["name", "price", "stock", "tags"],
        "properties": {
            "name": {"bsonType": "string"},
            "price": {"bsonType": ["int", "long", "double", "decimal"], "minimum": 0, "exclusiveMinimum": True},
            "stock": {"bsonType": ["int", "long"], "minimum": 0},
            "tags": {"bsonType": "array", "items": {"bsonType": "string"}},
        },
    })
    seed = [
        ("Wireless Mouse", 30, 5, ["electronics", "wireless"]),
        ("USB Hub", 25, 0, ["electronics", "accessories"]),
        ("Studio Headphones", 120, 4, ["electronics", "premium"]),
        ("Wireless Keyboard", 48, 8, ["electronics", "wireless", "premium"]),
        ("Desk Lamp", 40, 0, ["lighting"]), ("Monitor", 180, 3, ["electronics", "premium"]),
        ("Cotton Bag", 12, 4, ["fabric"]), ("Cotton Case", 23, 9, ["fabric", "accessories"]),
        ("Desk Mat", 20, 3, ["accessories"]), ("Laptop Stand", 50, 2, ["accessories", "premium"]),
    ]
    products.insert_many([{"name": name, "price": price, "stock": stock, "tags": tags}
                          for name, price, stock, tags in seed])
    filters = {
        "price_20_to_50": {"price": {"$gte": 20, "$lte": 50}},
        "out_of_stock": {"stock": 0},
        "out_of_stock_or_over_100": {"$or": [{"stock": 0}, {"price": {"$gt": 100}}]},
        "in_stock_premium": {"$and": [{"stock": {"$gt": 0}}, {"tags": "premium"}]},
        "wireless_electronics": {"tags": {"$all": ["electronics", "wireless"]}},
        "exactly_two_tags": {"tags": {"$size": 2}},
        "regex_cotton": {"name": {"$regex": re.escape("cotton"), "$options": "i"}},
    }
    results = {name: list(products.find(query, {"_id": 0}).sort("name"))
               for name, query in filters.items()}

    def page(number, size):
        return list(products.find({}, {"_id": 0}).sort([("name", 1), ("_id", 1)])
                    .skip((number - 1) * size).limit(size))

    return {"passed": len(results["regex_cotton"]) == 2, "queries": results, "page_2": page(2, 3)}
