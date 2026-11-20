"""Exercise the bookstore's CRUD operations and pre-2010 price update."""
def exercise(client, collection):
    books = collection("books")
    seed = [
        ("Clean Code", 2008, 40), ("Design Patterns", 1994, 60),
        ("The Pragmatic Programmer", 2019, 50), ("Learning Python", 2013, 35),
        ("Architecture Patterns with Python", 2020, 45),
    ]
    books.insert_many([{"title": title, "year": year, "price": price}
                       for title, year, price in seed])
    old = {"year": {"$lt": 2010}}
    before = list(books.find(old, {"_id": 0}).sort("title"))
    change = books.update_many(old, {"$mul": {"price": 1.10}})
    after = list(books.find(old, {"_id": 0}).sort("title"))
    recent = list(books.find({"year": {"$gte": 2010}}, {"_id": 0}).sort("title"))
    deleted = books.delete_one({"title": "Clean Code"})
    return {
        "passed": change.modified_count == 2 and deleted.deleted_count == 1,
        "before": before, "after": after, "recent_unchanged": recent,
        "remaining": list(books.find({}, {"_id": 0}).sort("title")),
        "note": "The before/after query verifies the update. Dashboard runs clean up the temporary collection.",
    }
