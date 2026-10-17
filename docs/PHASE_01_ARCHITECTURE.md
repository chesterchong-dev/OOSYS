# Phase 01 — Architecture & Governance

## Status
**Starter documentation only; architecture not yet verified against the repository.**

## Proposed baseline
- Modular monolith with domain-owned modules.
- Separate API/router, application service, domain, repository, persistence, and infrastructure responsibilities.
- Dependency injection at module boundaries.
- PostgreSQL with versioned migrations.
- OpenAPI schemas, focused unit/integration tests, and structured audit logging.
- Explicit tenant context and authorization at the application/data-access boundary.

## Governance rules
- Inspect dependants before changing shared contracts.
- Prefer one focused responsibility per file.
- Add tests for critical business logic and cross-tenant denial.
- Record decisions and compatibility impact in `docs/decisions/`.
