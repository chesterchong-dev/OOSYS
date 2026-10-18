# OOSYS Known Limitations — Phase 00 Baseline and Phase 01 Progress

## Repository and implementation

- The development branch remains a starter scaffold, not the full OOSYS product.
- app/main.py provides the root and liveness endpoints plus a composition root. The versioned API router is currently empty; no business endpoints are registered under /api/v1.
- Authentication, session expiry/revocation, RBAC, tenant enforcement, business repositories/domain services, live PostgreSQL integration, frontend and deployment manifests are not implemented. Alembic and an initial `platform_settings` migration now exist; this is only a deployment-wide non-secret configuration foundation, not a settings CRUD module or tenant settings implementation. A lazy SQLAlchemy engine/session factory and safe API error contract do not substitute for domain persistence or authentication.
- Requirements statuses remain 84 missing and 3 partial; source-map traceability does not mean the requirements are implemented.
- Canonical planning boundaries are recorded in docs/architecture/DOMAIN_OWNERSHIP.md and ADR-0002. MRP owns material/demand planning and planned requirements/schedules; CRM owns customer pipeline forecasting; Procurement owns purchasing execution; Manufacturing Execution owns actual production. Detailed domain schemas and APIs remain unimplemented.

## Verification

- Earlier Phase 00 checkpoint: CI run [39093554503](https://github.com/chesterchong-dev/OOSYS/actions/runs/39093554503) passed against exact SHA 113e47434bf87fc6881cb9afb8af2857202c55cd (1 test passed; compileall passed). This is historical evidence only.
- Database lifecycle checkpoint: CI run [39095937584](https://github.com/chesterchong-dev/OOSYS/actions/runs/39095937584) passed against exact SHA 7b196c8692f0a7459cd8d86ffc3dcf2763e3cbf7. It ran Python 3.12, installed declared dependencies, reported 12 passed in 0.75s, and completed compileall successfully. This includes four tests for explicit database configuration, no network connection during PostgreSQL engine construction, SQLite session use, and rollback on a use-case exception. No live PostgreSQL or migration test was run.
- Phase 01 test-fix checkpoint: CI run [39095505280](https://github.com/chesterchong-dev/OOSYS/actions/runs/39095505280) passed against exact SHA 24de54bcf573c1179df8e7855d4060af1cc33b35 (8 tests passed, no pytest warnings; compileall passed).
- Latest full-workflow checkpoint before the final evidence-log update: CI run [39095605637](https://github.com/chesterchong-dev/OOSYS/actions/runs/39095605637) passed against exact SHA 741bc34abf76633e7c9c2510e56de472b9732b7d. It checked out the real repository on Python 3.12.15, installed declared dependencies (including FastAPI 0.143.3, Starlette 1.8.0 and HTTPX 0.28.1), ran pytest (8 passed, no pytest warnings), and ran compileall successfully.
- The test suite uses HTTPX ASGITransport rather than Starlette TestClient, avoiding the observed Starlette/httpx deprecation warning without adding an unneeded dependency or pinning framework versions solely to hide the warning.
- Exact-HEAD verification: run [39097211785](https://github.com/chesterchong-dev/OOSYS/actions/runs/39097211785) passed against SHA `1405e8dbcbd6c0d5b941c5be3723c7cf1246ca5c` (22 pytest tests, SQLite migration upgrade/downgrade and compileall passed; six Alembic path-separator deprecation warnings were observed). The warning was addressed by setting `path_separator = os` in `alembic.ini`. Follow-up run [39104149009](https://github.com/chesterchong-dev/OOSYS/actions/runs/39104149009) passed against exact SHA `6463706380a7d389f7618ada4bb521c58862b640` after that fix; tests, SQLite migration upgrade/downgrade and compileall all passed. This does not verify later commits; any subsequent commit needs its own exact-SHA CI check before sign-off.
- The workflow runs `python -m pytest -q`, Alembic upgrade/downgrade smoke checks on isolated SQLite, and `python -m compileall -q app migrations tests` on Python 3.12. The database lifecycle foundation adds tests for SQLite session use, missing database configuration, rollback, and PostgreSQL engine construction without a socket connection. CI does not currently run lint, type checks, coverage, dependency vulnerability scanning, frontend build, live PostgreSQL integration, or dedicated security scanning. It does run Alembic upgrade/downgrade smoke checks against SQLite.
- API error contract tests cover 404, arbitrary HTTP exceptions, request validation, expected application errors and unexpected exceptions, including checks that rejected input and internal exception text are not echoed. Migration tests cover clean SQLite creation, repeat upgrade, schema constraints, downgrade/re-upgrade and missing URL. These tests passed as part of the exact-HEAD run [39097211785](https://github.com/chesterchong-dev/OOSYS/actions/runs/39097211785).
- No live PostgreSQL migration/integration, coverage report, lint/type check, frontend build, dynamic security scan, dependency vulnerability scan, deployment check or end-to-end test has been performed. SQLite migration success must not be represented as PostgreSQL verification. Phase 01 is accepted only as the architecture/governance foundation; these gaps remain explicit and must be closed in the appropriate module/release gates before production readiness.
- The verification commits are unsigned/unverified; branch protection was recorded as disabled during the prior audit. Repository protection settings were not changed during this work. Keep development changes on the development branch and protect main through repository rules.

## Product traceability

- The connected master product map OOSYS — Only One System has 198 topics.
- The connected Developer Implementation Blueprint has four sheets with 143, 173, 132 and 181 topics (629 total).
- The register and source crosswalk each contain 87 requirement IDs; the crosswalk has 15 exact-title mappings, 37 normalized semantic-feature mappings, 32 semantic-parent mappings and 3 duplicate-title disambiguations. No unresolved proxy-gap or partial-coverage classification remains in the current crosswalk.
- CRM/sales/order/marketing, MRP/ERP/manufacturing, QMS, workflow/approval and project-tracking responsibilities overlap across the source maps. Proposed ownership is documented but not approved as a final product decision.

## Security posture

- App construction and basic liveness are tested without opening network sockets; this is a narrow isolation check, not a security assessment.
- No dynamic penetration test or dependency vulnerability scan has been performed.
- The scaffold must not be described as secure or production-ready. Implement and verify authentication, authorization, tenant isolation, rate limiting, audit events, migrations and designated security checks in their assigned phases.
