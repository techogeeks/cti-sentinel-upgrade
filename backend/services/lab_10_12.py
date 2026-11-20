"""Isolated, synthetic-data MongoDB labs 10-11; read-only security checks for lab 12.

The API deliberately never executes privileged shell scripts, changes server auth,
creates TLS private keys, or modifies non-lab collections.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from threading import Lock

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.config.connection import get_client

# Serializes lab data resets within this Python process; not a distributed lock.
_run_lock = Lock()
LAB_DB = "cti_sentinel_labs_sandbox"


class LabSetupError(RuntimeError):
    pass


def _require_transaction_support(client: MongoClient):
    try:
        hello = client.admin.command("hello")
    except PyMongoError as exc:
        raise LabSetupError(f"MongoDB unavailable: {exc}") from exc
    if not (hello.get("setName") or hello.get("msg") == "isdbgrid"):
        raise LabSetupError(
            "Transactions need a replica set or sharded MongoDB. "
            "Start the included isolated Docker replica set and configure MONGO_LABS_URI."
        )


def _lab_client():
    """Use a separate URI when provided; caller owns the returned client."""
    import os
    uri = os.getenv("MONGO_LABS_URI")
    if uri:
        return MongoClient(uri, serverSelectionTimeoutMS=5000), True
    return get_client(), False


def bank_transfer():
    """Lab 10.1: demonstrate committed transfer and rollback on insufficient funds."""
    client, owned = _lab_client()
    try:
        _require_transaction_support(client)
        db = client[LAB_DB]
        accounts, transfers = db["lab10_1_accounts"], db["lab10_1_transfers"]
        with _run_lock:
            accounts.delete_many({})
            transfers.delete_many({})
            accounts.insert_many([
                {"account_id": "ACC-001", "holder": "Arjun", "balance": 5000},
                {"account_id": "ACC-002", "holder": "Sneha", "balance": 3000},
                {"account_id": "ACC-003", "holder": "Rahul", "balance": 1000},
            ])
            before = _balances(accounts)

            def transfer(sender, receiver, amount):
                def operation(session):
                    debit = accounts.update_one(
                        {"account_id": sender, "balance": {"$gte": amount}},
                        {"$inc": {"balance": -amount}}, session=session,
                    )
                    if debit.matched_count != 1:
                        raise ValueError("Insufficient funds or sender not found")
                    credit = accounts.update_one(
                        {"account_id": receiver}, {"$inc": {"balance": amount}},
                        session=session,
                    )
                    if credit.matched_count != 1:
                        raise ValueError("Receiver not found")
                    transfers.insert_one({
                        "sender": sender, "receiver": receiver, "amount": amount,
                        "created_at": datetime.now(timezone.utc),
                    }, session=session)
                with client.start_session() as session:
                    session.with_transaction(operation)

            transfer("ACC-001", "ACC-002", 1500)
            after_success = _balances(accounts)
            rejected = False
            try:
                transfer("ACC-003", "ACC-001", 5000)
            except ValueError:
                rejected = True
            after_rejection = _balances(accounts)
            return {
                "chapter": 10, "lab": 1, "dataset": "synthetic, generated on each run",
                "before": before, "after_success": after_success,
                "after_rejected_transfer": after_rejection,
                "insufficient_funds_rejected": rejected,
                "rollback_preserved_balances": after_success == after_rejection,
                "committed_transfers": transfers.count_documents({}),
                "passed": rejected and after_success == after_rejection and transfers.count_documents({}) == 1,
            }
    finally:
        if owned:
            client.close()


def _balances(collection):
    return {r["account_id"]: r["balance"] for r in collection.find({}, {"_id": 0, "account_id": 1, "balance": 1})}


def inventory_reservation():
    """Lab 10.2: concurrent, conditional inventory decrement inside transactions."""
    client, owned = _lab_client()
    try:
        _require_transaction_support(client)
        db = client[LAB_DB]
        products, orders = db["lab10_2_products"], db["lab10_2_orders"]
        with _run_lock:
            products.delete_many({})
            orders.delete_many({})
            products.insert_one({"sku": "LAPTOP", "stock": 5, "price": 999})

            def reserve(i):
                def operation(session):
                    changed = products.update_one(
                        {"sku": "LAPTOP", "stock": {"$gte": 1}},
                        {"$inc": {"stock": -1}}, session=session,
                    )
                    if changed.matched_count == 0:
                        return False
                    orders.insert_one({"sku": "LAPTOP", "qty": 1, "request_id": i}, session=session)
                    return True
                try:
                    with client.start_session() as session:
                        return session.with_transaction(operation)
                except PyMongoError as exc:
                    return f"error: {type(exc).__name__}"

            with ThreadPoolExecutor(max_workers=5) as pool:
                outcomes = list(pool.map(reserve, range(10)))
            stock = products.find_one({"sku": "LAPTOP"})["stock"]
            count = orders.count_documents({})
            errors = [r for r in outcomes if isinstance(r, str)]
            return {
                "chapter": 10, "lab": 2, "dataset": "synthetic: 1 product, 5 units, 10 requests",
                "initial_stock": 5, "requests": 10,
                "reservations_succeeded": sum(r is True for r in outcomes),
                "reservations_rejected": sum(r is False for r in outcomes),
                "remaining_stock": stock, "orders_created": count,
                "errors": errors,
                "passed": not errors and stock == 0 and count == 5 and sum(r is True for r in outcomes) == 5,
            }
    finally:
        if owned:
            client.close()


CANDIDATES = [
    ("user_id (hashed)", 1_000_000, .95, .90, False),
    ("order_id (hashed)", 500_000, .90, .60, False),
    ("category_id", 50, .30, .70, False),
    ("created_at (range)", 3_650, .85, .50, True),
]


def shard_key_evaluation():
    """Lab 11.1: decision matrix with explicitly illustrative assumptions."""
    rows = []
    for name, cardinality, evenness, targeting, monotonic in CANDIDATES:
        checks = {
            "high_cardinality": cardinality > 100_000,
            "even_distribution": evenness > .8,
            "query_targeting": targeting > .8,
            "not_monotonic": not monotonic,
        }
        rows.append({
            "candidate": name, "cardinality": cardinality,
            "distribution_score": evenness, "query_targeting_score": targeting,
            "monotonic": monotonic, "checks": checks,
            "score": sum(checks.values()),
        })
    return {"chapter": 11, "lab": 1, "dataset": "built-in illustrative assumptions",
            "simulation_only": True, "ranking": sorted(rows, key=lambda r: r["score"], reverse=True),
            "passed": len(rows) == 4}


def shard_key_hotspot():
    """Lab 11.2: persist synthetic docs, compare simulated 4-shard distribution."""
    docs = [{"ts": i // 1000, "user": f"u-{i % 500:04d}"} for i in range(10_000)]
    buckets = [0] * 4
    for doc in docs:
        index = int.from_bytes(sha256(doc["user"].encode()).digest()[:8], "big") % 4
        buckets[index] += 1
    client, owned = _lab_client()
    try:
        col = client[LAB_DB]["lab11_2_hotspot"]
        with _run_lock:
            col.delete_many({})
            col.insert_many(docs)
            inserted = col.count_documents({})
        return {"chapter": 11, "lab": 2, "dataset": "10,000 generated documents",
                "simulation_only": True, "note": "Hash buckets simulate shards; no sharded cluster is created.",
                "documents_inserted": inserted, "simulated_hashed_shard_counts": buckets,
                "monotonic_key": "increasing ts groups sequential writes",
                "passed": inserted == 10_000 and sum(buckets) == 10_000}
    finally:
        if owned:
            client.close()


def security_readiness(lab):
    """Lab 12: read-only readiness; NEVER create users or certificates from HTTP."""
    import os
    if lab == 1:
        client, owned = _lab_client()
        try:
            response = client.admin.command("connectionStatus")
            info = response.get("authInfo", {})
            return {"chapter": 12, "lab": 1, "mode": "read-only-check",
                    "authenticated_users": info.get("authenticatedUsers", []),
                    "authenticated_roles": info.get("authenticatedUserRoles", []),
                    "setup_guide": "docs/CHAPTER_12_SETUP.md",
                    "note": "Creating users/roles and enforcing authorization must be performed on an isolated test instance. This is not an RBAC permission test.",
                    "passed": None}
        finally:
            if owned:
                client.close()
    if lab == 2:
        uri = os.getenv("MONGO_TLS_URI")
        if not uri:
            return {"chapter": 12, "lab": 2, "mode": "requires-isolated-tls-instance",
                    "passed": None, "setup_guide": "docs/CHAPTER_12_SETUP.md",
                    "note": "Set MONGO_TLS_URI to a test TLS-enabled instance. Never use your production credentials."}
        ca_file = os.getenv("MONGO_TLS_CA_FILE")
        options = {"serverSelectionTimeoutMS": 5000, "tls": True}
        if ca_file:
            options["tlsCAFile"] = ca_file
        tls_client = MongoClient(uri, **options)
        try:
            tls_client.admin.command("ping")
            return {"chapter": 12, "lab": 2, "mode": "TLS ping",
                    "tls_connection_succeeded": True, "passed": True,
                    "note": "Only the positive TLS connection was tested; test non-TLS rejection separately."}
        finally:
            tls_client.close()
    raise ValueError("Unknown security lab")


RUNNERS = {
    (10, 1): bank_transfer,
    (10, 2): inventory_reservation,
    (11, 1): shard_key_evaluation,
    (11, 2): shard_key_hotspot,
    (12, 1): lambda: security_readiness(1),
    (12, 2): lambda: security_readiness(2),
}
