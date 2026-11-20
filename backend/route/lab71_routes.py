from flask import Blueprint, jsonify, request

from backend.config.connection import BSON_LIMIT, get_db
from backend.labs import lab71

bp = Blueprint("lab71", __name__)


@bp.get("/lab71/schema")
def schema():
    return jsonify({"relationships": lab71.relationship_report(get_db())})


@bp.get("/lab71/sizes")
def sizes():
    return jsonify({"limitBytes": BSON_LIMIT, "collections": lab71.size_stats(get_db())})


@bp.post("/lab71/build-embedded")
def build():
    return jsonify({"documents": lab71.build_embedded(get_db())})


@bp.get("/lab71/benchmark")
def benchmark():
    runs = min(max(int(request.args.get("runs", 30)), 5), 200)
    return jsonify(lab71.benchmark(get_db(), runs=runs))
