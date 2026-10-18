"""Contract tests for safe, stable API error responses."""
import asyncio

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

from app.core.config import Settings
from app.main import create_app


def request(app, method: str, path: str, **kwargs) -> httpx.Response:
    async def send():
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://oosys.test"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_not_found_uses_safe_error_envelope() -> None:
    response = request(create_app(Settings(_env_file=None)), "GET", "/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Resource not found."}
    }


def test_validation_error_does_not_echo_submitted_input() -> None:
    app = create_app(Settings(_env_file=None))

    class Payload(BaseModel):
        quantity: int

    @app.post("/test-payload")
    def accept_payload(payload: Payload) -> dict[str, int]:
        return {"quantity": payload.quantity}

    response = request(
        app, "POST", "/test-payload", json={"quantity": "sensitive-invalid-value"}
    )
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert body["message"] == "Request validation failed."
    assert body["details"][0]["location"] == ["body", "quantity"]
    assert "sensitive-invalid-value" not in response.text
    assert "input" not in body["details"][0]


def test_http_exception_does_not_expose_internal_detail() -> None:
    app = create_app(Settings(_env_file=None))

    @app.get("/test-denied")
    def denied():
        raise HTTPException(status_code=403, detail="secret database identifier")

    response = request(app, "GET", "/test-denied")
    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Request could not be completed.",
        }
    }
    assert "secret database identifier" not in response.text


def test_unexpected_error_does_not_leak_exception_text() -> None:
    app = create_app(Settings(_env_file=None))

    @app.get("/test-crash")
    def crash():
        raise RuntimeError("secret SQL and credentials")

    response = request(app, "GET", "/test-crash")
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An unexpected error occurred.",
        }
    }
    assert "secret SQL and credentials" not in response.text
