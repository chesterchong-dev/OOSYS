# OOSYS Phase 05 — Security, Observability & Recovery

**Status: In progress; not accepted until exact-commit CI, extended recovery-test CI and the required restore drill are evidenced.**

## Baseline

Phase 05 builds on the accepted Phase 00–04 baseline. The existing API already has a liveness endpoint, a database readiness probe, safe error envelopes, environment-backed settings, and a database-backed login-attempt limiter. Login attempts are persisted in PostgreSQL, keyed by HMAC digests, and PostgreSQL advisory transaction locks serialize concurrent checks across workers. The configured production environment requires `OOSYS_LOGIN_RATE_LIMIT_SECRET`.

This phase must not claim the database is ready when the probe fails, change the established `/health` or `/health/ready` response contracts, or expose dependency details.

## Requirement traceability

| Requirement | Baseline | Phase 05 change/evidence | Status |
|---|---|---|---|
| Structured logging and correlation IDs | No common access log/correlation middleware | JSON request logs, safe ID normalization and response header; tests added | Implemented; CI pending |
| Safe errors and sensitive-data redaction | Generic error envelope already exists | Access logs exclude query strings, bodies and headers; regression test added | Implemented; CI pending |
| Health/readiness | Existing liveness and DB SELECT 1 readiness | Preserved without contract/schema changes | Existing; regression suite pending |
| Secret/configuration safety | Environment-backed settings and production login secret requirement | Placeholder-only .env example; strict CORS origin validation | Implemented; CI pending |
| Rate limiting | DB-backed login limiter and per-account reset-request cooldown exist | No schema change; review reset-confirm/invitation abuse paths remains required | Partially implemented |
| Security headers/CORS | No central CORS middleware found in inspected composition root | Baseline headers; explicit origins only; bearer model and no credentials | Implemented; CI pending |
| Dependency/supply-chain checks | No audit workflow found at inspected paths | Added scheduled and PR/push pip-audit workflow | Implemented; scan result pending |
| Backup/restore | No tested restore evidence found | PostgreSQL backup/restore runbook documented | Partially implemented; real restore blocked |
| Incident runbooks | No Phase 05 runbook found | Startup/readiness, secret exposure, dependency, backup/restore and rate-limit runbooks | Implemented; review pending |
| Requirements/architecture traceability | Existing 87-row register/crosswalk referenced by Phase 03 | Phase 05 ADR and phase record added; source-node crosswalk reconciliation still pending | Partially implemented |

## Controls introduced

- Request correlation IDs are accepted only when they match a bounded safe character set; otherwise the API generates a UUID. IDs are returned in `X-Request-ID`.
- Request access logs are JSON structured and contain method, path (not query string), status, request ID and duration. Request bodies and headers are deliberately excluded.
- Baseline security response headers are added: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `Permissions-Policy`.
- CORS is disabled unless exact origins are configured using comma-separated `OOSYS_CORS_ALLOWED_ORIGINS`; wildcard origins and credentialed cross-origin requests are not supported. Bearer authorization remains the authentication model; do not add cookie authentication without a separate CSRF design review.
- `.env.example` contains placeholders only.
- A dependency audit workflow runs `pip-audit` against the installed dependency set on pull requests, selected branch pushes and a weekly schedule.

## Configuration and secrets

Use environment variables or a managed secret store in deployment. Never put actual credentials in `.env.example`, source control, issue comments or logs. In production, set a strong randomly generated `OOSYS_LOGIN_RATE_LIMIT_SECRET`; changing it invalidates the keyed rate-limit identifiers but does not delete attempt rows. Restrict environment and backup access to operators who need it. Avoid printing environment variables in diagnostic commands.

CORS example:
```sh
OOSYS_CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```
Origins must contain scheme and host only; do not include a path. Keep this empty for same-origin reverse-proxy hosting.

## PostgreSQL backup and restore runbook

Prerequisites: approved maintenance/recovery window, PostgreSQL client tools compatible with the server, access to the correct database, protected backup storage, and a separately configured **disposable restore database**. Never run the restore command against production as a test.

Create a custom-format backup (avoid embedding passwords in shell history):
```sh
pg_dump --format=custom --no-owner --file=oosys-$(date -u +%Y%m%dT%H%M%SZ).dump "$OOSYS_DATABASE_URL"
```
Restrict file permissions and transfer/store the artifact using the organisation's approved encrypted storage. Verify the artifact can be read:
```sh
pg_restore --list oosys-YYYYMMDDTHHMMSSZ.dump
```
Restore to a separately created empty disposable database, using a separately configured URL:
```sh
pg_restore --exit-on-error --no-owner --dbname="$OOSYS_RESTORE_DATABASE_URL" oosys-YYYYMMDDTHHMMSSZ.dump
```
Then verify the restored database is reachable, inspect the Alembic revision with `alembic current` configured for that database, run the application's migration compatibility checks and relevant read-only smoke tests. Compare expected table counts and representative non-sensitive records against the backup inventory. Do not run `alembic upgrade head` on a production database as part of a restore test. If the backup includes tenant/user data, treat the artifact as sensitive production data and preserve its access controls.

For a real incident: stop writes or place the service in maintenance mode if required by the recovery plan; preserve logs and the original database; restore to a new database/instance; verify migrations and critical data; point the application to the restored instance only after approval; validate readiness and critical user flows; document data-loss window and incident timeline. Escalate if backup integrity, credentials or recovery point cannot be established.

**Verification status:** No live database or disposable restore database was available through this repository-editing session. A real restore test is therefore blocked/unverified; the commands above are documented, not claimed as executed.

## Incident runbooks

### Startup or readiness failure
1. Check deployment logs and `GET /health` to distinguish process liveness from readiness.
2. Check `GET /health/ready`; it intentionally returns only `not_ready` on dependency failure.
3. Verify `OOSYS_DATABASE_URL` exists in the deployment secret configuration without printing its value; confirm DNS, network, TLS and database availability.
4. Check migration state using an authorised operator connection; do not auto-run migrations as a workaround.
5. Recover connectivity or roll back a verified configuration change, then confirm readiness and critical API flows.

### Suspected secret exposure
1. Treat the secret as compromised; preserve evidence and restrict access to affected logs/repositories.
2. Revoke/rotate the affected credential with its provider; update the managed secret store and redeploy.
3. Inspect access/audit logs for misuse, invalidate affected sessions/tokens where appropriate, and remove exposed artifacts from active branches without assuming history has been erased.
4. Verify old credentials no longer work and document scope, impact and notification obligations.

### Dependency vulnerability
1. Capture the scanner report, package/version, exploitability and reachable code path.
2. Reproduce in an isolated environment and identify the narrowest compatible patched version.
3. Update dependency constraints deliberately, run tests/build/migration checks and review transitive changes.
4. If no safe patch exists, document mitigation, owner and review date; do not suppress findings silently.

### Backup or restore failure
1. Stop treating the failed artifact as recoverable; preserve it for diagnosis.
2. Check exit code, free space, tool/server compatibility, permissions and database target.
3. Retry only against a fresh disposable target after correcting the cause; never overwrite production during a drill.
4. Verify data and migration state before authorising recovery. Escalate if the recovery point cannot be proven.

### Rate limiting or security-control issue
1. Confirm repeated login attempts, status codes and application/DB health without collecting passwords or bearer tokens.
2. Check database availability, attempt-table growth, production rate-limit secret configuration and trusted proxy/IP behavior.
3. Do not bypass limits globally. Apply a scoped mitigation, verify legitimate login still works, and test across multiple workers using PostgreSQL.
4. Escalate if abuse persists or the control can be evaded.

## Remaining verification gates

- Full backend and frontend CI run [39791287085](https://github.com/chesterchong-dev/OOSYS/actions/runs/39791287085) passed on candidate `d51530d050cf25e0605cf1ea28905b588973c962` (57 passed, 1 failed, 2 skipped; first run's log-test failure was corrected afterward). Dependency audit run [39792499218](https://github.com/chesterchong-dev/OOSYS/actions/runs/39792499218) passed on candidate `b3d9320e8a3fc6809ccca40e68555a46dcaa8c63` after upgrading the pytest constraint. The newer recovery-test additions still require a completed exact-HEAD validation run.
- Verify database-backed login rate limiting across concurrent PostgreSQL workers and review token/recovery endpoints for equivalent abuse protection.
- Dependency audit run [39792499218](https://github.com/chesterchong-dev/OOSYS/actions/runs/39792499218) passed. Earlier run [39790464814](https://github.com/chesterchong-dev/OOSYS/actions/runs/39790464814) identified `pytest 8.4.2` / `PYSEC-2026-1845`; dependency constraint now requires `pytest>=9.0.3,<10.0`. Continue reviewing future scanner output; do not suppress advisories.
- Perform an actual backup restore in a disposable PostgreSQL database and record the evidence.
- Reconcile the 87-row requirements register and source-node crosswalk, and verify the master roadmap and two original XMind maps before marking acceptance. The XMind references were not readable by the repository tools during this work; do not silently infer source-node mappings.
