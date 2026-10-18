# OOSYS Application and API Contracts

**Status:** Phase 01 foundation contract. This document defines boundaries, not implemented business use cases.

## Dependency direction

- **API/router:** owns HTTP paths, request parsing, response schemas, status codes and dependency wiring. It must not contain business policy, direct SQL or ORM query logic.
- **Application/use case:** accepts validated commands, coordinates domain behavior, authorization decisions, repository ports and transaction boundaries. It maps domain outcomes to expected application errors.
- **Domain:** owns invariants, entities, value objects and domain events. It must not import FastAPI, SQLAlchemy, settings, HTTP status codes or provider clients.
- **Repository/persistence adapter:** implements an explicit port owned by the application/domain boundary. It owns SQL and ORM mapping, not business policy.
- **Composition root:** constructs adapters and injects dependencies. Importing modules and creating the FastAPI app must not connect to external systems.

The typed `app.application.contracts.UseCase[Command, Result]` protocol is the stable injection seam: API adapters call `execute(command)` and depend on the protocol, not a concrete service class. Use case implementations coordinate domain logic and persistence ports. `app.application.errors.ApplicationError` and its safe subclasses are the expected-failure contract; the API adapter maps them to HTTP responses. Dependency direction is API → application → domain/ports; infrastructure implements ports and is wired at the composition root. Cross-domain calls use published application contracts or versioned events, never another domain's private ORM/table.

## HTTP contract

- Business endpoints are versioned under `/api/v1`; operational endpoints remain unversioned.
- Success responses use the endpoint's explicit Pydantic response model and appropriate HTTP status. Do not impose a generic success wrapper that obscures resource-specific schemas.
- Errors use `ErrorResponse`: `{ "error": { "code": string, "message": string, "details"?: [...] } }`.
- Validation details expose only location and validator code with a generic message. Never return rejected input, validator context, stack traces, SQL or exception text.
- Expected application errors map to stable safe status/code/message values. Unknown errors return generic HTTP 500. HTTP exception status and headers are preserved.
- Breaking changes to published response fields or meanings require a new API version or an explicitly time-bounded compatibility plan. Additive optional fields may be introduced compatibly.
- Pagination, filtering, sorting, idempotency, authentication and tenant authorization are not yet implemented; each must be specified and tested before business endpoints depend on it.

## Persistence and transaction contract

- Engine creation is explicit through `create_database_engine(settings)`; no module-global engine or application-startup connection is allowed.
- Sessions are request/use-case scoped and always closed. The generic dependency rolls back if an exception escapes and never commits automatically.
- Application use cases own transaction boundaries: use `with session.begin():` for an atomic unit of work and let exceptions propagate so the transaction rolls back. Do not commit in routers or generic session dependencies.
- Schema changes require Alembic revisions, clean-install and upgrade/downgrade tests. Application construction never runs migrations or creates tables.
- `platform_settings` stores deployment-wide non-secret values only. Do not store passwords, API keys, access tokens, tenant settings or user preferences there. Secret values belong in a secret manager/environment configuration; tenant/user configuration awaits its owning module and authorization model.

## Contract verification

The current suite checks safe 404/HTTP/validation/500 errors, app factory and liveness behavior, explicit session lifecycle and SQLite migration upgrade/downgrade. These checks do not establish PostgreSQL integration, auth/tenant security or production readiness.
