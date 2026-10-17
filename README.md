# OOSYS — Phase 00–02 Starter Bundle

**Status: starter scaffold, not a completed production implementation.**

This bundle gives the repository a documented baseline for Phase 00 (audit/governance), Phase 01 (architecture foundation), and Phase 02 (identity/authentication/multi-tenancy). It is not a replacement for inspecting and integrating the actual existing repository.

## Stack
- Python 3.12+
- FastAPI
- SQLAlchemy 2
- PostgreSQL (recommended for deployment)
- Pytest

## Important
- Authentication and tenant isolation are not implemented in this starter bundle.
- Do not deploy this scaffold or expose it to the internet as a production service.
- Keep secrets in environment variables; never commit real credentials.
- Preserve the existing `.gitignore` in your GitHub repository.

## Local setup
1. Create a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `uvicorn app.main:app --reload`
4. Visit `/docs` for the API schema.

## Next development work
1. Audit current repository contents and map requirements.
2. Finalize architecture decisions and migration strategy.
3. Implement identity and tenant boundaries with migrations, session revocation, rate limiting, audit events, and tests before marking Phase 02 complete.
