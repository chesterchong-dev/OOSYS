"""OOSYS application composition root."""
import hmac
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.api.errors import install_error_handlers
from app.api.operations import router as operations_router
from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings
from app.core.observability import install_observability, valid_metrics_token


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API with injectable settings and no startup infrastructure calls."""
    active_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine = getattr(app.state, "identity_engine", None)
        if engine is not None:
            engine.dispose()

    application = FastAPI(
        lifespan=lifespan,
        title=active_settings.app_name,
        description="Only One System — modular enterprise platform",
        version=active_settings.app_version,
    )
    application.state.settings = active_settings
    application.state.identity_engine = None
    application.state.identity_session_factory = None
    install_error_handlers(application)

    allowed_origins = [
        origin.strip()
        for origin in active_settings.cors_allowed_origins.split(",")
        if origin.strip()
    ]
    if allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )
    install_observability(application)

    application.include_router(operations_router)
    application.include_router(v1_router, prefix=active_settings.api_prefix)

    @application.get("/metrics", tags=["Operations"], include_in_schema=False)
    def metrics(request: Request) -> PlainTextResponse:
        """Expose bounded aggregate metrics only when explicitly enabled and authenticated."""
        metrics_settings: Settings = request.app.state.settings
        if not metrics_settings.metrics_enabled or metrics_settings.metrics_token is None:
            return PlainTextResponse("Not found", status_code=404)
        supplied_token = request.headers.get("X-Metrics-Token")
        configured_token = metrics_settings.metrics_token.get_secret_value()
        if not valid_metrics_token(supplied_token, configured_token):
            return PlainTextResponse("Not found", status_code=404)
        return PlainTextResponse(
            request.app.state.request_metrics.render_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @application.get("/", tags=["Operations"])
    def root() -> dict[str, str]:
        return {"name": active_settings.app_name, "status": "starter"}

    return application


app = create_app()
