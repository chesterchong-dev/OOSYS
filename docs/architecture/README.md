# Architecture Map

## Dependency direction
`API/router → application/use cases → domain/contracts`. Infrastructure adapters implement persistence/external-service contracts and are wired at the composition root. Domain code must not depend on FastAPI, SQLAlchemy, or infrastructure.

## Responsibilities
- `app/api/`: HTTP routing, request/response mapping, transport validation.
- `app/application/`: typed `UseCase[Command, Result]` injection contract, expected application errors and the future home for use-case orchestration/transaction boundaries; no business use cases are implemented yet.
- `app/domain/`: future entities, value objects, invariants and domain policies; no empty domain package is created before an owning module needs it.
- `app/repositories/`: persistence contracts, introduced with persistence work.
- `app/infrastructure/`: database and external adapters, introduced when needed.
- `app/core/`: cross-cutting runtime configuration and framework-independent utilities.
- `docs/decisions/`: ADRs and compatibility rationale.
- `tests/`: unit/API/integration tests grouped by behavior.

Do not create empty placeholder packages for future modules without a real contract or behavior. Add boundaries when the owning phase needs them.

- [Identity & Access Integration Contract](IDENTITY_ACCESS_CONTRACT.md)
