# OOSYS Known Limitations — Phase 00

## Repository and execution
- The verified branch is a starter scaffold, not the full product. It contains only a FastAPI root/liveness endpoint and one health test.
- No real local Git checkout is available in this runtime. The prior DNS lookup returned zero entries and no `.git` directory was found under `/mnt/data`. The current GitHub connector can fetch individual repository files but does not expose a repository archive/git-bundle download; the archive route was unavailable. A branch-scoped GitHub Actions workflow has been added. Its commit has no reported combined status checks; the available workflow-run connector only returns pull-request-triggered runs and returned none; the direct Actions-runs endpoint is not allowed by the connector. The workflow's execution remains unverified.
- Installed pytest is 9.0.2 while `requirements.txt` specifies `pytest>=8.0,<9.0`. `python -m pip install --dry-run --no-index 'pytest>=8.0,<9.0'` failed with `No matching distribution found`, confirming the local package index/cache cannot supply a compatible pytest. Dependency parity remains unverified locally. The authored workflow YAML passed a local PyYAML syntax parse, but this is not a test run; the remote workflow must establish whether the declared constraints install and tests pass.
- No migrations/database integration, coverage, lint/type checks, frontend build, security/dependency scan, deployment check or end-to-end test has been performed.

## Product traceability
- Settings/configuration has partial source coverage through environment configuration (`4cad7a6a-8e2b-4352-9232-5f84be03b74e`), user notification preferences (`d8d6ddaf-52d0-486c-b543-ac91c93edac3`) and per-tenant connector configuration (`55839809-6854-4d8f-8c52-374a5fac46f2`); no general tenant/user settings CRUD and lifecycle topic exists.
- Subscription/entitlement and commercial-readiness requirements remain unresolved: `Commercial Enablement` (`560e332e-cbfe-4657-9107-0da7bda708f2`) has only CRM, Sales and Marketing children. The `Pricing and sales controls` node (`0ca9cf8d-8dfa-4c43-a019-377a26569209`) concerns transaction pricing, and `Define contract coverage, entitlements, response and resolution targets` (`cb386407-51e4-4bfb-a424-8daf4e011c71`) concerns service-contract/SLA scope, not SaaS product entitlements. No approved scope decisions exist.
- CRM service cases map to the actual `Service desk and ticketing` blueprint branch; semantic match, not exact title.
- CRM/sales/marketing, QMS/MRP, and workflow/approval subjects overlap across source maps. Domain ownership and shared contracts still need approved architecture decisions.

## Security posture
- No authentication, session revocation, RBAC, tenant enforcement, rate limiting, audit-event pipeline, database migration constraints, CI security checks or security scan configuration is implemented in the baseline branch.
- No dynamic penetration test or dependency vulnerability scan has been performed. Do not describe the scaffold as secure or production-ready.

## Governance
- Baseline commit is unsigned/unverified; branch protection is disabled.
- Phase 00 remains PARTIAL. Do not start Phase 02 until source gaps, real-checkout verification and final review are complete.
