"""Expected application failures have stable, safe HTTP mappings."""
import asyncio

import httpx
from fastapi import FastAPI

from app.api.errors import install_error_handlers
from app.application.errors import OperationConflict, OperationForbidden, ResourceNotFound


def request(app: FastAPI, path: str) -> httpx.Response:
    async def send():
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://oosys.test") as client:
            return await client.get(path)
    return asyncio.run(send())


def test_expected_application_errors_map_to_stable_safe_responses() -> None:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/missing")
    def missing():
        raise ResourceNotFound()

    @app.get("/conflict")
    def conflict():
        raise OperationConflict()

    @app.get("/forbidden")
    def forbidden():
        raise OperationForbidden()

    cases = [
        ("/missing", 404, "not_found", "Resource not found."),
        ("/conflict", 409, "conflict", "The operation conflicts with the current state."),
        ("/forbidden", 403, "forbidden", "The operation is not permitted."),
    ]
    for path, status, code, message in cases:
        response = request(app, path)
        assert response.status_code == status
        assert response.json() == {"error": {"code": code, "message": message}}
