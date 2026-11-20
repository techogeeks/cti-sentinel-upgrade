"""Lab 7.2 endpoints. Loading 100,000 documents takes a while, so it runs in a background thread."""
import threading
import time

from flask import Blueprint, jsonify, request

from backend.config.connection import get_db
from backend.labs import lab72

bp = Blueprint("lab72", __name__)
STATE = {"running": False, "loaded": 0, "total": 0, "result": None, "error": None, "started": None}
_lock = threading.Lock()


def _run(count):
    try:
        def progress(n):
            STATE["loaded"] = n
        STATE["result"] = lab72.load_reports(get_db(), count, progress=progress)
    except Exception as exc:
        STATE["error"] = str(exc)
    finally:
        STATE["running"] = False


@bp.post("/lab72/load")
def load():
    count = min(max(int((request.get_json(silent=True) or {}).get("count", 100_000)), 1000), 200_000)
    with _lock:
        if STATE["running"]:
            return jsonify({"error": "A load is already running"}), 409
        STATE.update(running=True, loaded=0, total=count, result=None, error=None, started=time.time())
    threading.Thread(target=_run, args=(count,), daemon=True).start()
    return jsonify(STATE), 202


@bp.get("/lab72/load/status")
def load_status():
    return jsonify(STATE)


@bp.get("/lab72/metrics")
def metrics():
    return jsonify(lab72.cache_snapshot(get_db()))


@bp.post("/lab72/random-reads")
def random_reads():
    body = request.get_json(silent=True) or {}
    total = min(max(int(body.get("reads", 5000)), 500), 50_000)
    try:
        return jsonify(lab72.random_reads(get_db(), total=total))
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400
