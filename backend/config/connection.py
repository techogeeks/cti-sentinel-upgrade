"""MongoDB connection and index setup, shared by the API, lab scripts and monitor."""
import os

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ctiSentinelDB")
BSON_LIMIT = 16 * 1024 * 1024  # MongoDB's maximum document size

_client = None


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[DATABASE_NAME]


def ensure_indexes(db=None):
    """Create every index the app relies on (safe to call repeatedly)."""
    db = db if db is not None else get_db()

    # Full-text search across the fields analysts search most.
    db.threats.create_index(
        [("title", TEXT), ("description", TEXT), ("category", TEXT),
         ("tags", TEXT), ("indicators.value", TEXT)],
        name="threat_text",
        weights={"title": 10, "tags": 5, "category": 4, "indicators.value": 3, "description": 1},
    )
    # Default listing: most severe first, newest first.
    db.threats.create_index([("severity_rank", DESCENDING), ("created_at", DESCENDING)], name="severity_recent")
    db.threats.create_index([("created_at", DESCENDING)], name="recent")
    db.threats.create_index([("category", ASCENDING), ("severity_rank", DESCENDING)], name="category_severity")
    db.threats.create_index([("classification.verdict", ASCENDING)], name="verdict")
    db.threats.create_index([("source_id", ASCENDING)], name="source_ref")
    db.threats.create_index([("indicators.value", ASCENDING)], name="ioc_value")  # multikey, exact IOC lookups

    # CVE id (or other external id) of threats imported from feeds; unique only where present.
    db.threats.create_index([("external_id", ASCENDING)], name="external_id", unique=True,
                            partialFilterExpression={"external_id": {"$type": "string"}})

    db.sources.create_index([("name", ASCENDING)], name="source_name", unique=True)
    db.threat_actors.create_index([("name", ASCENDING)], name="actor_name", unique=True)

    # Lab 7.1 embedded redesign
    db.threats_embedded.create_index([("assessment.actual_threat", ASCENDING), ("source.reliability", DESCENDING)], name="actual_threat")
    db.threats_embedded.create_index([("source.name", ASCENDING)], name="embedded_source_name")

    # Lab 7.2 working-set collection and report catalogue
    db.security_reports.create_index([("seq", ASCENDING)], name="seq")
    db.report_catalog.create_index([("url", ASCENDING)], name="report_url", unique=True)


def banner(text):
    line = "=" * 60
    print(f"\n{line}\n  {text}\n{line}")
