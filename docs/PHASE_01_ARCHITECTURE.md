# Phase 01 Architecture — Governance Contract

Status: IN PROGRESS. This document defines current scaffold boundaries; it does not claim persistence, authentication, tenant isolation or production readiness.

## Current implementation

- app/main.py is the composition root and exposes create_app(settings=None).
- app/core/config.py provides environment-backed settings with the OOSYS_ prefix.
- app/api/operations.py exposes unversioned liveness at /health.
- app/api/v1/router.py currently defines an empty APIRouter placeholder; no business endpoints are registered under /api/v1 yet. The configured prefix is verified by a test-only probe router, and the prefix will appear in the real OpenAPI schema when module routes are registered.
- Root / and /health behavior are preserved and tested through the public ASGI interface.
- App construction and imports must not connect to databases or external services.

## Layer responsibilities and dependency direction

- API/router: HTTP routing, transport validation, request/response mapping; no business rules or direct SQL.
- Application/use cases: orchestration, authorization coordination, transaction boundaries and idempotency; depends on domain rules and ports.
- Domain: entities, value objects, invariants, domain errors/events; no FastAPI, SQLAlchemy, environment or network dependencies.
- Repository contracts: persistence operations defined at application/domain boundary, not concrete ORM implementations.
- Persistence: SQLAlchemy mappings, repository adapters, queries and unit-of-work implementation.
- Infrastructure: database/session factories, provider clients, logging and telemetry, wired through dependency injection.
- Composition root: app/main.py wires settings and routers. Add infrastructure wiring only when actual implementations exist.

Dependency direction: API -> application -> domain/ports. Persistence and infrastructure implement ports. Cross-module communication uses published contracts/events, never another module’s private tables or repository. Do not create empty packages for future modules. Prefer one focused responsibility per file; aim below 150 lines and review around 120 where useful.

Proposed domain ownership and duplicated map-topic resolution are documented in [DOMAIN_OWNERSHIP.md](architecture/DOMAIN_OWNERSHIP.md). That proposal is not yet product-owner sign-off; MRP ownership and CRM/Sales boundaries need explicit review before those domains are implemented.

## API and operations

Business APIs use /api/v1; operational liveness/readiness remains outside business versioning. Validate input at the API boundary and use explicit schemas. Do not expose ORM objects. Errors should use stable codes and safe messages; never expose stack traces, SQL, secrets or private record existence. Preserve / and /health behavior until a documented compatibility change is approved. OpenAPI is the API contract; additive changes may remain in v1, breaking changes need a new version or time-bounded compatibility plan.

## Configuration and lifecycle

Environment variables use OOSYS_; never commit secrets. Settings can be injected into create_app. Importing modules and constructing the app must not open DB/network connections, create schemas, run migrations or call providers. Liveness is not dependency readiness; readiness must be bounded and truthful when real dependencies exist.

## Persistence standards (not implemented integration)

PostgreSQL is the target, SQLAlchemy 2 the proposed ORM, Alembic the migration tool. Every schema change requires a reviewed versioned migration, fresh-install and supported-upgrade tests, plus rollback/data-repair notes. Never auto-create production schema at startup. Use constraints for integrity and transactions for atomic use cases. Use Decimal and numeric database types for money, never binary float; persist UTC timestamps and handle timezone explicitly. Do not claim repositories, sessions, migrations or transaction handling exist until implemented and tested.

## Security and shared contracts

Authentication and server-side authorization are prerequisites for protected APIs. Tenant scope derives from verified identity/membership, never an untrusted request field. Cross-tenant read and mutation denial tests are required before tenant-owned modules ship. Store secrets outside source control; redact credentials and personal data in logs. Apply input validation, parameterized queries, strict CORS allowlists, CSRF protections for cookie auth, XSS-safe rendering, upload validation and tenant-scoped file access as applicable. Audit sensitive changes with actor, tenant, action, target, timestamp and outcome. Before changing shared API schemas, permissions, events or database contracts, inspect consumers, record compatibility impact and add contract tests. Version external events and require idempotent consumers; use an outbox when event publication must be atomic with a DB write.

## Testing and deferred scope

The current suite covers settings, factory injection, root and liveness behavior, generated OpenAPI basics, configured router prefix, and app construction/basic requests without socket connections. CI uses pytest and compileall; tests should use the public HTTPX ASGI transport rather than deprecated Starlette TestClient integration. Deferred: identity/session lifecycle, RBAC, tenant enforcement, audit persistence, DB/Alembic wiring, business modules, frontend, deployment, dependency scanning and production operations.
