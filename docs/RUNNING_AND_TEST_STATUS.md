# CTI Sentinel — Running and verification

## Local Windows launch

1. Install Python dependencies from the root: `python -m pip install -r requirements.txt`.
2. Install frontend packages: `cd frontend && npm install`, then return to the root.
3. Start MongoDB as a local Windows service (or configure `MONGO_URI` in a private `.env`).
4. Double-click `start-windows.bat` from the project root. It opens separate API and Vite terminal windows.
5. Visit http://localhost:5173. API health: http://localhost:5000/api/health.

The dashboard only displays data returned by MongoDB. Empty databases show empty states; it does not invent alerts or metrics. The Ollama AI tab requires a running local Ollama server and an installed model (for example `qwen2.5:3b`); no API key is required.

## Docker local demo (frontend and backend in one container)

`docker compose -f docker-compose.app.yml up --build -d` then open http://localhost:5000.
Compose uses a separate local MongoDB container; do not point this demo at production data.
The Dockerfile uses a two-stage React build and launches Flask on port 5000.

## Test coverage and limitations

- Python bytecode syntax: checked locally.
- Frontend JSX: statically parsed with Babel parser.
- Frontend runtime bundle: depends on npm packages and platform-specific Rollup binaries. Complete `npm install && npm run build` on Windows to verify.
- MongoDB/replica-set workloads: not tested end-to-end in this environment. Keep `ENABLE_LAB_RUNNER=0` unless using a disposable lab database.
- Chapters 7–18: lab source viewing and selected API routes are available, not a claim that all 24 lab experiments execute automatically. Failover, backup/restore and Kubernetes need external lab infrastructure.
- Docker deployment: configuration created, not pushed to Docker Hub or verified with a running Docker daemon.

## UI

Dark security operations layout, KPI tiles, genuine MongoDB severity/verdict breakdowns, recent threats, source rankings, lab workspace, and local Ollama chat. Dashboard uses existing `/api/stats` and `/api/threats` endpoints; no new mock-data dependency.
