# OOSYS Phase 05 — Security, Observability & Recovery

**Status: In Progress; Phase 05 is not accepted as fully production-ready.**  
**Application/test evidence checkpoint:** code HEAD `555371277428a2ea6736c520b434f4d2c23e00a2`. Phase 00 validation [run 39965923995](https://github.com/chesterchong-dev/OOSYS/actions/runs/39965923995), Dependency Audit [run 39965924051](https://github.com/chesterchong-dev/OOSYS/actions/runs/39965924051), and Secret Scan [run 39965924064](https://github.com/chesterchong-dev/OOSYS/actions/runs/39965924064) all passed on this exact code SHA. Backend suite: **83 passed, 2 skipped**, configured total coverage **92.46%** (90% threshold). PostgreSQL recovery-token concurrency: **2 passed**. SQLite and PostgreSQL migration lifecycle/persistence checks, PostgreSQL downgrade, compileall and disposable restore drill passed; restore evidence reports migration `20261018_0006`, 5 identity users and sentinel `"ok"`. Frontend: 3 test files, **8 tests passed**, production build succeeded. Dependency audit and full-history secret scan passed. The added CORS validation tests cover empty query/fragment delimiters, credentials, malformed/whitespace/underscore hostnames, invalid/empty/out-of-range ports, non-HTTP schemes, malformed IPv6 and accepted IPv4/IPv6 origins. Non-failing dependency/runtime deprecation warnings remain maintenance debt. This evidence is repository CI only, not production operations or independent security assurance.

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

Phase 05 branch HEAD tested: `dd1c72665f4a7af03f587d3efd39d80eef7351aa`. The Phase 00 validation workflow checked out PR merge commit `e2a58fa1d5fd0fe1a54867f3ab132448d198ceff`, which is the merge of that branch head into base `81839b7e0b5608404a5cacfbeb97c845d513e302`.

- **Phase 00 validation**, run [39805260559](https://github.com/chesterchong-dev/OOSYS/actions/runs/39805260559): overall result **success**. Backend: `68 passed, 2 skipped, 1 warning`; configured coverage **93% total**, with `app/core/config.py` **100%** (45 statements), `app/core/metrics.py` **100%** (28 statements), and `app/core/observability.py` **100%** (47 statements). The CI command was `python -m pytest -q --cov=app.identity --cov=app.api.operations --cov=app.core.config --cov=app.core.observability --cov=app.core.metrics --cov-report=term-missing --cov-fail-under=90`. Frontend unit tests and Vite build passed. SQLite migration upgrade/downgrade, PostgreSQL migration/persistence/RLS probes, PostgreSQL recovery-token concurrency (**2 passed**), disposable PostgreSQL backup/restore, PostgreSQL downgrade and `python -m compileall -q app migrations tests` all passed.
- **Backup/restore drill evidence** from run 39805260559: `Backup/restore drill passed: migration=20261018_0006; identity_users=5; sentinel="ok"`. `pg_dump` wrote a custom-format backup from the ephemeral PostgreSQL 16 CI database; `pg_restore --list` validated the archive; the archive was restored to a separately created disposable database; the Alembic revision, sentinel data and identity-user count were compared; cleanup dropped the target. This is a genuine restore test using generated CI data, not production data.
- **Dependency Audit**, run [39805260653](https://github.com/chesterchong-dev/OOSYS/actions/runs/39805260653): success on branch HEAD `dd1c72665f4a7af03f587d3efd39d80eef7351aa`. `pytest>=9.0.3,<10.0` installs pytest 9.1.1. Earlier `PYSEC-2026-1845` on pytest 8.4.2 was addressed by an explicit version constraint; no suppression was added.
- **Secret Scan**, run [39805260563](https://github.com/chesterchong-dev/OOSYS/actions/runs/39805260563): success on the same branch HEAD. Gitleaks reported 28 commits scanned and no leaks found.
- **Earlier failure causes and fixes:** run 39790464759's log-redaction test used caplog against ASGI middleware, where no records were captured; the test now spies on the logger directly and asserts query/authorization secrets are omitted. A negative password-reset test used a token shorter than the schema's 32-character minimum and expected handler status 400; it now uses a 32-character unknown token so the request passes schema validation and exercises handler-level invalid-token rejection, preserving the API schema. Audit run 39790464814 found `PYSEC-2026-1845` on pytest 8.4.2; the dependency constraint was updated and the subsequent audit passed.

The CI restore is verified only for synthetic data in a disposable PostgreSQL 16 service. It does not establish production backup retention, encrypted/off-site storage, recovery-point/recovery-time objectives, or recovery of a production deployment. The report above distinguishes that limitation from the verified CI restore.
## PostgreSQL backup/restore drill details

The exact tested candidate's backup/restore evidence is documented under [Phase 00 validation run 39805260559](https://github.com/chesterchong-dev/OOSYS/actions/runs/39805260559) and branch HEAD `dd1c72665f4a7af03f587d3efd39d80eef7351aa`.

The workflow:
1. Dumped the ephemeral PostgreSQL 16 CI source database into a custom-format archive stored in a runner temporary file.
2. Verified the archive with `pg_restore --list`.
3. Restored the archive into a separately created disposable `oosys_restore_target` database.
4. Compared the Alembic revision, a `ci.persistence.probe` sentinel, and identity-user row counts between source and restored databases.
5. Reported `Backup/restore drill passed: migration=20261018_0006; identity_users=5; sentinel="ok"`.
6. Completed the PostgreSQL downgrade and CI cleanup steps successfully.

Only generated CI test data was used. No production database or production credentials were used. This proves the tested backup/archive/restore path and the stated data-integrity checks in an isolated environment; it does not prove production backup retention, encrypted/off-site storage, recovery-point/recovery-time objectives, or a production-system recovery rehearsal.

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

- The tested branch head is `dd1c72665f4a7af03f587d3efd39d80eef7351aa`. Phase 00 validation run 39805260559, Dependency Audit run 39805260653 and Secret Scan run 39805260563 all passed on that candidate (the Phase 00 workflow tests its GitHub-generated PR merge commit noted above).
- Requirements traceability was reconciled with the connected Master Development Roadmap (23 phases), the original OOSYS product map, the Developer Implementation Blueprint, the 87-row requirements register and the source-node crosswalk. The roadmap defines this phase’s scope as logging/correlation, liveness/readiness consistency and metrics hooks; secret boundaries/rate limits/security headers/CORS review; dependency and secret scans; and a documented/tested restore plus incident runbooks. The roadmap's “Not started” note was stale when this work began; scoped implementation/CI evidence is now recorded. Phase 05 remains In Progress because production-like recovery/monitoring and release safeguards are not proven.
- Production-equivalent restore, encrypted/off-site backup, retention/access-control review, recovery objectives and alert delivery remain partial/unverified. The verified restore is a disposable PostgreSQL CI drill using synthetic records.
- Metrics counters are process-local with bounded labels; central aggregation, alert delivery and operational rehearsal are not configured. Dedicated type-check/lint jobs, staged deployment/rollback controls and independent penetration testing are not configured or completed.
- `CORE-011`, `CORE-012`, `CORE-014`, `CORE-015`, `OPS-085` and `OPS-087` remain partial where their broader product requirements exceed the verified Phase 05 slice. No database migration was required; `/health` and `/health/ready` response contracts remain unchanged. OOSYS is not production-ready.

## Latest current-head verification and operational acceptance plan

Implementation verification checkpoint: `8087430ff1f268658a6950318f9b14e273f23c61`. Subsequent commits added operational acceptance documentation and requirements/README reconciliation; exact-head CI for the final documentation commit is a separate acceptance check.

- Phase 00 validation [39807993423](https://github.com/chesterchong-dev/OOSYS/actions/runs/39807993423): workflow and both jobs passed. The backend job passed test execution, SQLite migration upgrade/downgrade, PostgreSQL migration/persistence/RLS checks, PostgreSQL recovery-token concurrency, disposable PostgreSQL backup/restore, PostgreSQL downgrade and compileall. The frontend test and production build job passed.
- Dependency Audit [39807993312](https://github.com/chesterchong-dev/OOSYS/actions/runs/39807993312): audit step passed.
- Secret Scan [39807993363](https://github.com/chesterchong-dev/OOSYS/actions/runs/39807993363): Gitleaks scan step passed.
- The implementation verification checkpoint is documentation-only relative to the preceding implementation candidate. Workflow results establish CI status for that checkpoint; detailed test counts and coverage figures documented above remain attributed to their stated implementation candidate and must not be reattributed without reading the corresponding run output. Subsequent documentation-only commits must have their own successful exact-head CI before final acceptance.
- The password-reset negative test retains the schema's 32-character minimum and tests an unknown token that passes schema validation, so handler-level invalid-token behavior is tested without weakening the 422 schema-validation contract.
- The earlier dependency finding `PYSEC-2026-1845` was addressed with `pytest>=9.0.3,<10.0`; the current-head dependency audit passed.

The new [Phase 05 Operational Acceptance Plan](./PHASE_05_OPERATIONAL_ACCEPTANCE_PLAN.md) defines the proposed production backup policy, proposed RPO/RTO targets, central metrics/alert acceptance, staged release/rollback rehearsal, penetration-test scope, blockers and required evidence. These are acceptance criteria and proposals, not claims that production infrastructure is configured. RPO/RTO targets require product-owner approval; backup/metrics/deployment and independent penetration-test evidence remain blocked on the corresponding environment, operator and authorization.

Requirements `OOSYS-CORE-012`, `OOSYS-CORE-014`, `OOSYS-CORE-015`, `OOSYS-OPS-085` and `OOSYS-OPS-087` remain `partial` for their broader product requirements. Their UUID mappings and classifications are checked against `docs/requirements/REQUIREMENT_SOURCE_NODE_CROSSWALK.csv`. Do not mark Phase 05 accepted until the operational gates are evidenced and the PR is reviewed.


## Current intended-head CI verification — 2026-10-23

The prior sections contain historical implementation checkpoints. At the start of the latest acceptance review, the intended PR head was `6bf79bcb1a729fa6df56f6b5f8f07c2fb1e3f825`. GitHub's commit-scoped workflow lookup returned completed successful runs for that SHA:

- Phase 00 validation [39960204359](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960204359): backend and frontend jobs succeeded. The backend steps for tests, SQLite migration upgrade/downgrade, PostgreSQL migration/persistence, recovery-token concurrency, disposable PostgreSQL backup/restore, PostgreSQL downgrade and compileall all completed successfully; frontend unit tests and production build succeeded.
- Dependency Audit [39960204581](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960204581): pip-audit succeeded.
- Secret Scan [39960204464](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960204464): Gitleaks succeeded.

The separate combined-status endpoint had no status entries; conclusions above come from the commit-scoped workflow runs and completed jobs. Any subsequent commit requires exact-head verification. CI results do not establish production backup, central monitoring, staged deployment/rollback or independent penetration-test completion. Requirements CORE-012, CORE-014, CORE-015, OPS-085 and OPS-087 remain partial.


## Follow-up exact-head CI result — documentation HEAD b80148e6f6c9bfe3409a2b7a82600191e78cbdaa

The pending Phase 00 validation result has now completed successfully on exact SHA `b80148e6f6c9bfe3409a2b7a82600191e78cbdaa`:

- Phase 00 validation [39960856737](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960856737): backend and frontend jobs succeeded. Backend steps for tests, SQLite migration lifecycle, PostgreSQL migration/persistence, recovery-token concurrency, disposable PostgreSQL backup/restore, PostgreSQL downgrade and compileall succeeded; frontend unit tests and production build succeeded.
- Dependency Audit [39960856880](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960856880): succeeded.
- Secret Scan [39960856652](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960856652): succeeded.

This verifies the documentation HEAD stated above. The following documentation-only commit changes the HEAD and must receive its own exact-head workflow verification. No new application code or local test execution occurred in this continuation. Production operations and independent penetration testing remain unverified; all five broad requirements remain partial.


## Exact-head CI reconciliation and remaining acceptance blockers — 2026-10-23

At PR head `5a690acfdc5096bdec31497f6ea9e25fe6a29505`, live commit-scoped workflow records confirm:
- Phase 00 validation [39961354573](https://github.com/chesterchong-dev/OOSYS/actions/runs/39961354573) — success; backend and frontend jobs passed. Backend included tests, SQLite migration lifecycle, PostgreSQL migration/persistence, recovery-token concurrency, disposable PostgreSQL restore, PostgreSQL downgrade and compileall; frontend tests and production build passed.
- Dependency Audit [39961354869](https://github.com/chesterchong-dev/OOSYS/actions/runs/39961354869) — success.
- Secret Scan [39961354686](https://github.com/chesterchong-dev/OOSYS/actions/runs/39961354686) — success.

The previous pending note for Phase 00 validation at this SHA is superseded. CI success is not proof of production readiness. The PR remains open and draft.

Acceptance gaps remain partial:
- CORE-012: central collection, actionable alert routing, missing-telemetry detection and end-to-end alert receipt/acknowledgement/resolution need a platform/operations owner, selected destination, authorized access and verified delivery evidence.
- CORE-014: production backup controls and measured recovery need product-owner approval of retention/data residency/RPO/RTO, database/platform configuration and an isolated timed restore with integrity/access-control evidence.
- CORE-015: independent penetration testing needs authorized scope/tester, report, remediation/retest and risk-owner disposition.
- OPS-085: incident response needs a named on-call receiver, alert lifecycle evidence and timed recovery rehearsal.
- OPS-087: release controls need staging, immutable artifact provenance, promotion approvals, rollback triggers and an executed rollback rehearsal.
- RPO ≤15 minutes and RTO ≤4 hours are proposed targets only until approved and measured.

No shared API/database/permission/event contract changed. No database migration was introduced. The CI restore uses synthetic data in a disposable database and does not close production recovery gaps.
