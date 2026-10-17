# OOSYS Known Limitations — Phase 00

## Repository and execution
- The verified branch is a starter scaffold, not the full product. It contains only a FastAPI root/liveness endpoint and one health test.
- No real local Git checkout is available in this runtime. A prior clone failed because DNS could not resolve `github.com`. GitHub API reads do not substitute for a working-tree test run.
- Earlier test execution used pytest 9.0.2 while `requirements.txt` specifies `pytest>=8.0,<9.0`; dependency parity is unverified.
- No migrations/database integration, coverage, lint/type checks, frontend build, security/dependency scan, deployment check or end-to-end test has been performed.

## Product traceability
- General settings/configuration has only a related deployment-configuration proxy topic.
- Subscription/entitlement and commercial-readiness requirements have only the `Commercial Enablement` parent topic; no dedicated subscription, billing-plan or entitlement topic was found.
- CRM service cases map to the actual `Service desk and ticketing` blueprint branch; semantic match, not exact title.
- CRM/sales/marketing, QMS/MRP, and workflow/approval subjects overlap across source maps. Domain ownership and shared contracts still need approved architecture decisions.

## Security posture
- No authentication, session revocation, RBAC, tenant enforcement, rate limiting, audit-event pipeline, database migration constraints, CI security checks or security scan configuration is implemented in the baseline branch.
- No dynamic penetration test or dependency vulnerability scan has been performed. Do not describe the scaffold as secure or production-ready.

## Governance
- Baseline commit is unsigned/unverified; branch protection is disabled.
- Phase 00 remains PARTIAL. Do not start Phase 02 until source gaps, real-checkout verification and final review are complete.
