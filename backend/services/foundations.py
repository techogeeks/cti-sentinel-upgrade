"""Fixed Chapter 1–6 runners using isolated, per-run MongoDB collections."""
from importlib import import_module
import os
from uuid import uuid4

from pymongo import MongoClient

from backend.services.lab_10_12 import LAB_DB, LabSetupError

LABS = {
    (1, 1): "classify_databases",
    (1, 2): "map_application",
    (2, 1): "setup_environment",
    (2, 2): "bookstore_crud",
    (3, 1): "embedded_courses",
    (3, 2): "migrate_blog",
    (4, 1): "product_queries",
    (4, 2): "bulk_operations",
    (5, 1): "sales_analytics",
    (5, 2): "lookup_joins",
    (6, 1): "index_design",
    (6, 2): "index_strategies",
}


def run(chapter, lab):
    uri = os.getenv("MONGO_LABS_URI")
    if not uri:
        raise LabSetupError("Set MONGO_LABS_URI to your isolated MongoDB lab server.")
    module = import_module(f"assignments.chapter_{chapter:02d}.lab_{lab:02d}_{LABS[chapter, lab]}")
    prefix = f"lab{chapter}_{lab}_{uuid4().hex}"
    collections = set()

    with MongoClient(uri, serverSelectionTimeoutMS=5000, timeoutMS=15000) as client:
        db = client[LAB_DB]

        def collection(name, validator=None):
            name = f"{prefix}_{name}"
            collections.add(name)
            if validator:
                return db.create_collection(name, validator={"$jsonSchema": validator})
            return db[name]

        try:
            return {"chapter": chapter, "lab": lab, **module.exercise(client, collection)}
        finally:
            for name in collections:
                db.drop_collection(name)
