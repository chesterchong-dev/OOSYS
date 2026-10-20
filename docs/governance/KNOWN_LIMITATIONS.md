# OOSYS Known Limitations — Phase 03 Foundation Review

## Repository and implementation
- The development branch is a partial platform foundation, not the full OOSYS product.
- Phase 00–02 are accepted for their explicitly scoped criteria; see phase-specific evidence documents.
- Phase 03 adds database readiness at GET /health/ready; it only checks a configured database using SELECT 1. It does not prove migrations are current or validate mail, storage, search, integrations, AI, business workflows or production topology.
- /health remains liveness-only and makes no dependency calls.
- platform_settings remains deployment-wide non-secret storage, not tenant/user settings CRUD. Do not store secrets in this table.
- Shared audit/compliance, notifications, file service, global search, tenant settings CRUD, subscription/entitlements, workflow engine, integration framework, shared AI, frontend and deployment manifests remain unimplemented or only represented by narrow adapter boundaries.
- Business repositories, frontend and production deployment remain unimplemented.
- PostgreSQL CI probes are focused integration checks, not production deployment verification or full business persistence tests.

## Verification limitations
- Phase 03 code changes must be verified by CI against their exact commit before acceptance.
- Local commands were not run in this GitHub-web-only workflow. Do not report local test, type-check, lint, build or migration success.
- The existing workflow runs pytest with --cov=app.identity, SQLite Alembic upgrade/downgrade, PostgreSQL 16 migration/persistence/RLS smoke probes and compileall. Identity coverage does not measure the new operations endpoint's coverage.
- Dedicated type-check, lint, dependency-vulnerability scanning, broad security scanning, frontend build and end-to-end production checks are not configured.
- Branch protection is disabled on the development branch; review/CI gates remain governance risks.
