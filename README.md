# OOSYS — Only One System

**Current state: Phase 01 architecture foundation in progress. Not production-ready.**

OOSYS is planned as a modular enterprise platform spanning ERP, WMS, CRM, accounting, HRMS, manufacturing/engineering, integrations and AI. The product map and requirements register remain the scope authority; implementation status must be evidence-based.

## Stack baseline
- Python 3.12+, FastAPI and Pydantic Settings
- PostgreSQL and SQLAlchemy 2 for planned persistence
- Pytest and GitHub Actions
- Frontend and deployment decisions belong to later architecture/implementation phases.

## Local setup
1. Create a virtual environment with Python 3.12.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Run: `uvicorn app.main:app --reload`
4. Open `/docs` for OpenAPI; liveness is `/health`.

## Governance
- Keep phase work on `phase-00-02-starter`; do not write phase work directly to `main`.
- CI installs declared dependencies, runs pytest, and compiles app/tests. A green run proves only tested behavior.
- Never commit secrets. Configuration uses `OOSYS_`-prefixed environment variables.
- Authentication, sessions, RBAC, tenant isolation, database migrations, business modules, frontend, and production deployment are not yet implemented.
- See `docs/PHASE_01_ARCHITECTURE.md`, `docs/architecture/README.md`, and `docs/decisions/`.
