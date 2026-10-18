# OOSYS Known Limitations — Phase 00 Baseline and Phase 01 Progress

## Repository and implementation

- The development branch remains a starter scaffold, not the full OOSYS product.
- app/main.py provides the root and liveness endpoints plus a composition root. The versioned API router is currently empty; no business endpoints are registered under /api/v1.
- Authentication, session expiry/revocation, RBAC, tenant enforcement, business modules, models/repositories, database migrations/integration, frontend and deployment manifests are not implemented.
- Requirements statuses remain 84 missing and 3 partial; source-map traceability does not mean the requirements are implemented.
- Proposed domain ownership is recorded in docs/architecture/DOMAIN_OWNERSHIP.md, but product-owner sign-off remains outstanding for cross-domain boundaries, particularly MRP and CRM/Sales.

## Verification

- Earlier Phase 00 checkpoint: CI run [39093554503](https://github.com/chesterchong-dev/OOSYS/actions/runs/39093554503) passed against exact SHA 113e47434bf87fc6881cb9afb8af2857202c55cd (1 test passed; compileall passed). This is historical evidence only.
- Phase 01 factory-test checkpoint: CI run [39095376591](https://github.com/chesterchong-dev/OOSYS/actions/runs/39095376591) passed against exact SHA fe0f84286793c8342b039a99b45ddf549780c744 (8 tests passed; compileall passed). That run still reported a Starlette/httpx deprecation warning because tests/test_health.py used Starlette TestClient.
- After that checkpoint, tests were refactored to share tests/asgi_client.py using HTTPX ASGITransport and to remove TestClient imports from test_health.py. Those changes and subsequent governance edits require a new successful CI run against the exact final SHA before Phase 01 sign-off.
- The workflow runs python -m pytest -q and python -m compileall -q app tests on Python 3.12. It does not currently run lint, type checks, coverage, dependency vulnerability scanning, frontend build, database/migration integration, or security scanning.
- No database/migration integration, coverage report, lint/type check, frontend build, dynamic security scan, dependency vulnerability scan, deployment check or end-to-end test has been performed.
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
