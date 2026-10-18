# ADR-0002: Explicit Database Engine and Session Lifecycle

- **Date:** 2026-10-18
- **Status:** Accepted for the current foundation.

## Context

OOSYS must support a PostgreSQL-backed modular monolith without opening connections at import time or app construction. Database configuration must not be committed as a secret, and tests must be able to inject an isolated engine.

## Decision

- Read the optional database URL from `OOSYS_DATABASE_URL` into Pydantic `SecretStr` settings.
- Construct SQLAlchemy engines only by explicitly calling `create_database_engine(settings)`; never create a module-global engine or connect during application factory execution.
- Construct session factories from an explicitly supplied engine. A FastAPI-compatible dependency owns request-session cleanup and rolls back when a use case raises.
- Keep commit/transaction policy in application use cases, not generic request plumbing or repository helpers.
- Do not auto-create schema at startup. Introduce Alembic and versioned migrations alongside the first real schema; every schema change must include migration and upgrade tests.
- A missing database URL raises a clear configuration error when database construction is requested. It does not prevent the current liveness-only application from starting.

## Consequences and limits

The current foundation is database lifecycle plumbing only. It does not add ORM models, repositories, a unit-of-work abstraction, migrations, database readiness, tenant isolation or production database credentials. Tests use SQLite in-memory for the generic session lifecycle and assert PostgreSQL engine construction does not initiate a network connection. A live PostgreSQL integration test remains a later acceptance requirement.
