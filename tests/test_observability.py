"""Correlation and security-header regression tests."""
import json
import logging

from app.core.config import Settings
from app.core.observability import correlation_id
from app.main import create_app
from tests.asgi_client import asgi_get


def test_request_id_is_returned_and_safe_headers_are_set() -> None:
    application = create_app(Settings(_env_file=None))
    response = asgi_get(application, "/health", headers={"X-Request-ID": "crm-request_123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "crm-request_123"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"


def test_invalid_request_id_is_replaced() -> None:
    request_id = correlation_id("bad\r\nX-Injected: yes")
    assert request_id
    assert len(request_id) == 36
    assert "\r" not in request_id and "\n" not in request_id
    assert correlation_id("x" * 65) != "x" * 65


def test_structured_logs_do_not_include_query_or_auth_headers(caplog) -> None:
    application = create_app(Settings(_env_file=None))
    with caplog.at_level(logging.INFO, logger="oosys.request"):
        asgi_get(
            application,
            "/health?password=should-not-appear",
            headers={"Authorization": "Bearer secret-token-value", "X-Request-ID": "trace-42"},
        )
    entries = [record.message for record in caplog.records if record.name == "oosys.request"]
    assert entries
    assert all("should-not-appear" not in entry for entry in entries)
    assert all("secret-token-value" not in entry for entry in entries)
    parsed = json.loads(entries[-1])
    assert parsed["request_id"] == "trace-42"
    assert parsed["path"] == "/health"


def test_cors_wildcard_and_path_origins_are_rejected() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins="*", _env_file=None)


def test_cors_is_allowlisted_when_configured() -> None:
    application = create_app(Settings(cors_allowed_origins="https://portal.example.com", _env_file=None))
    response = asgi_get(
        application,
        "/health",
        headers={"Origin": "https://portal.example.com"},
    )
    assert response.headers["access-control-allow-origin"] == "https://portal.example.com"
    assert "access-control-allow-credentials" not in response.headers
