"""Threat endpoints: search, filter, sort, paginate, create, classify."""
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, jsonify, request
from pymongo import ReturnDocument

from backend.config.connection import get_db
from backend.services.classifier import SEVERITY_RANK, suggest

bp = Blueprint("threats", __name__)

SORTS = {
    "newest": {"created_at": -1},
    "severity": {"severity_rank": -1, "created_at": -1},
    "confidence": {"classification.confidence": -1, "created_at": -1},
}
VERDICTS = ["Malicious", "Suspicious", "Benign"]

INDICATOR_PATTERNS = [
    ("url", re.compile(r"^https?://", re.I)),
    ("ip", re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")),
    ("sha256", re.compile(r"^[a-f0-9]{64}$", re.I)),
    ("sha1", re.compile(r"^[a-f0-9]{40}$", re.I)),
    ("md5", re.compile(r"^[a-f0-9]{32}$", re.I)),
    ("email", re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")),
    ("domain", re.compile(r"^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$", re.I)),
]


def oid(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise ValueError("Invalid id")


def parse_indicators(raw):
    out = []
    for item in raw or []:
        value = (item.get("value") if isinstance(item, dict) else str(item)).strip()
        if not value:
            continue
        kind = next((k for k, rx in INDICATOR_PATTERNS if rx.match(value)), "other")
        out.append({"type": kind, "value": value})
    return out


def iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def shape(doc):
    src, act = doc.get("src") or {}, doc.get("act") or {}
    cls = dict(doc.get("classification", {}))
    cls["updated_at"] = iso(cls.get("updated_at"))
    cls["history"] = [{**h, "at": iso(h.get("at"))} for h in cls.get("history", [])]
    return {
        "id": str(doc["_id"]), "title": doc.get("title"), "description": doc.get("description", ""),
        "severity": doc.get("severity"), "category": doc.get("category"), "tags": doc.get("tags", []),
        "indicators": doc.get("indicators", []), "referenceUrl": doc.get("reference_url"), "affected": doc.get("affected"), "classification": cls, "createdAt": iso(doc.get("created_at")),
        "source": {"id": str(src["_id"]), "name": src.get("name"), "website": src.get("website"),
                   "type": src.get("type"), "reliability": src.get("reliability"), "tier": src.get("tier")} if src else None,
        "actor": {"id": str(act["_id"]), "name": act.get("name"), "aliases": act.get("aliases", []),
                  "motivation": act.get("motivation")} if act else None,
    }


JOINS = [
    {"$lookup": {"from": "sources", "localField": "source_id", "foreignField": "_id", "as": "src"}},
    {"$unwind": {"path": "$src", "preserveNullAndEmptyArrays": True}},
    {"$lookup": {"from": "threat_actors", "localField": "actor_id", "foreignField": "_id", "as": "act"}},
    {"$unwind": {"path": "$act", "preserveNullAndEmptyArrays": True}},
]


def build_query(args):
    q, term = {}, args.get("search", "").strip()
    if term:
        if args.get("mode") == "text":
            q["$text"] = {"$search": term}  # uses the text index (whole words, stemmed)
        else:
            rx = {"$regex": re.escape(term), "$options": "i"}  # partial matches, e.g. "ransom"
            q["$or"] = [{"title": rx}, {"description": rx}, {"category": rx}, {"tags": rx}, {"indicators.value": rx}]
    for field, key in (("severity", "severity"), ("category", "category"), ("classification.verdict", "verdict")):
        if args.get(key):
            q[field] = args[key]
    if args.get("reviewed") in ("true", "false"):
        q["classification.reviewed"] = args["reviewed"] == "true"
    if args.get("source"):
        q["source_id"] = oid(args["source"])
    return q


@bp.get("/threats")
def list_threats():
    a = request.args
    q = build_query(a)
    page = max(int(a.get("page", 1)), 1)
    limit = min(max(int(a.get("limit", 12)), 1), 100)
    pipeline = [{"$match": q}]
    if "$text" in q:
        pipeline.append({"$sort": {"score": {"$meta": "textScore"}}})
    else:
        pipeline.append({"$sort": SORTS.get(a.get("sort"), SORTS["newest"])})
    pipeline.append({"$facet": {
        "items": [{"$skip": (page - 1) * limit}, {"$limit": limit}] + JOINS,
        "total": [{"$count": "n"}],
    }})
    res = list(get_db().threats.aggregate(pipeline))[0]
    total = res["total"][0]["n"] if res["total"] else 0
    return jsonify({"items": [shape(d) for d in res["items"]], "total": total, "page": page,
                    "pages": max(1, -(-total // limit))})


@bp.get("/threats/<threat_id>")
def get_threat(threat_id):
    docs = list(get_db().threats.aggregate([{"$match": {"_id": oid(threat_id)}}] + JOINS))
    if not docs:
        return jsonify({"error": "Threat not found"}), 404
    return jsonify(shape(docs[0]))


@bp.post("/threats")
def add_threat():
    db, body = get_db(), request.get_json(silent=True) or {}
    missing = [f for f in ("title", "description", "severity", "category") if not str(body.get(f, "")).strip()]
    if missing:
        return jsonify({"error": "Missing required fields: " + ", ".join(missing)}), 400
    if body["severity"] not in SEVERITY_RANK:
        return jsonify({"error": "Severity must be Critical, High, Medium or Low"}), 400

    name = str(body.get("source") or "Manual entry").strip()
    source = db.sources.find_one_and_update(
        {"name": name},
        {"$setOnInsert": {"name": name, "website": body.get("sourceWebsite", ""), "type": "Community", "reliability": 50, "tier": "C"}},
        upsert=True, return_document=ReturnDocument.AFTER)

    tags = [t.strip().lower() for t in str(body.get("tags", "")).split(",") if t.strip()]
    doc = {"title": body["title"].strip(), "description": body["description"].strip(), "severity": body["severity"],
           "severity_rank": SEVERITY_RANK[body["severity"]], "category": body["category"].strip(), "tags": tags,
           "indicators": parse_indicators(body.get("indicators")), "source_id": source["_id"], "actor_id": None,
           "created_at": datetime.now(timezone.utc)}
    s = suggest(doc, source.get("reliability", 50))
    doc["classification"] = {"verdict": s["verdict"], "confidence": s["confidence"], "reviewed": False,
                             "updated_at": datetime.now(timezone.utc), "history": []}
    new_id = db.threats.insert_one(doc).inserted_id
    return jsonify({"success": True, "id": str(new_id)}), 201


@bp.post("/threats/<threat_id>/suggest")
def suggest_classification(threat_id):
    doc = get_db().threats.find_one({"_id": oid(threat_id)})
    if not doc:
        return jsonify({"error": "Threat not found"}), 404
    src = get_db().sources.find_one({"_id": doc.get("source_id")}) or {}
    return jsonify(suggest(doc, src.get("reliability", 50)))


@bp.patch("/threats/<threat_id>/classify")
def classify(threat_id):
    body = request.get_json(silent=True) or {}
    verdict = body.get("verdict")
    if verdict not in VERDICTS:
        return jsonify({"error": "Verdict must be Malicious, Suspicious or Benign"}), 400
    try:
        confidence = int(body.get("confidence", 80))
    except (TypeError, ValueError):
        return jsonify({"error": "Confidence must be a number"}), 400
    if not 0 <= confidence <= 100:
        return jsonify({"error": "Confidence must be between 0 and 100"}), 400

    now = datetime.now(timezone.utc)
    entry = {"verdict": verdict, "confidence": confidence, "note": str(body.get("note", ""))[:300], "at": now}
    res = get_db().threats.update_one({"_id": oid(threat_id)}, {
        "$set": {"classification.verdict": verdict, "classification.confidence": confidence,
                 "classification.reviewed": True, "classification.updated_at": now},
        # Bounded array pattern: keep only the last 20 changes so the document cannot grow forever.
        "$push": {"classification.history": {"$each": [entry], "$slice": -20}},
    })
    if res.matched_count == 0:
        return jsonify({"error": "Threat not found"}), 404
    return get_threat(threat_id)


@bp.get("/meta")
def meta():
    db = get_db()
    return jsonify({
        "categories": sorted(db.threats.distinct("category")),
        "sources": [{"id": str(s["_id"]), "name": s["name"]} for s in db.sources.find({}, {"name": 1}).sort("name", 1)],
    })


@bp.get("/stats")
def stats():
    db = get_db()
    res = list(db.threats.aggregate([{"$facet": {
        "total": [{"$count": "n"}],
        "verdicts": [{"$group": {"_id": "$classification.verdict", "n": {"$sum": 1}}}],
        "severities": [{"$group": {"_id": "$severity", "n": {"$sum": 1}}}],
        "categories": [{"$group": {"_id": "$category", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}, {"$limit": 8}],
        "reviewed": [{"$match": {"classification.reviewed": True}}, {"$count": "n"}],
        "sources": [{"$group": {"_id": "$source_id", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}, {"$limit": 6},
                    {"$lookup": {"from": "sources", "localField": "_id", "foreignField": "_id", "as": "s"}},
                    {"$unwind": "$s"}, {"$project": {"name": "$s.name", "reliability": "$s.reliability", "n": 1}}],
    }}]))[0]
    pick = lambda key: {r["_id"]: r["n"] for r in res[key]}
    total = res["total"][0]["n"] if res["total"] else 0
    reviewed = res["reviewed"][0]["n"] if res["reviewed"] else 0
    return jsonify({
        "total": total, "reviewed": reviewed, "awaitingReview": total - reviewed,
        "verdicts": pick("verdicts"), "severities": pick("severities"),
        "categories": [{"name": r["_id"], "n": r["n"]} for r in res["categories"]],
        "sources": [{"name": r["name"], "reliability": r["reliability"], "n": r["n"]} for r in res["sources"]],
    })
