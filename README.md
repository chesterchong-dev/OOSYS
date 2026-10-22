# OOSYS — Only One System

**Current state: Phases 00–02 accepted for their scoped criteria; Phase 03 accepted for its bounded API/readiness foundation scope. OOSYS is not production-ready.**

OOSYS is planned as a modular enterprise platform spanning ERP, WMS, CRM, accounting, HRMS, manufacturing/engineering, integrations and AI. The product map and requirements register remain the scope authority; implementation status must be evidence-based.

## Stack baseline
- Python 3.12+, FastAPI and Pydantic Settings
- PostgreSQL and SQLAlchemy 2 for persistence
- Alembic migrations, Pytest and GitHub Actions
- Frontend and deployment decisions remain unimplemented until their scoped phases.

## Local setup
1. Create a virtual environment with Python 3.12.
2. Install dependencies: python -m pip install -r requirements.txt
3. Run: uvicorn app.main:app --reload
4. Open /docs for OpenAPI. /health is liveness; /health/ready checks configured database readiness and returns 503 when no database is configured or the check fails.

## Database migrations
- Configure OOSYS_DATABASE_URL outside source control before running migrations.
- Apply schema changes explicitly with alembic upgrade head; migrations are never run during app import or startup.
- The initial 20261018_0001 revision creates deployment-wide non-secret platform_settings. Do not store credentials or tenant/user preferences in this table.
- Phase 01/02 CI verified SQLite migration lifecycle and PostgreSQL 16 migration/persistence/RLS probes on commits recorded in governance documentation. This does not prove production readiness.

## Governance
- Keep phase work on phase-00-02-starter; do not write phase work directly to main.
- CI installs declared dependencies, runs pytest with identity and operations-module coverage, checks migrations on SQLite and PostgreSQL, and compiles application/migration/test code. Implementation commit `724b0a8a2ea41173e5acb73a8b7fb474b4030c5b` passed exact-HEAD run [39513802070](https://github.com/chesterchong-dev/OOSYS/actions/runs/39513802070): 50 passed, 2 skipped, `app.api.operations.py` 100% coverage (26 statements), total configured coverage 92%, SQLite/PostgreSQL migration lifecycle, PostgreSQL persistence/RLS and concurrency probes, and compileall. The final requirements/documentation state also passed exact-HEAD CI run [39775847343](https://github.com/chesterchong-dev/OOSYS/actions/runs/39775847343) on SHA `df96f6f3fd2362c70fa404c524225603aaee0b52`.
- Never commit secrets. Configuration uses OOSYS_-prefixed environment variables.
- Phase 02 identity, authentication, sessions, RBAC and tenant isolation are implemented for their accepted scope. Broader tenant lifecycle and future business-table RLS still require work.
- Tenant settings CRUD, shared notifications/files/search/workflow/integration/subscription/AI services, business modules, frontend and production deployment remain unimplemented or deferred.
- See docs/PHASE_01_ARCHITECTURE.md, docs/PHASE_02_IDENTITY_MULTITENANCY.md, docs/PHASE_03_CORE_PLATFORM_FOUNDATION.md, docs/architecture/README.md, and docs/decisions/.
