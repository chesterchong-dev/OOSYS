# OOSYS Known Limitations — Phase 03 Foundation Review

## Repository and implementation
- The development branch is a partial platform foundation, not the full OOSYS product.
- Phase 00–02 are accepted for their explicitly scoped criteria; see phase-specific evidence documents.
- Phase 03 adds database readiness at GET /health/ready; it only checks a configured database using SELECT 1. It does not prove migrations are current or validate mail, storage, search, integrations, AI, business workflows or production topology.
- /health remains liveness-only and makes no dependency calls.
- platform_settings remains deployment-wide non-secret storage, not tenant/user settings CRUD. Do not store secrets in this table.
- Shared notifications, file service, global search, tenant settings CRUD, subscription/entitlements, workflow engine, integration framework, shared AI and production deployment manifests remain unimplemented or only represented by narrow adapter boundaries. Phase 04 adds the frontend shell and selected existing-API administration UI, not the complete product.
- Business repositories, frontend and production deployment remain unimplemented.
- PostgreSQL CI probes are focused integration checks, not production deployment verification or full business persistence tests.

## Verification limitations
- Phase 03 is accepted for its bounded API/readiness foundation scope. Implementation commit `724b0a8a2ea41173e5acb73a8b7fb474b4030c5b` passed exact-HEAD CI run `39513802070`; final requirements/documentation commit `df96f6f3fd2362c70fa404c524225603aaee0b52` passed exact-HEAD CI run `39775847343`.
- Local commands were not run in this GitHub-web-only workflow. Do not report local test, type-check, lint, build or migration success.
- Exact-HEAD run `39513802070` executed pytest with --cov=app.identity and --cov=app.api.operations: `app/api/operations.py` measured 100% (26 statements, 0 missed); overall measured coverage 92%; 50 passed, 2 skipped, one Starlette/httpx deprecation warning. SQLite Alembic upgrade/downgrade, PostgreSQL 16 migration/persistence/RLS probes, two PostgreSQL recovery-token concurrency tests, PostgreSQL downgrade and compileall all passed. This is not production readiness or full-platform coverage. CORE-011 and CORE-012 remain partial; shared services outside the bounded slice remain unimplemented/deferred.
- Dedicated type-check, lint, dependency-vulnerability scanning, broad security scanning, frontend build and end-to-end production checks are not configured.
- Branch protection is disabled on the development branch; review/CI gates remain governance risks.

## Phase 04 frontend limitations
- No invitation listing/revocation UI, role-permission readback, profile-name readback, tenant/user settings CRUD or analytics-grade dashboard exists because required read contracts/services are absent.
- Production deployment must configure same-origin API routing or a reviewed CORS allowlist. Vite proxy is development-only.
- Frontend acceptance requires the dedicated Node.js CI job to pass on the exact final commit; no local build is claimed in this GitHub-web workflow.

- The member-list API does not return assigned role IDs; Phase 04 can assign/replace a role but cannot display the existing assignment. The UI states this before the table.
