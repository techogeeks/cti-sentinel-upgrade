# Chapters 10–11: Synthetic-data experiments

No external dataset is required. All test records are generated in code and **are not real bank accounts, inventory or customers**.

## Windows PowerShell setup

From the repository root, with Docker Desktop running:

```powershell
docker compose -f docker-compose-labs.yml up -d
# Wait until MongoDB is ready (repeat if the container is still starting):
docker exec cti-mongo-labs mongosh --quiet --eval "db.adminCommand({ping:1})"
# Initialize the isolated single-node replica set once:
docker exec cti-mongo-labs mongosh --quiet --eval "rs.initiate({_id:'rs0',members:[{_id:0,host:'localhost:27017'}]})"
```

If you already initialized it, `rs.initiate()` reports that the replica set is already configured. Check with:

```powershell
docker exec cti-mongo-labs mongosh --quiet --eval "rs.status().ok"
```

In `.env`, set:

```dotenv
ENABLE_LAB_RUNNER=1
MONGO_LABS_URI=mongodb://127.0.0.1:27019/?directConnection=true
```

The isolated database is `cti_sentinel_labs_sandbox`; the experiment code resets **only its own** `lab10_1_*`, `lab10_2_*`, and `lab11_2_*` collections on each run. Do not store anything valuable in those collections.

Install Python dependencies with `python -m pip install -r requirements.txt`, then start the backend from the project root using `python -m backend.app`. Run the React UI in another terminal with `cd frontend; npm install; npm run dev`.

## What each lab does

- **10.1:** Seeds three test accounts, transfers 1500 inside a multi-document transaction, attempts an insufficient-funds transfer, and verifies that the second transaction leaves balances unchanged.
- **10.2:** Seeds one product with five units and starts ten competing reservation requests. A conditional stock update and transaction prevent negative stock and overselling. Retryable conflicts are handled by PyMongo's transaction helper.
- **11.1:** Produces a decision matrix from fixed illustrative assumptions; no MongoDB is required for the calculation.
- **11.2:** Generates and inserts 10,000 synthetic documents, then hashes user IDs into four *simulated* shard buckets. This does **not** create real shards or measure actual cluster distribution.

## Limitations

- A standalone MongoDB server cannot run Chapter 10 multi-document transactions. Use the isolated replica set above or an appropriate Atlas cluster.
- This Docker replica set is **for local coursework only**: it has no authentication and is bound to the host loopback address.
- The lab runner is local-only and off by default. Do not expose the Flask debug server or the lab runner on the public internet.
- No end-to-end MongoDB run has been verified in the supplied archive. Check the returned `passed` field and inspect the results on your machine.
