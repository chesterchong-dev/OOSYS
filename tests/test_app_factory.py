"""Architecture tests for application composition and dependency isolation."""
import socket

from fastapi import APIRouter

import app.main as application_module
from app.core.config import Settings
from app.main import create_app
from tests.asgi_client import asgi_get


def test_factory_preserves_root_health_and_openapi_contract() -> None:
    app = create_app(Settings(_env_file=None))

    root = asgi_get(app, "/")
    assert root.status_code == 200
    assert root.json() == {"name": "OOSYS API", "status": "starter"}

    health = asgi_get(app, "/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    schema_response = asgi_get(app, "/openapi.json")
    assert schema_response.status_code == 200
    schema = schema_response.json()
    assert schema["info"]["title"] == "OOSYS API"
    assert schema["info"]["version"] == "0.1.0"
    assert {"/", "/health"}.issubset(schema["paths"])


def test_factory_needs_no_external_services(monkeypatch) -> None:
    """Construction and basic requests must not require live infrastructure."""
    def fail_if_called(*args, **kwargs):
        raise AssertionError("external infrastructure must not be initialized here")

    monkeypatch.setattr(socket, "create_connection", fail_if_called)
    monkeypatch.setattr(socket.socket, "connect", fail_if_called)
    app = create_app(Settings(_env_file=None))

    response = asgi_get(app, "/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_configured_api_prefix_is_applied_to_router_and_openapi(monkeypatch) -> None:
    router = APIRouter()

    @router.get("/probe")
    def probe() -> dict[str, str]:
        return {"status": "ok"}

    monkeypatch.setattr(application_module, "v1_router", router)
    app = create_app(Settings(api_prefix="/test/v1", _env_file=None))

    response = asgi_get(app, "/test/v1/probe")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    schema = asgi_get(app, "/openapi.json").json()
    assert "/test/v1/probe" in schema["paths"]
    assert "/api/v1/probe" not in schema["paths"]
