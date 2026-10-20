"""Operational endpoints independent of business API versioning."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import Settings
from app.core.database import create_database_engine

router = APIRouter(tags=["Operations"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness only; this endpoint does not verify dependency readiness."""
    return {"status": "ok"}


@router.get("/health/ready", response_model=None)
def readiness_check(request: Request) -> JSONResponse | dict[str, object]:
    """Check database readiness without exposing connection or configuration details."""
    settings: Settings = request.app.state.settings
    if settings.database_url is None:
        return JSONResponse(status_code=503, content={"status": "not_ready"})

    engine = getattr(request.app.state, "identity_engine", None)
    owns_engine = engine is None
    try:
        if engine is None:
            engine = create_database_engine(settings)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "checks": {"database": "ok"}}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    finally:
        if owns_engine and engine is not None:
            engine.dispose()
