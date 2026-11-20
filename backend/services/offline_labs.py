"""Explicit allowlist of non-destructive educational demos. No arbitrary file execution."""
import os
import subprocess
import sys
from backend.assignment_registry import ROOT

# Exact, reviewed scripts only. All infrastructure-changing labs are excluded.
ALLOWED = {
    (16, 1): [sys.executable, "-m", "assignments.chapter_16.lab_01_polyglot_modeling"],
    (17, 2): [sys.executable, "-c", "import assignments.chapter_17.lab_02_hnsw_vs_ivf as lab; lab.N_VECTORS=450; lab.N_QUERIES=8; lab.main()"],
}


def run_offline(chapter, lab):
    cmd = ALLOWED[(chapter, lab)]
    # Do not pass API keys or DB credentials into subprocesses that do not need them.
    filtered_env = {k: v for k, v in os.environ.items()
                    if not any(t in k.upper() for t in ("KEY", "TOKEN", "SECRET", "PASSWORD", "MONGO_URI", "NVIDIA"))}
    filtered_env.update(PYTHONUTF8="1", NO_COLOR="1")
    try:
        process = subprocess.run(cmd, cwd=str(ROOT), env=filtered_env,
                                 text=True, encoding="utf-8", errors="replace",
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=75, check=False)
    except subprocess.TimeoutExpired:
        return {"chapter": chapter, "lab": lab, "passed": False,
                "error": "Demo exceeded its 75-second time limit."}
    return {"chapter": chapter, "lab": lab, "passed": process.returncode == 0,
            "mode": "isolated-offline-demo", "simulation_only": (chapter, lab) == (17, 2),
            "output": process.stdout[-24000:], "error": process.stderr[-4000:] if process.returncode else None,
            "note": "Lab 17.2 runs a reduced 450-vector educational comparison, not an Atlas-native benchmark." if (chapter, lab) == (17, 2) else "Conceptual database-schema comparison; no live Cassandra/Neo4j queries."}
