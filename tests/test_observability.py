"""Correlation and security-header regression tests."""
import json

from fastapi import Request

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
    request_id = correlation_id("bad\\r\\nX-Injected: yes")
    assert request_id
    assert len(request_id) == 36
    assert "\\r" not in request_id and "\\n" not in request_id
    assert correlation_id("x" * 65) != "x" * 65


def test_generated_request_id_is_visible_to_downstream_endpoint() -> None:
    application = create_app(Settings(_env_file=None))

    @application.get("/test-correlation")
    def echo_correlation(request: Request) -> dict[str, str]:
        return {"request_id": request.headers["X-Request-ID"]}

    response = asgi_get(application, "/test-correlation")
    assert response.status_code == 200
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_structured_logs_do_not_include_query_or_auth_headers(monkeypatch) -> None:
    from app.core import observability

    captured: list[str] = []
    monkeypatch.setattr(observability._logger, "log", lambda _level, message: captured.append(message))
    application = create_app(Settings(_env_file=None))
    asgi_get(
        application,
        "/health?password=should-not-appear",
        headers={"Authorization": "Bearer secret-token-value", "X-Request-ID": "trace-42"},
    )
    assert captured
    assert all("should-not-appear" not in entry for entry in captured)
    assert all("secret-token-value" not in entry for entry in captured)
    parsed = json.loads(captured[-1])
    assert parsed["request_id"] == "trace-42"
    assert parsed["path"] == "/health"


def test_cors_wildcard_and_path_origins_are_rejected() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins="*", _env_file=None)
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins="https://portal.example.com/", _env_file=None)


def test_cors_is_allowlisted_when_configured() -> None:
    application = create_app(Settings(cors_allowed_origins="https://portal.example.com", _env_file=None))
    response = asgi_get(
        application,
        "/health",
        headers={"Origin": "https://portal.example.com"},
    )
    assert response.headers["access-control-allow-origin"] == "https://portal.example.com"
    assert "access-control-allow-credentials" not in response.headers



def test_metrics_endpoint_is_disabled_by_default() -> None:
    application = create_app(Settings(_env_file=None))
    response = asgi_get(application, "/metrics")
    assert response.status_code == 404
    assert "oosys_http_requests_total" not in response.text


def test_metrics_endpoint_requires_scrape_token_and_exposes_only_aggregate_labels() -> None:
    token = "metrics-scrape-token-with-32-chars-minimum"
    application = create_app(
        Settings(metrics_enabled=True, metrics_token=token, _env_file=None)
    )
    asgi_get(application, "/health?secret-query-value=private")
    denied = asgi_get(application, "/metrics")
    assert denied.status_code == 404
    rejected = asgi_get(application, "/metrics", headers={"X-Metrics-Token": "incorrect-metrics-token"})
    assert rejected.status_code == 404
    accepted = asgi_get(application, "/metrics", headers={"X-Metrics-Token": token})
    assert accepted.status_code == 200
    assert "oosys_http_requests_total" in accepted.text
    assert 'method="GET"' in accepted.text
    assert "secret-query-value" not in accepted.text
    assert "private" not in accepted.text


def test_metrics_cannot_be_enabled_without_a_long_token() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(metrics_enabled=True, metrics_token="short", _env_file=None)
