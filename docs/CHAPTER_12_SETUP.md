# Chapter 12: Authentication/RBAC and TLS — isolated lab only

**No external dataset is required.** Chapter 12 uses test users, roles and certificates. Never run privilege-management experiments against your real CTI Sentinel database or an Atlas production cluster.

The dashboard currently performs **read-only readiness checks**. The checks do not claim to have completed the whole RBAC or TLS assignment.

## Lab 12.1 — RBAC

1. Create a separate local MongoDB instance on a different port (for example, 27021), with authentication enabled and a randomly generated administrator password. Docker's `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` can bootstrap an isolated test instance; use a local `.env` file, not a committed password.
2. Connect with `mongosh` as the test administrator and create a test database such as `cti_rbac_lab` with a few **synthetic** documents.
3. Create two roles/users in the test database: an analyst with `read`, and an application writer with `readWrite`. Generate strong unique passwords; do not reuse your Atlas credentials.
4. Verify that the analyst can query test documents but cannot insert, update or delete them; verify that the writer can update test documents. Record expected authorization errors as evidence of enforcement.
5. In the dashboard, **Check setup** for Lab 12.1 reports the authenticated identity and roles of the configured `MONGO_LABS_URI` connection. To inspect the RBAC test instance, point that variable at the *isolated* instance using its credentials, and restart the backend. This is an inspection only, not the full permission test.

## Lab 12.2 — TLS

1. Use a separate MongoDB test instance, not your primary database. Create a local CA and server certificate with OpenSSL. Include a Subject Alternative Name matching the host you will connect to, e.g. `localhost`.
2. Start that instance with `--tlsMode requireTLS`, `--tlsCertificateKeyFile` pointing at the server key+certificate PEM, and `--tlsCAFile` pointing at the CA certificate. Restrict the port to localhost.
3. Attempt a connection *without* TLS and confirm it is rejected. Then connect with `mongosh --tls --tlsCAFile <path-to-ca.crt>` and confirm `db.adminCommand({ping:1})` succeeds.
4. Configure `MONGO_TLS_URI` and `MONGO_TLS_CA_FILE` in `.env` to point to this isolated test instance, then use **Check setup** in the dashboard. It verifies that a TLS-enabled PyMongo connection can ping the server. It does **not** independently test that plaintext connections are rejected.
5. Never disable hostname verification in a real deployment. Do not commit CA private keys, server keys, PEM files, passwords or connection strings containing secrets.

## What to include in the lab report

- Lab 12.1: created roles and their allowed operations; evidence of a denied write by the analyst and a successful authorized write.
- Lab 12.2: TLS-required configuration, rejected non-TLS connection, successful TLS connection, and certificate verification method.

These are **manual environment-dependent experiments**. Do not report successful completion until you run and capture the evidence.
