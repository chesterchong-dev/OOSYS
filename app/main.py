"""OOSYS application composition root."""
from fastapi import FastAPI

from app.api.operations import router as operations_router
from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API with injectable settings and no startup infrastructure calls."""
    active_settings = settings or get_settings()
    application = FastAPI(
        title=active_settings.app_name,
        description="Only One System — modular enterprise platform",
        version=active_settings.app_version,
    )
    application.include_router(operations_router)
    application.include_router(v1_router, prefix=active_settings.api_prefix)

    @application.get("/", tags=["Operations"])
    def root() -> dict[str, str]:
        return {"name": active_settings.app_name, "status": "starter"}

    return application


app = create_app()
