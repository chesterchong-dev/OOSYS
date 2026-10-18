"""Smoke tests for the OOSYS application composition root."""
from app.core.config import Settings
from app.main import app, create_app
from tests.asgi_client import asgi_get


def test_health_check() -> None:
    response = asgi_get(app, "/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint() -> None:
    response = asgi_get(app, "/")
    assert response.status_code == 200
    assert response.json() == {"name": "OOSYS API", "status": "starter"}


def test_app_factory_uses_injected_settings() -> None:
    custom_settings = Settings(
        app_name="Test OOSYS",
        app_version="9.1",
        api_prefix="/custom/v1",
        _env_file=None,
    )
    custom_app = create_app(custom_settings)

    assert custom_app.title == "Test OOSYS"
    assert custom_app.version == "9.1"
    assert asgi_get(custom_app, "/").json()["name"] == "Test OOSYS"
    assert asgi_get(custom_app, "/health").status_code == 200
