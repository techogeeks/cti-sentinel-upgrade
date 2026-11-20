"""Opt-in local-only lab execution routes (not intended for public deployment)."""
import os
from flask import Blueprint, jsonify, request
from pymongo.errors import PyMongoError
from backend.services.lab_10_12 import RUNNERS, LabSetupError
from backend.services import foundations
from backend.services.lab_18 import RUNNERS as CAPSTONE_RUNNERS
from backend.services.offline_labs import ALLOWED, run_offline

bp = Blueprint("lab10_12", __name__)

@bp.post("/labs/<int:chapter>/<int:lab>/run")
def run_lab(chapter, lab):
    if os.getenv("ENABLE_LAB_RUNNER") != "1":
        return jsonify({"error": "Local lab runner disabled. Set ENABLE_LAB_RUNNER=1 in your .env and restart the backend."}), 403
    origin = request.headers.get("Origin", "")
    if origin and origin not in ("http://localhost:5173", "http://127.0.0.1:5173"):
        return jsonify({"error": "Lab execution allowed only from the local development dashboard."}), 403
    key = (chapter, lab)
    fn = RUNNERS.get(key) or CAPSTONE_RUNNERS.get(key)
    if (key in {(10, 1), (10, 2), (11, 2)} or key in CAPSTONE_RUNNERS) and not os.getenv("MONGO_LABS_URI"):
        return jsonify({"error": "Set MONGO_LABS_URI to an isolated lab database/replica set before running this experiment."}), 422
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify({"error": "Local runner is restricted to localhost."}), 403
    if key in foundations.LABS:
        try:
            return jsonify(foundations.run(chapter, lab))
        except LabSetupError as exc:
            return jsonify(error=str(exc)), 422
        except PyMongoError:
            return jsonify(error="The MongoDB lab operation failed. Check MONGO_LABS_URI and permissions."), 422
    if fn is None and (chapter, lab) in ALLOWED:
        return jsonify(run_offline(chapter, lab))
    if fn is None:
        return jsonify({"error": "This lab is not implemented in the interactive runner."}), 404
    try:
        return jsonify(fn())
    except (LabSetupError, PyMongoError) as exc:
        return jsonify({"error": str(exc)}), 422
