"""Architecture tests for application composition and dependency isolation."""
import asyncio

import httpx
from fastapi import APIRouter, FastAPI

from app.core.config import Settings
import app.main as application_module
from app.main import create_app


def request(app: FastAPI, path: str) -> httpx.Response:
    """Exercise ASGI endpoints without Starlette's deprecated httpx TestClient."""
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://oosys.test"
        ) as client:
            return await client.get(path)

    return asyncio.run(send_request())


def test_factory_preserves_root_health_and_openapi_contract() -> None:
    app = create_app(Settings(_env_file=None))

    root = request(app, "/")
    assert root.status_code == 200
    assert root.json() == {"name": "OOSYS API", "status": "starter"}

    health = request(app, "/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    schema_response = request(app, "/openapi.json")
    assert schema_response.status_code == 200
    schema = schema_response.json()
    assert schema["info"]["title"] == "OOSYS API"
    assert schema["info"]["version"] == "0.1.0"
    assert {"/", "/health"}.issubset(schema["paths"])


def test_factory_needs_no_external_services(monkeypatch) -> None:
    """Construction and basic requests must not require live infrastructure."""
    import socket

    def fail_if_called(*args, **kwargs):
        raise AssertionError("external infrastructure must not be initialized here")

    monkeypatch.setattr(socket, "create_connection", fail_if_called)
    monkeypatch.setattr(socket.socket, "connect", fail_if_called)
    app = create_app(Settings(_env_file=None))

    response = request(app, "/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_configured_api_prefix_is_applied_to_router_and_openapi(monkeypatch) -> None:
    router = APIRouter()

    @router.get("/probe")
    def probe() -> dict[str, str]:
        return {"status": "ok"}

    monkeypatch.setattr(application_module, "v1_router", router)
    app = create_app(Settings(api_prefix="/test/v1", _env_file=None))

    response = request(app, "/test/v1/probe")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    schema = request(app, "/openapi.json").json()
    assert "/test/v1/probe" in schema["paths"]
    assert "/api/v1/probe" not in schema["paths"]
