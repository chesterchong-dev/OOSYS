# OOSYS Known Limitations — Phase 00 Baseline

## Repository and implementation
- The verified development branch remains a starter scaffold, not the full OOSYS product.
- `app/main.py` exposes only root and liveness endpoints; one health test exists.
- Authentication, session expiry/revocation, RBAC, tenant enforcement, business modules, models/repositories, database migrations/integration, frontend and deployment manifests are not implemented in this baseline.
- Requirements statuses remain 84 `missing` and 3 `partial`; source-map traceability does not mean the requirements are implemented.

## Verification
- Latest verified GitHub Actions run [39093554503](https://github.com/chesterchong-dev/OOSYS/actions/runs/39093554503) used a genuine checkout of exact SHA `113e47434bf87fc6881cb9afb8af2857202c55cd`, Python 3.12.15 and declared dependencies. Result: 1 test passed, one Starlette/httpx deprecation warning; compileall passed. Run 39090249092 is historical evidence for an earlier checkpoint.
- No database/migration integration, coverage, lint/type check, frontend build, dynamic security scan, dependency vulnerability scan, deployment check or end-to-end test has been performed.
- The verification checkpoint commit is unsigned/unverified; branch protection was recorded as disabled during the prior audit. Repository protection settings were not changed during this reconciliation. The latest verified checkpoint is `113e47434bf87fc6881cb9afb8af2857202c55cd`; its exact-SHA CI run 39093554503 passed. Any subsequent documentation commit must be verified separately against its own exact SHA. Keep development changes on the development branch and protect `main` through repository rules.

## Product traceability
- Settings/configuration scope is now represented by canonical master-map and blueprint topics.
- Subscription/entitlement and SaaS commercial-readiness scope is now represented by canonical master-map and blueprint topics.
- The crosswalk contains 87 verified requirement IDs and no proxy-gap classifications. UUIDs are source locators, not proof of implemented functionality.
- CRM/sales/order/marketing, QMS/MRP and workflow/approval responsibilities overlap across source maps; Phase 01 must establish clear ownership and stable contracts.

## Security posture
- No dynamic penetration test or dependency vulnerability scan has been performed.
- The scaffold must not be described as secure or production-ready. Implement and verify auth, authorization, tenant isolation, rate limiting, audit events, migrations and security checks in their designated phases.


## Current verification checkpoint — 2026-10-18
Live HEAD is `113e47434bf87fc6881cb9afb8af2857202c55cd`; `main` remains `568a208d81ecbba293c5b563df4402230846bc5c`. The latest successful CI is run `39093554503` against the exact HEAD. Register and crosswalk integrity checks passed; source UUIDs are present in the current maps. These checks do not establish application feature implementation, security, coverage or deployment readiness.


## Latest verified documentation checkpoint — 2026-10-18
The immediately preceding documentation-only reconciliation HEAD was `7ead5d67ee971a41f11e0dc3ccd2abbebc54549b`, tested successfully by exact-SHA GitHub Actions run [39094138486](https://github.com/chesterchong-dev/OOSYS/actions/runs/39094138486). It passed genuine checkout, Python 3.12.15 dependency installation, pytest (1 passed with one Starlette/httpx deprecation warning) and compileall. `main` remained `568a208d81ecbba293c5b563df4402230846bc5c`; the branch was 24 commits ahead, 0 behind. The current closure follow-up is verified separately; no product implementation or production readiness is implied.


## Phase 01 foundation checkpoint — 2026-10-18
The first Phase 01 foundation commit `d3a939bfdc17d51ce23beb68b58e9e6788cb07bf` passed exact-SHA CI run [39094708094](https://github.com/chesterchong-dev/OOSYS/actions/runs/39094708094). This does not verify authentication, tenant enforcement, persistence, migrations, frontend, security scans, or deployment. Later changes require their own exact-SHA CI evidence.
