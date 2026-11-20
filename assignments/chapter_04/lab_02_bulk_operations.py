"""Verify SKU upserts, bulk updates and repeatable imports."""
from pymongo import UpdateOne


def exercise(client, collection):
    products = collection("inventory")
    products.create_index("sku", unique=True)
    products.insert_many([{"sku": sku, "price": 10, "stock": 0, "is_active": True} for sku in "ABCDE"])

    def set_price(sku, price):
        return products.update_one({"sku": sku},
                                   {"$set": {"price": price},
                                    "$setOnInsert": {"stock": 0, "is_active": True}},
                                   upsert=True)

    updated = set_price("A", 25)
    created = set_price("F", 15)
    bulk = products.bulk_write([
        *(UpdateOne({"sku": sku}, {"$inc": {"stock": 10}}) for sku in "ABC"),
        *(UpdateOne({"sku": sku}, {"$set": {"is_active": False}}) for sku in "DE"),
    ])

    def import_products():
        return products.bulk_write([
            UpdateOne({"sku": sku}, {"$set": {"price": 15}, "$setOnInsert": {"stock": 0}},
                      upsert=True) for sku in "GH"
        ])

    first, second = import_products(), import_products()
    return {"passed": updated.modified_count == 1 and created.upserted_id is not None
                      and bulk.modified_count == 5 and first.upserted_count == 2
                      and second.upserted_count == second.modified_count == 0,
            "bulk": {"modified": bulk.modified_count, "upserted": bulk.upserted_count},
            "imports": {"first_upserted": first.upserted_count, "second_upserted": second.upserted_count},
            "products": list(products.find({}, {"_id": 0}).sort("sku"))}
