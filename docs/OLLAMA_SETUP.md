# CTI Sentinel — Ollama-only AI setup (Windows)

Ollama replaces the cloud NVIDIA backend. No API key is needed. This document
covers the AI assistant; existing MongoDB labs are separate features.

## Quick start

1. Install the official Windows application from https://ollama.com/download/windows.
2. Close VS Code and open it again (so PowerShell gets the new PATH).
3. In **a new PowerShell terminal** run:

   ```powershell
   ollama --version
   ollama pull qwen2.5:3b
   ollama list
   ```

   `qwen2.5:3b` is a modest starting model for 16 GB RAM. CPU inference may be
   slow; it is not guaranteed to fit every machine or model variant.

4. Test Ollama without Flask at http://127.0.0.1:11434/api/tags.
   A JSON response with `models` means the local Ollama HTTP API is reachable.
   For the chat API, Ollama uses `POST /api/chat` and `stream:false`.
5. Start MongoDB and Flask from the project root, and Vite from `frontend`:

   ```powershell
   python -m pip install -r requirements.txt
   python -m backend.app
   ```

   In a **second** terminal, from the same project root:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Or double-click `start-windows.bat` after dependencies are installed.
6. Open http://localhost:5173 > **AI assistant** > **Refresh**.

## Verify the integration

- `http://127.0.0.1:5000/api/ai/status` should show
  `"provider":"OLLAMA"`, `"available":true`, and at least one installed model.
- Send the message `Explain MongoDB replication in two sentences` in the UI.
- PowerShell API test (only if Flask and Ollama are running):

  ```powershell
  $body = @{message="Explain MongoDB replication in two sentences"} | ConvertTo-Json
  Invoke-RestMethod -Uri http://127.0.0.1:5000/api/ai/chat -Method Post -ContentType 'application/json' -Body $body
  ```

## Troubleshooting

- **`ollama` command not found:** Install Ollama for Windows and restart VS Code.
  Check `Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"`.
- **Ollama offline:** Launch the installed Ollama desktop app. If you are
  running Ollama without its desktop service, start `ollama serve` in a terminal.
  Do not start a second server if one already listens on 11434.
- **No models:** Run `ollama pull qwen2.5:3b`, then click **Refresh**.
- **Model missing:** Choose a model displayed in the dropdown, or pull it.
- **Flask offline:** From the project root run `python -m backend.app`.
- **Slow response:** The first response loads the model into memory; CPU-only
  laptops can be slow. Try a smaller local model if necessary.
- **Docker:** `localhost` inside Docker means the container. The included
  `docker-compose.app.yml` uses `http://host.docker.internal:11434`. Ollama may
  need host access/firewall configuration. Use the Windows launcher for easiest setup.
- **Privacy:** Inference is local for a local Ollama server. The app also saves
  conversation text in your configured MongoDB when available. The app does not
  provide user authentication; use it only on a trusted local machine.

This update **does not** make all 24 Chapter 7–18 labs executable. The registry
shows which labs have working routes and which require separate infrastructure.

## Running MongoDB labs from chat

Use `run lab 10.1` or `/run 10.1` in **Ollama AI Assistant**. Chat shows the JSON returned by Flask. Explicit lab commands also work while Ollama is offline.

1. Copy `.env.example` to `.env` if needed. Set `ENABLE_LAB_RUNNER=1` and restart Flask.
2. For Labs 10.1, 10.2 and 11.2, start the isolated database and configure `MONGO_LABS_URI` using [the Chapters 10–11 setup guide](CHAPTER_10_11_SETUP.md).
3. Start the local frontend at `http://localhost:5173`. Run `run lab 11.1` to check the execution path without a database, then try `run lab 10.1` to test transactions.

Chat supports Labs 8.2, 10.1, 10.2, 11.1, 11.2, 12.1, 12.2, 14.1, 16.1 and 17.2. Use the Assignments dashboard for Chapter 7 workspaces and to confirm and launch the Lab 9.1 benchmark. Labs that require manual infrastructure setup remain available in the assignment catalog.

### Chapter 18 capstone

With `ENABLE_LAB_RUNNER=1` and `MONGO_LABS_URI` configured, use **Run experiment** in Assignments or send `run lab 18.1` or `run lab 18.2` in chat. The runner measures four MongoDB workloads on synthetic transactions. Lab 18.2 returns the Markdown report with estimates labeled for Cassandra and Neo4j.

To write the report to disk, run `python -m assignments.chapter_18.lab_02_comparative_report` from the project root.

### Chapters 1–6

With `ENABLE_LAB_RUNNER=1` and `MONGO_LABS_URI` configured, open **MongoDB labs** or enter an explicit command such as `run lab 3.1` in the AI Assistant. Each run uses its own temporary collections under `cti_sentinel_labs_sandbox` and removes them when finished.

Lab 2.1 reports the local server version using PyMongo's `server_info()`. To complete the Atlas comparison, set `MONGO_URI_ATLAS` in your private `.env` and restart Flask. Lab 2.2 returns before-and-after prices for verification in the app. It removes its temporary collection, so it does not provide a persistent collection for Compass screenshots.

The exercises follow the public chapter references in [NoSQL Databases using MongoDB](https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB). The app integration does not include classroom ZIP or DOCX submission bundles.
