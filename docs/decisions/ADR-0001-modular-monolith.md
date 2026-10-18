# ADR-0001: Modular Monolith and Dependency Boundaries

- **Date:** 2026-10-18
- **Status:** Accepted for the current foundation; revisit only through a new ADR.

## Context
OOSYS spans many business domains. It needs maintainable boundaries without premature distributed-systems overhead; shared contracts and tenant/security boundaries will be critical.

## Decision
Use a modular monolith. Each business domain owns its entities, use cases, persistence adapters and API integration. Cross-domain communication uses explicit application contracts; domains must not import another domain's persistence internals. The API composition root wires modules through stable interfaces. Business APIs use `/api/v1`; operational liveness remains outside that prefix.

## Consequences
- Simpler local development, transactions, deployment and testing than early microservices.
- Requires explicit module ownership and dependency checks to avoid a distributed monolith inside one process.
- Shared contract changes require dependency inspection, compatibility notes and tests.
- PostgreSQL/SQLAlchemy are planned persistence standards; schema changes require reviewed migrations. No database connection or schema creation occurs at startup in this scaffold.
- This ADR does not imply authentication, tenant isolation, or production readiness.
