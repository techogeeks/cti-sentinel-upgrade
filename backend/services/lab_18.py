"""Run the capstone against a dedicated MongoDB lab server."""
import os
from uuid import uuid4

from pymongo import MongoClient

from assignments.chapter_18.lab_01_comparative_capstone import (
    benchmark_mongodb,
    generate_transactions,
)
from assignments.chapter_18.lab_02_comparative_report import build_report
from backend.services.lab_10_12 import LAB_DB, LabSetupError


def run_capstone():
    uri = os.getenv("MONGO_LABS_URI")
    if not uri:
        raise LabSetupError("Set MONGO_LABS_URI to an isolated MongoDB lab server.")

    with MongoClient(uri, serverSelectionTimeoutMS=5000, timeoutMS=15000) as client:
        transactions = generate_transactions()
        collection = client[LAB_DB][f"lab18_transactions_{uuid4().hex}"]
        try:
            collection.insert_many(transactions)
            collection.create_index([("user_id", 1), ("timestamp", -1)], name="idx_user_time")
            collection.create_index([("risk_score", -1)], name="idx_risk")
            collection.create_index([("category", 1)], name="idx_category")
            return benchmark_mongodb(collection, transactions)
        finally:
            collection.drop()


def benchmark():
    rows = run_capstone()
    return {
        "chapter": 18,
        "lab": 1,
        "passed": True,
        "measurements": [
            {"workload": name, "duration_ms": round(seconds * 1000, 3), "count": count}
            for name, seconds, count in rows
        ],
        "note": "Live MongoDB measurements using synthetic transactions.",
    }


def comparative_report():
    report = build_report(run_capstone(), mongo_measured=True)
    return {
        "chapter": 18,
        "lab": 2,
        "passed": True,
        "output": report,
        "note": "MongoDB timings are measured. Cassandra and Neo4j figures are estimates.",
    }


RUNNERS = {(18, 1): benchmark, (18, 2): comparative_report}
