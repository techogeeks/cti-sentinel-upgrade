# CTI Sentinel — SOC Dashboard + MongoDB Lab Workspace

**Redesigned UI:** responsive dark security operations dashboard with live MongoDB metrics, source rankings, alert table, lab workspace (Chapters 7–18), and local Ollama chat. No fake data.

**Windows:** run `python -m pip install -r requirements.txt` from the project root, then `cd frontend && npm install` (return to root), start MongoDB, and double-click `start-windows.bat`. Open **http://localhost:5173**.

**Docker local demo:** `docker compose -f docker-compose.app.yml up --build -d`. Open **http://localhost:5000**. This is a local demonstration service, not a secured public production deployment.


## Ollama (local AI; no API key)

1. Install Ollama for Windows: https://ollama.com/download/windows
2. Close and reopen VS Code, then run `ollama --version`.
3. Download the starter model: `ollama pull qwen2.5:3b`.
4. Make sure Ollama is running. Test `http://127.0.0.1:11434/api/tags` in your browser.
5. Start Flask and Vite as usual (or use `start-windows.bat`). Open **AI assistant** and click **Refresh**.

No `.env` file is required for the default localhost Ollama address. If needed,
copy `.env.example` to `.env` and set `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.
When using Docker, the Compose file uses `host.docker.internal` to reach
Ollama running on Windows; host networking/firewall rules may need adjustment.
See [docs/OLLAMA_SETUP.md](docs/OLLAMA_SETUP.md) for troubleshooting.
After installing requirements, run `python -m unittest discover -s tests -p "test_*.py"` for unit tests.

For prerequisites, limitations, and the execution status of the lab experiments, see `docs/RUNNING_AND_TEST_STATUS.md`.

---

# CTI Sentinel — Integrated starter

**Read `docs/DELIVERY_STATUS.md` before claiming assignment completion.**

# CTI Sentinel - Cyber Threat Intelligence platform (Labs 7.1 and 7.2)

Flask + MongoDB backend, React (Vite) frontend. The same code powers the web UI and the lab scripts.

## 1. Prerequisites
MongoDB 4.4 or newer running locally (`$bsonSize` needs 4.4+), Python 3.10+, Node 18+.

## 2. Backend
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt # installs Flask, PyMongo and the other libraries
copy .env.example .env          # optional: only needed if MongoDB is not on localhost
python -m backend.scripts.seed          # loads demo sources, actors and 120 threats, builds indexes
python -m backend.app                   # API on http://127.0.0.1:5000
```
Run the labs as modules (`-m`) from the project root so the imports resolve.

## 3. Frontend
```bash
cd frontend
npm install                     # downloads the dependencies listed in package.json
npm run dev                     # http://localhost:5173 (proxies /api to the backend)
```

## 4. Lab scripts (terminal)
| Command | What it does |
|---|---|
| `python -m backend.labs.lab71` | Embed vs reference analysis, `$bsonSize` stats, embedded redesign and benchmark |
| `python -m backend.labs.lab72` | Inserts 100,000 documents of about 2 KB, prints WiredTiger cache metrics, runs random reads |
| `python -m backend.labs.monitor` | Prints the cache hit ratio every 10 s and scans for new threat reports |
| `python -m backend.labs.monitor --once --ingest` | One reading and one scan, saving new reports to `report_catalog` |

The existing Lab 7.1/7.2 scripts have dedicated tabs. Labs 10–11 have an opt-in local runner on the Assignments tab. Chapter 12 has read-only setup checks and a manual guide.

## 5. GCVE vulnerability feed (https://db.gcve.eu/recent)
- UI: the **Sync GCVE feed** button on the Threats tab, or `POST /api/monitor/sync-gcve`.
- Terminal: `python -m backend.labs.monitor --once --ingest` (the monitor also lists new GCVE entries on every scan).
- It reads the site's Atom feed, which holds only the latest ~10 entries per feed, so sync regularly. Entries become threats in the
  category "Vulnerability" with source "GCVE Vulnerability-Lookup" (reliability 85, editable in `sources`), keyed by CVE id so repeats are skipped.
- The feed has no CVSS score, so severity is estimated from keywords in the description and the verdict is an unreviewed suggestion.

## 6. Features
- Search: live "Contains" search (partial words, IOCs) or MongoDB text index with relevance ranking.
- Filters by severity, verdict, category, source and review status; sorting; pagination.
- Threat classification: rule-based suggestion with the reasons shown, analyst verdict, confidence and note, capped history.
- Overview with clickable charts that open the filtered threat list.
- Add a threat report (indicators are typed automatically: IP, domain, URL, hash, email).

## 7. Schema summary
| Relationship | Design | Reason |
|---|---|---|
| threat -> indicators | Embedded | Read with the threat, small, bounded |
| threat -> classification (+ history, max 20) | Embedded | One-to-one, shown on every row, bounded array |
| threat -> source | Referenced (`source_id`) | Shared by many threats, reliability edited independently |
| threat -> actor | Referenced (`actor_id`) | Shared, has its own growing profile |

Lab 7.1 activity: `threats_embedded` copies the source into each threat and stores `assessment.actual_threat`
(Malicious verdict from a source with reliability of at least 75).
Faster: filtering and listing (no join). Harder: changing a source's reliability must rewrite every copy and recompute the flag.

## 8. Notes
- Seed data is generated sample data (documentation-only IPs, `.example` domains), not real incident reports.
- The report scanner reads the README of `jacobdjwilson/awesome-annual-security-reports` and `ctidigest.com`. If either site changes layout or is unreachable, the scan reports the error and carries on.
- To see the cache hit ratio drop in Lab 7.2, start mongod with a small cache: `mongod --wiredTigerCacheSizeGB 0.25`.
- The default database is `ctiSentinelDB`, so it does not collide with an older `cyberThreatDB`.

## 9. Synthetic data and missing chapters
Chapters 10 and 11 do **not** require an external dataset. This project includes original implementations with generated test data and a local-only runner. Start the isolated replica set using `docker-compose-labs.yml` and follow `docs/CHAPTER_10_11_SETUP.md`. Chapter 12 requires a separate authentication/TLS test instance; follow `docs/CHAPTER_12_SETUP.md`.

**Status:** Labs 10–11 are implemented but not tested against a live MongoDB instance in this archive; Chapter 12 has setup checks, not automated security provisioning. Chapters 8–9 and 13–18 have source scripts but are not yet wired into the runner. Chapters 1–6 are missing from this project. See `docs/INTEGRATION_STATUS.md`.
