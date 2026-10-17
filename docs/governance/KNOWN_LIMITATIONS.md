# OOSYS Known Limitations — Phase 00

## Repository and execution
- The verified branch is a starter scaffold, not the full product. It contains only a FastAPI root/liveness endpoint and one health test.
- No real local Git checkout is available in this runtime. Fresh `getent ahosts github.com` returned zero entries, and no `.git` directory was found under `/mnt/data`. The archive-download alternative was unavailable through current retrieval tools. GitHub API reads do not substitute for a working-tree test run.
- Earlier test execution used pytest 9.0.2 while `requirements.txt` specifies `pytest>=8.0,<9.0`; dependency parity is unverified.
- No migrations/database integration, coverage, lint/type checks, frontend build, security/dependency scan, deployment check or end-to-end test has been performed.

## Product traceability
- Settings/configuration has partial source coverage through environment configuration (`4cad7a6a-8e2b-4352-9232-5f84be03b74e`), user notification preferences (`d8d6ddaf-52d0-486c-b543-ac91c93edac3`) and per-tenant connector configuration (`55839809-6854-4d8f-8c52-374a5fac46f2`); no general tenant/user settings CRUD and lifecycle topic exists.
- Subscription/entitlement and commercial-readiness requirements remain unresolved: only the `Commercial Enablement` parent topic was found; no dedicated SaaS subscription, billing-plan, feature-entitlement or commercial-readiness topic was found in the master map or four blueprint sheets.
- CRM service cases map to the actual `Service desk and ticketing` blueprint branch; semantic match, not exact title.
- CRM/sales/marketing, QMS/MRP, and workflow/approval subjects overlap across source maps. Domain ownership and shared contracts still need approved architecture decisions.

## Security posture
- No authentication, session revocation, RBAC, tenant enforcement, rate limiting, audit-event pipeline, database migration constraints, CI security checks or security scan configuration is implemented in the baseline branch.
- No dynamic penetration test or dependency vulnerability scan has been performed. Do not describe the scaffold as secure or production-ready.

## Governance
- Baseline commit is unsigned/unverified; branch protection is disabled.
- Phase 00 remains PARTIAL. Do not start Phase 02 until source gaps, real-checkout verification and final review are complete.
