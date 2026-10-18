# Architecture Map

## Dependency direction
`API/router → application/use cases → domain/contracts`. Infrastructure adapters implement persistence/external-service contracts and are wired at the composition root. Domain code must not depend on FastAPI, SQLAlchemy, or infrastructure.

## Responsibilities
- `app/api/`: HTTP routing, request/response mapping, transport validation.
- `app/application/`: use-case orchestration and transaction boundaries, introduced with the first business module.
- `app/domain/`: entities, value objects, invariants and domain policies, introduced with the first business module.
- `app/repositories/`: persistence contracts, introduced with persistence work.
- `app/infrastructure/`: database and external adapters, introduced when needed.
- `app/core/`: cross-cutting runtime configuration and framework-independent utilities.
- `docs/decisions/`: ADRs and compatibility rationale.
- `tests/`: unit/API/integration tests grouped by behavior.

Do not create empty placeholder packages for future modules without a real contract or behavior. Add boundaries when the owning phase needs them.
