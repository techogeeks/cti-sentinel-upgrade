from flask import Blueprint, jsonify, request

from backend.config.connection import get_db
from backend.labs import monitor
from backend.labs.lab72 import cache_snapshot

bp = Blueprint("monitoring", __name__)


@bp.get("/monitor/cache")
def cache():
    return jsonify(cache_snapshot(get_db()))


@bp.get("/monitor/new-reports")
def new_reports():
    new, total, errors = monitor.find_new_reports(get_db())
    return jsonify({"linksFound": total, "new": new[:200], "newCount": len(new), "errors": errors,
                    "catalogSize": get_db().report_catalog.count_documents({})})


@bp.post("/monitor/ingest")
def ingest():
    db = get_db()
    new, _, errors = monitor.find_new_reports(db)
    return jsonify({"saved": monitor.ingest(db, new), "errors": errors})


@bp.post("/monitor/sync-gcve")
def sync_gcve():
    """Fetch the GCVE 'recent' feed and add vulnerabilities that are not in the platform yet."""
    db = get_db()
    new, errors = monitor.find_new_gcve(db)
    return jsonify({"found": len(new), "saved": monitor.ingest_gcve(db, new), "errors": errors})
