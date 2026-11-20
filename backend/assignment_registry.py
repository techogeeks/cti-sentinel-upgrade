"""Live inventory of 18 chapters x 2 labs. Never claim execution without a route."""
from pathlib import Path
import re

from backend.services.foundations import LABS

ROOT = Path(__file__).resolve().parent.parent
EXTENSIONS = {".py", ".sh", ".js", ".ipynb"}
# Support lab_01_... and chapter-qualified names like lab_8.1_... / lab_9.2_...
PATTERN = re.compile(r"^lab[_-]?0*(\d+)(?:\.0*(\d+))?(?:[._-]|$)", re.I)
SPECIAL = {(7, 1): "existing-ui", (7, 2): "existing-ui",
           (9, 1): "benchmark-api", (14, 1): "monitoring-api"}
INTERACTIVE = LABS.keys() | {(10, 1), (10, 2), (11, 1), (11, 2), (18, 1), (18, 2)}
GUIDED = {(12, 1), (12, 2)}
OFFLINE = {(16, 1), (17, 2)}
READ_ONLY = {(8, 2), (14, 1)}


def discover_assignments():
    result = []
    for chapter in range(1, 19):
        folder = ROOT / "assignments" / f"chapter_{chapter:02d}"
        candidates = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS] if folder.is_dir() else []
        for lab in (1, 2):
            files = []
            for path in candidates:
                match = PATTERN.match(path.name)
                if not match:
                    continue
                first, second = int(match.group(1)), match.group(2)
                actual_lab = int(second) if second is not None and first == chapter else first
                if actual_lab == lab:
                    files.append(path.relative_to(ROOT).as_posix())
            if chapter == 7:
                backend_path = ROOT / "backend" / "labs" / f"lab7{lab}.py"
                if backend_path.is_file():
                    files.append(backend_path.relative_to(ROOT).as_posix())
            key = (chapter, lab)
            execution = ("interactive-local" if key in INTERACTIVE else
                         "guided-security" if key in GUIDED else
                         ("offline-demo" if key in OFFLINE else
                          "replica-inspection" if key == (8, 2) else
                          SPECIAL.get(key, "not-wired")))
            result.append({"chapter": chapter, "lab": lab,
                           "title": f"Chapter {chapter} - Lab {lab}",
                           "files": sorted(set(files)),
                           "status": "source-present" if files else "missing-source",
                           "execution": execution,
                           "runnable": bool(files) and key in (INTERACTIVE | GUIDED | OFFLINE),
                           "viewable": bool(files)})
    return result


# Backward compatible import, refreshed by the API per request.
ASSIGNMENTS = discover_assignments()
