# OOSYS Phase 05 — Security, Observability & Recovery

**Status: Partially complete; not accepted as fully production-ready.** On current verified documentation candidate `e7b56bd75ea0718a3a2d11f0800ffbaa4c160522`, Phase 00 validation run 39800827099 passed backend and frontend jobs, Dependency Audit run 39800827064 passed, and Secret Scan run 39800827144 passed. The requirements-register follow-up is a documentation-only commit; verify checks on the latest final HEAD before acceptance. Production-equivalent recovery, central alert delivery, staged release/rollback and independent security review remain unverified.

## Baseline inspected

Phase 05 continues the accepted Phase 00–04 baseline and preserves its API/database contracts. Before changes, the repository already had:
- `GET /health` liveness, without dependency checks.
- `GET /health/ready` database readiness via `SELECT 1`, with a generic 503 failure response.
- A stable safe error envelope in `app/api/errors.py`.
- Environment-backed Pydantic settings, including production validation for `OOSYS_LOGIN_RATE_LIMIT_SECRET`.
- Database-backed login failure throttling with keyed email/IP identifiers and PostgreSQL advisory transaction locks.
- Password-reset requests throttled per account, hashed reset/invitation tokens, expiry and revocation, single-use confirmation using row locking, session revocation and invitation email/tenant checks.

The phase deliberately keeps liveness and readiness response bodies unchanged, does not run migrations at startup, and introduces no database schema migration.

## Requirement traceability matrix

| Requirement | Change / verification evidence | Status |
|---|---|---|
| Structured logs and request correlation | `app/core/observability.py` emits JSON method/path/status/request-id/duration logs. Query strings, headers and bodies are excluded. Unsafe IDs are replaced; the normalized ID is returned and passed downstream. `tests/test_observability.py` verifies propagation and redaction. | Implemented; backend CI passed |
| Safe unexpected errors | Existing generic HTTP 500 contract retained. No exception strings or sensitive header/body data are put in the request log. Earlier logger-capture test failure was fixed by spying on the logger deterministically. | Implemented; backend CI passed |
| Health and readiness | Existing `/health` and `/health/ready` contract preserved; readiness continues to return 503 on unavailable/unconfigured database. | Existing, regression CI passed |
| Metrics hooks | Bounded process-local counters/duration aggregates; no path, tenant, query or user labels. `/metrics` hidden and disabled by default; token-gated with constant-time compare and minimum token length when enabled. Tests verify disabled-by-default, token denial, and aggregate labels. | Implemented; backend CI passed; production metrics topology not verified |
| Secret/configuration validation | Placeholder-only `.env.example`; CORS wildcard/path rejected; production requires a nonempty rate-limit secret; metrics token required if metrics enabled. | Implemented; backend CI passed |
| Rate limiting and recovery abuse | Login failure limit remains database-backed with PostgreSQL lock serialization. Reset-request cooldown, expired/unknown/used reset-token tests, session revocation, invitation email-mismatch/replay/revocation/expiry/wrong-organization tests, and PostgreSQL one-time-token concurrency test are present. | Implemented for current identity flows; CI passed |
| CORS and headers | Explicit-origin allowlist; no wildcard or credentialed CORS; bearer auth remains cookie-free. `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` added. | Implemented; backend CI passed |
| Dependency/supply-chain | `pip-audit` workflow added. First scan found `pytest 8.4.2` / `PYSEC-2026-1845`; constraint updated to `pytest>=9.0.3,<10.0`, without suppressions. Current candidate audit run 39799962614 completed successfully. | Implemented; audit passed |
| Secret scanning | Gitleaks workflow scans repository history; prior run 39794403938 passed with “no leaks found”. Current candidate run 39799963011 has been created but remains queued/incomplete at last inspection. | Implemented; exact-head scan pending |
| PostgreSQL backup/restore | Workflow dumps only the ephemeral CI PostgreSQL 16 database with custom format, lists the archive, restores to a separate disposable target, compares Alembic revision, sentinel value and identity-user row count, then tears down. On latest candidate, run 39799962837: backup/restore step completed successfully. | CI restore drill verified on candidate; production-equivalent recovery remains partial |
| Incident runbooks | Startup/readiness, suspected secret exposure, vulnerability, backup/restore and rate-limit incident guidance documented below. | Implemented; operational rehearsal not performed |
| Source traceability | Master product map, Developer Implementation Blueprint, 23-phase roadmap, 87-row requirements register and 87-row UUID crosswalk are in repository/connected XMind records. Relevant canonical rows include CORE-002, CORE-006, CORE-011, CORE-012, CORE-014, CORE-015, OPS-085 and OPS-087. Mapping classifications remain unchanged. | Source mapping available; broader product requirements remain partial/missing as recorded in the register |

## CI evidence for current candidate

Phase 05 branch head: `342e5f6fe161dd0ee636db69912cb6e810f819f0`.

- **Phase 00 validation**, run [39800827099](https://github.com/chesterchong-dev/OOSYS/actions/runs/39800827099), on `e7b56bd75ea0718a3a2d11f0800ffbaa4c160522`: both backend and frontend jobs passed. The backend test command `python -m pytest -q --cov=app.identity --cov=app.api.operations --cov-report=term-missing` reported **65 passed, 2 skipped, 92% total configured coverage**. PostgreSQL recovery-token concurrency tests reported **2 passed**. SQLite migration upgrade/downgrade, PostgreSQL migration/persistence/RLS probes, the disposable PostgreSQL backup/restore step, PostgreSQL downgrade and compileall passed. Frontend unit tests and Vite production build passed.
- **Dependency Audit**, run [39800827064](https://github.com/chesterchong-dev/OOSYS/actions/runs/39800827064), on `e7b56bd75ea0718a3a2d11f0800ffbaa4c160522`: passed. The scan installed pytest 9.1.1. The earlier `PYSEC-2026-1845` finding against pytest 8.4.2 was addressed by setting `pytest>=9.0.3,<10.0`; no audit suppression was added.
- **Secret Scan**, run [39800827144](https://github.com/chesterchong-dev/OOSYS/actions/runs/39800827144), on `e7b56bd75ea0718a3a2d11f0800ffbaa4c160522`: passed; the Gitleaks scan step completed successfully.
- Earlier candidate scan [39794403938](https://github.com/chesterchong-dev/OOSYS/actions/runs/39794403938) also passed and logged “28 commits scanned” / “no leaks found”. The current-head evidence is the run above.
- **Earlier dependency audit** run [39790464814](https://github.com/chesterchong-dev/OOSYS/actions/runs/39790464814) failed on pytest 8.4.2 / `PYSEC-2026-1845`. The dependency constraint was changed to `pytest>=9.0.3,<10.0` without suppression; current-head audit run 39800827064 passed.
- **Earlier observability test failure** run [39790464759](https://github.com/chesterchong-dev/OOSYS/actions/runs/39790464759): log capture via pytest caplog yielded no entries in the ASGI middleware context. Test was revised to spy directly on the structured logger. A later candidate failed a different negative test because its “invalid token” was shorter than the schema's 32-character minimum, so it received 422 before the handler while the test expected 400. The test now sends a 32-character unknown token, preserving the schema/API contract and actually exercising handler-level invalid-token rejection. Current backend CI passed.

The CI restore drill uses only generated test data in its ephemeral PostgreSQL service. It is real evidence for archive/restore and checked data integrity in that disposable environment; it is not evidence of production retention, restore-point objectives, full RPO/RTO, encrypted off-site backup, or recovery of a production system.

## PostgreSQL backup/restore drill details

In run 39799962837, the following workflow step concluded success on candidate `342e5f6fe161dd0ee636db69912cb6e810f819f0`:
1. Dumped the CI-only source database into a permission-restricted custom-format backup.
2. Verified the backup archive could be listed.
3. Restored into a separately created `oosys_restore_target` disposable database.
4. Compared the Alembic version/revision, the `ci.persistence.probe` sentinel value and identity-user row counts between source and restored databases.
5. Completed later PostgreSQL downgrade and CI cleanup steps successfully.

No production database or credentials were used in the drill. A production-equivalent restore rehearsal, RPO/RTO test and backup-retention/off-site storage verification remain unperformed and outside this evidence.

## Architecture and compatibility notes

- No migration was required; no schema was changed.
- `/health` liveness and `/health/ready` readiness response bodies remain unchanged.
- `/metrics` is not in the OpenAPI schema, is disabled by default, and returns 404 when disabled or unauthenticated. It exposes only low-cardinality aggregate method/status metrics; counters are process-local and do not by themselves provide cross-worker aggregation.
- CORS remains disabled unless explicit origins are configured. Cookie auth/CSRF behavior has not been introduced; browser auth is bearer-token based. Reverse proxy TLS, CSP, trusted proxy configuration and deployment-level CSRF policy remain deployment review items.
- A dedicated type checker/linter and external penetration test/security certification are not represented as passed or performed.
- The runbook does not claim mail, object storage, search, AI, or external integrations are ready based on database readiness.

## Incident runbooks

### Startup or readiness failure
1. Check deployment logs and `GET /health` to distinguish process liveness from readiness.
2. Check `GET /health/ready`; this endpoint intentionally returns only `not_ready` on dependency failure.
3. Verify that `OOSYS_DATABASE_URL` is present in deployment secret configuration without printing its value; confirm DNS, network, TLS and database availability.
4. Check migration state with an authorised operator connection; do not run migrations automatically as a workaround.
5. Restore connectivity or roll back a verified configuration change, then confirm readiness and critical API flows.

### Suspected secret exposure
1. Treat the secret as compromised; preserve evidence and restrict access to affected logs/repositories.
2. Revoke/rotate the credential with its provider; update the secret store and redeploy.
3. Inspect audit logs for misuse, invalidate affected sessions/tokens where appropriate, and remove exposed artifacts from active branches without assuming that history is erased.
4. Confirm old credentials no longer work and document impact and notification obligations.

### Dependency vulnerability
1. Capture package/version, scanner report, exploitability and reachable code path.
2. Identify the narrowest compatible patched version and update constraints deliberately.
3. Run audit, tests, migration checks and builds, and review transitive dependency changes.
4. If no safe patch exists, document mitigation, an owner and a review date; do not suppress findings silently.

### Backup/restore failure
1. Stop treating the failed artifact as recoverable; preserve it for diagnosis.
2. Check exit code, disk space, tool/server compatibility, permissions and target database.
3. Retry only against a fresh disposable target after correcting the cause; never overwrite production during a drill.
4. Verify data and migration state before authorising recovery. Escalate if the recovery point cannot be established.

### Rate-limiting or security-control issue
1. Confirm repeated failures, response codes and application/database health without collecting passwords or bearer tokens.
2. Check database availability, attempt-table growth, rate-limit secret configuration and trusted proxy/IP behavior.
3. Do not bypass limits globally. Apply a scoped mitigation and verify that legitimate login still works.
4. Test concurrent behavior against PostgreSQL and escalate if abuse persists.

## Remaining acceptance gates

- The most recent checked Phase 05 documentation candidate was `e7b56bd75ea0718a3a2d11f0800ffbaa4c160522`; Phase 00 validation run 39800827099, Dependency Audit run 39800827064, and Secret Scan run 39800827144 all passed on that SHA. The requirements-register and narrative follow-up commits are documentation-only; verify checks against the final branch HEAD before acceptance.
- Production-equivalent restore, backup retention/access-control review, recovery objectives and alert delivery remain partial/unverified; the verified restore is an automated CI drill using synthetic data in a disposable PostgreSQL 16 service.
- Process-local metrics are implemented, but a central metrics backend and operational alert routing are not configured in this phase.
- Dedicated type-check/lint jobs, staged deployment/rollback controls and an independent penetration test are not configured or completed.
- The overall OOSYS product is not production-ready; future tenant/business-domain RLS, module authorization and broader release hardening remain subject to their owning requirements and phases.