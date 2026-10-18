# Phase 01 — Architecture & Development Governance

**Status: IN PROGRESS — foundation implementation started 2026-10-18.**

## Scope
Establish architecture contracts and minimal application scaffolding. Business modules, authentication, tenant enforcement, persistence, migrations, and production deployment are not implemented by this phase unless explicitly accepted and tested.

## Canonical rules
- Use a modular monolith with explicit domain ownership; avoid microservices until an ADR justifies their operational cost.
- Runtime baseline: Python 3.12+, FastAPI, Pydantic Settings. PostgreSQL/SQLAlchemy are planned persistence standards, not connected by this scaffold.
- Composition root: `app/main.py` creates the FastAPI application and wires routers. Importing modules must not create network/database connections.
- Responsibilities: API/router handles HTTP; application services orchestrate use cases; domain owns invariants; repository contracts abstract persistence; infrastructure implements database/external adapters.
- Dependency direction points inward: API → application → domain/contracts. Domain code must not import FastAPI, SQLAlchemy, or infrastructure.
- Business APIs use `/api/v1`; operational liveness is separate at `/health`.
- Environment settings use `OOSYS_` prefix. Never commit secrets.
- Errors must be stable and non-sensitive; never expose stack traces, credentials, SQL, or tenant data.
- Database changes require versioned migrations, reviewed constraints/indexes, rollback notes, and migration tests. Never create schema automatically at startup.
- Use decimal arithmetic and database numeric columns for money, never binary floating point.
- Authorization is server-side. Tenant scope derives from verified identity and applies to every tenant-owned read/write; client tenant IDs are not authorization.
- Test domain/application behavior, API contracts, migrations, and cross-tenant denial in their owning phases. Do not claim unmeasured coverage.
- One focused responsibility per file; aim under 150 lines and refactor around 120 lines when practical.
- Before changing shared contracts, inspect dependants and document compatibility implications.

## Scaffold
- `app/core/config.py`: typed environment configuration.
- `app/api/operations.py`: operational liveness route.
- `app/api/v1/router.py`: versioned business API composition.
- `app/main.py`: application factory/composition root.
- Business modules and persistence adapters are added only when their phase defines a real contract.

## Git and CI
Keep phase work on `phase-00-02-starter`; do not write to `main`. CI installs declared dependencies, runs pytest, and compiles app/tests. A green run proves only tested behavior.

## Acceptance checklist
- [x] Architecture, boundaries, configuration, versioning, migration, errors, testing and Git/CI rules documented.
- [x] Minimal app skeleton added while preserving root/liveness behavior.
- [ ] Focused tests pass in GitHub Actions.
- [ ] Exact final commit and CI evidence reconciled.
- [ ] Review source blueprint and record unresolved limitations.

Phase 01 remains in progress until all unchecked criteria are verified.