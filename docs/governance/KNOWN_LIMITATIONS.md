# OOSYS Known Limitations — Phase 00 Baseline

## Repository and implementation
- The verified development branch remains a starter scaffold, not the full OOSYS product.
- `app/main.py` exposes only root and liveness endpoints; one health test exists.
- Authentication, session expiry/revocation, RBAC, tenant enforcement, business modules, models/repositories, database migrations/integration, frontend and deployment manifests are not implemented in this baseline.
- Requirements statuses remain 84 `missing` and 3 `partial`; source-map traceability does not mean the requirements are implemented.

## Verification
- GitHub Actions run [39090249092](https://github.com/chesterchong-dev/OOSYS/actions/runs/39090249092) used a genuine checkout, Python 3.12.15 and declared dependencies. Result: 1 test passed, one Starlette/httpx deprecation warning; compileall passed.
- No database/migration integration, coverage, lint/type check, frontend build, dynamic security scan, dependency vulnerability scan, deployment check or end-to-end test has been performed.
- The verification checkpoint commit is unsigned/unverified; branch protection was recorded as disabled during the prior audit. Repository protection settings were not changed during this reconciliation. The final evidence-only commit's CI must be verified against its exact SHA from GitHub Actions. Keep development changes on the development branch and protect `main` through repository rules.

## Product traceability
- Settings/configuration scope is now represented by canonical master-map and blueprint topics.
- Subscription/entitlement and SaaS commercial-readiness scope is now represented by canonical master-map and blueprint topics.
- The crosswalk contains 87 verified requirement IDs and no proxy-gap classifications. UUIDs are source locators, not proof of implemented functionality.
- CRM/sales/order/marketing, QMS/MRP and workflow/approval responsibilities overlap across source maps; Phase 01 must establish clear ownership and stable contracts.

## Security posture
- No dynamic penetration test or dependency vulnerability scan has been performed.
- The scaffold must not be described as secure or production-ready. Implement and verify auth, authorization, tenant isolation, rate limiting, audit events, migrations and security checks in their designated phases.
