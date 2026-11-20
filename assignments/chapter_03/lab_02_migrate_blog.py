"""Join referenced comments and migrate them into embedded post documents."""
def exercise(client, collection):
    posts, comments, embedded = (collection(name) for name in ("posts", "comments", "embedded"))
    posts.insert_many([{"_id": i, "title": f"Post {i}"} for i in range(1, 6)])
    comments.insert_many([{"_id": i, "post_id": (i - 1) // 2 + 1, "body": f"Comment {i}"}
                          for i in range(1, 11)])
    comments.create_index([("post_id", 1), ("_id", 1)])
    lookup = {"$lookup": {"from": comments.name, "localField": "_id",
                          "foreignField": "post_id", "as": "comments"}}
    referenced = list(posts.aggregate([{"$match": {"_id": 1}}, lookup]))[0]
    migrated = list(posts.aggregate([lookup]))
    embedded.insert_many(migrated)
    sample = embedded.find_one({"_id": 1})
    return {"passed": len(migrated) == 5 and sum(len(row["comments"]) for row in migrated) == 10,
            "with_lookup": referenced, "embedded": sample,
            "read_queries": {"separate_find_calls": 2, "lookup": 1, "embedded": 1},
            "large_roster_design": "For 10,000 comments, keep separate documents with an index on post ID and paginate. A growing embedded array risks the 16 MiB document limit."}
