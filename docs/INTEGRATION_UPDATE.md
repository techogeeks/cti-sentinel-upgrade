# MongoDB lab integration update

This update refreshes the catalogue from actual files on disk, adds a read-only source preview API, and enables Run buttons only for the six pre-existing, opt-in Chapter 10–12 runners. Existing CTI, benchmark, replica, and monitoring endpoints are preserved.

## Important missing inputs

The uploaded ZIP has no assignment source scripts for Chapters 1–6. Restore those folders from your working local project before attempting their integration. This update does **not** claim all 36 labs execute. Chapters 7–9 and 13–18 have special infrastructure and side effects; they are inventoried but are **not** executed by a generic source runner.

## Running locally

From project root: `python -m backend.app` (or your existing backend start command); in another terminal `cd frontend; npm install; npm run dev`. Set `ENABLE_LAB_RUNNER=1` only for a trusted, local development environment with an isolated MongoDB instance. Do not expose the Flask development server or opt-in lab routes to the internet.

## API

- `GET /api/assignments`: live catalogue with source-present and runnable flags
- `GET /api/assignments/<chapter>/<lab>/source`: bounded, read-only preview
- `POST /api/labs/<chapter>/<lab>/run`: pre-existing Chapter 10–12 local runners only

## Next phase

Restore Chapters 1–6; audit each lab's database writes and dependencies; implement dedicated, isolated execution adapters; add controlled run history and output capture; validate each lab on its required topology before enabling additional Run buttons.
