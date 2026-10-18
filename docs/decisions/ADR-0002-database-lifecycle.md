# ADR-0002: Explicit Database Engine and Session Lifecycle

- **Date:** 2026-10-18
- **Status:** Accepted.

## Context

OOSYS must support a PostgreSQL-backed modular monolith without opening connections at import time or app construction. Database configuration must not be committed as a secret, and tests must be able to inject an isolated engine.

## Decision

- Read the optional database URL from `OOSYS_DATABASE_URL` into Pydantic `SecretStr` settings.
- Construct SQLAlchemy engines only by explicitly calling `create_database_engine(settings)`; never create a module-global engine or connect during application factory execution.
- Construct session factories from an explicitly supplied engine. A FastAPI-compatible dependency owns request-session cleanup and rolls back when a use case raises.
- Keep commit/transaction policy in application use cases, not generic request plumbing or repository helpers. The generic session dependency never commits implicitly; atomic use cases must use an explicit transaction such as `with session.begin():`.
- Do not auto-create schema at startup. Alembic owns versioned schema changes and is invoked explicitly by operators/deployment tooling. The initial migration is tracked in ADR-0003.
- A missing database URL raises a clear configuration error when database construction or migrations are requested. It does not prevent the current liveness-only application from starting.

## Consequences and limits

The current foundation includes lifecycle plumbing and a deployment-wide non-secret platform settings table, but no business repositories, settings CRUD API, readiness endpoint, tenant isolation or production credentials. Tests use SQLite in-memory/file databases for local lifecycle and migration checks, and assert PostgreSQL engine construction does not initiate a network connection. A live PostgreSQL migration/integration test remains unverified and is required before claiming PostgreSQL compatibility.
