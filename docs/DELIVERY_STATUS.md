# Delivery status — verified scope

This is an improved **starter implementation**, not a verified completion of all 36 labs. It is based on the supplied CTI Sentinel source archive.

## New working code paths (require real services)
- Ollama chat: POST /api/ai/chat; local inference with MongoDB-backed conversation history when available; no API key required.
- Replica set inspection: GET /api/labs/replica/status.
- Lab 9.1: POST /api/labs/9/1/benchmark, local opt-in only, 6 combinations × 1,000 inserts. `w:all` means `w` equal to the number of configured replica-set members; tests require three voting/data-bearing members.
- Lab 14.1: GET /api/labs/14/1/metrics, a snapshot, not a scheduled monitor or webhook.
- Frontend: Ollama Chat tab and three lab controls.

## Existing components retained
- CTI Sentinel dashboard, threat management, labs 7.1/7.2, chapter 10–12 opt-in runner, original scripts and configs for 8–18.

## Not yet complete
- Chapters 1–6 have no source in the supplied archive.
- Labs 8.1/8.2, 9.2, 13–18 are not fully wired to executable UI workflows.
- Lab 14.2 automated backup/restore verification, Lab 15 tenant API hardening, Chapter 16 three-database integration, Chapter 17 Atlas RAG, Chapter 18 100k multi-database benchmark are not validated.
- Ollama chat currently has conversation history, **not RAG**. No MongoDB Atlas vector search is implemented in this chat endpoint.
- No Docker build, database integration test, live Ollama request, or deployment to Docker Hub was performed in this environment.

## Safety
Never expose the local lab runner publicly. Run network partitions, failover, backup restores and benchmarks only against isolated lab infrastructure. Keep Ollama bound to localhost; do not expose an unauthenticated Ollama server publicly.
