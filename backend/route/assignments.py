"""Assignment catalogue and safe source-code preview (no arbitrary execution)."""
from pathlib import Path
from flask import Blueprint, jsonify
from backend.assignment_registry import ROOT, discover_assignments

bp = Blueprint("assignments", __name__)


@bp.get("/assignments")
def assignments():
    items = discover_assignments()
    return jsonify({"assignments": items, "total": len(items),
                    "source_present": sum(a["viewable"] for a in items),
                    "runnable": sum(a["runnable"] for a in items)})


@bp.get("/assignments/<int:chapter>/<int:lab>/source")
def assignment_source(chapter, lab):
    item = next((a for a in discover_assignments()
                 if a["chapter"] == chapter and a["lab"] == lab), None)
    if item is None:
        return jsonify(error="Unknown assignment"), 404
    if not item["files"]:
        return jsonify(error="Source file is not included in this project copy"), 404
    sources = []
    for relative in item["files"]:
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            continue
        if path.stat().st_size > 200_000:
            sources.append({"file": relative, "error": "File exceeds preview limit"})
            continue
        sources.append({"file": relative, "content": path.read_text(encoding="utf-8", errors="replace")})
    return jsonify(chapter=chapter, lab=lab, sources=sources)
