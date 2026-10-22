# OOSYS — Only One System

**Current state: Phases 00–03 accepted for their scoped criteria; Phase 04 accepted for the scoped frontend shell and existing-API administration milestone. Phase 05 is in progress and is not yet accepted. OOSYS is not production-ready.**

OOSYS is planned as a modular enterprise platform spanning ERP, WMS, CRM, accounting, HRMS, manufacturing/engineering, integrations and AI. The product map and requirements register remain the scope authority; implementation status must be evidence-based.

## Stack baseline
- Python 3.12+, FastAPI and Pydantic Settings
- PostgreSQL and SQLAlchemy 2 for persistence
- Alembic migrations, Pytest and GitHub Actions
- Frontend stack is React 18, TypeScript, Vite and Tailwind CSS 3 (Phase 04); production deployment configuration remains unimplemented.

## Local setup
1. Create a virtual environment with Python 3.12.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Run: `uvicorn app.main:app --reload`
4. Open /docs for OpenAPI. /health is liveness; /health/ready checks configured database readiness and returns 503 when no database is configured or the check fails.
5. Copy `.env.example` to `.env` and replace placeholders locally. Never commit `.env` or real secrets.

## Frontend (Phase 04)
1. Start the backend: install requirements, configure OOSYS_DATABASE_URL and run alembic upgrade head.
2. Start the API with uvicorn app.main:app --reload.
3. In another terminal run npm install and npm run dev; open the Vite URL (usually http://localhost:5173). The development proxy forwards /api to http://127.0.0.1:8000.
4. Verify frontend with npm run test:ci and npm run build. GitHub Actions runs both commands.
5. Sign in with an existing OOSYS account. Registration is disabled by default. Invitations require an existing active account and configured SMTP.

Production hosting must route /api to FastAPI on the same origin or configure VITE_API_BASE_URL and a strict backend CORS allowlist. CORS is disabled unless exact comma-separated origins are configured in OOSYS_CORS_ALLOWED_ORIGINS. Bearer tokens are used rather than authentication cookies.

## Phase 05 security and operations
See [Phase 05 implementation and recovery runbooks](docs/PHASE_05_SECURITY_OBSERVABILITY_RECOVERY.md). The phase is not accepted until exact-commit CI, dependency triage and a real disposable-database restore drill have evidence. Dependency audit and secret scanning run on pull requests, pushes to configured branches and on a weekly schedule. Aggregate request metrics are disabled by default; enable with OOSYS_METRICS_ENABLED and a 32+ character OOSYS_METRICS_TOKEN, and restrict the endpoint to trusted scrapers.

## Database migrations
- Configure OOSYS_DATABASE_URL outside source control before running migrations.
- Apply schema changes explicitly with alembic upgrade head; migrations are never run during app import or startup.
- The initial 20261018_0001 revision creates deployment-wide non-secret platform_settings. Do not store credentials or tenant/user preferences in this table.
- Phase 01/02 CI verified SQLite migration lifecycle and PostgreSQL 16 migration/persistence/RLS probes on commits recorded in governance documentation. This does not prove production readiness.

## Governance
- Keep phase work on phase-00-02-starter; do not write phase work directly to main. Phase 05 implementation is isolated on phase-05-security-observability pending review.
- CI installs declared dependencies, runs pytest with identity and operations-module coverage, checks migrations on SQLite and PostgreSQL, and compiles application/migration/test code. Implementation commit `724b0a8a2ea41173e5acb73a8b7fb474b4030c5b` passed exact-HEAD run [39513802070](https://github.com/chesterchong-dev/OOSYS/actions/runs/39513802070): 50 passed, 2 skipped, `app.api.operations.py` 100% coverage (26 statements), total configured coverage 92%, SQLite/PostgreSQL migration lifecycle, PostgreSQL persistence/RLS and concurrency probes, and compileall. The final requirements/documentation state also passed exact-HEAD CI run [39775847343](https://github.com/chesterchong-dev/OOSYS/actions/runs/39775847343) on SHA `df96f6f3fd2362c70fa404c524225603aaee0b52`.
- Never commit secrets. Configuration uses OOSYS_-prefixed environment variables.
- Phase 02 identity, authentication, sessions, RBAC and tenant isolation are implemented for their accepted scope. Broader tenant lifecycle and future business-table RLS still require work.
- Tenant settings CRUD, shared notifications/files/search/workflow/integration/subscription/AI services, business modules and production deployment remain unimplemented or deferred.
- See docs/PHASE_01_ARCHITECTURE.md, docs/PHASE_02_IDENTITY_MULTITENANCY.md, docs/PHASE_03_CORE_PLATFORM_FOUNDATION.md, docs/PHASE_04_FRONTEND_SHELL_ADMINISTRATION.md, docs/architecture/README.md, and docs/decisions/.
