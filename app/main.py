"""OOSYS application composition root."""
from fastapi import FastAPI

from app.api.operations import router as operations_router
from app.api.v1.router import router as v1_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Build the API without connecting to external infrastructure at import time."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description="Only One System — modular enterprise platform",
        version=settings.app_version,
    )
    application.include_router(operations_router)
    application.include_router(v1_router, prefix=settings.api_prefix)

    @application.get("/", tags=["Operations"])
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "status": "starter"}

    return application


app = create_app()
