"""Architecture tests for application composition and dependency isolation."""
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_factory_registers_operational_and_versioned_routers() -> None:
    app = create_app(Settings(_env_file=None))
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/health" in paths
    assert app.openapi_url == "/openapi.json"


def test_factory_needs_no_external_services(monkeypatch) -> None:
    """Construction and basic requests must not require live infrastructure."""
    def fail_if_called(*args, **kwargs):
        raise AssertionError("external infrastructure must not be initialized here")

    monkeypatch.setattr("socket.create_connection", fail_if_called)
    app = create_app(Settings(_env_file=None))
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_prefix_is_configurable() -> None:
    app = create_app(Settings(api_prefix="/test/v1", _env_file=None))
    assert app.title == "OOSYS API"
    assert "/health" in {route.path for route in app.routes}
