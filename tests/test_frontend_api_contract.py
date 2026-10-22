"""Contract checks for the frontend's existing FastAPI endpoints; no database required."""
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_frontend_consumed_routes_exist_in_openapi():
    client = TestClient(create_app(Settings()))
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    expected = {
        "/api/v1/auth/login": {"post"},
        "/api/v1/auth/me": {"get", "patch"},
        "/api/v1/auth/me/password": {"post"},
        "/api/v1/auth/logout": {"post"},
        "/api/v1/organizations/{organization_id}": {"get", "patch"},
        "/api/v1/organizations/{organization_id}/members": {"get"},
        "/api/v1/organizations/{organization_id}/members/{user_id}": {"patch"},
        "/api/v1/organizations/{organization_id}/invitations": {"post"},
        "/api/v1/organizations/{organization_id}/roles": {"get", "post"},
        "/api/v1/organizations/{organization_id}/roles/{role_id}": {"patch"},
        "/api/v1/organizations/{organization_id}/roles/{role_id}/archive": {"post"},
        "/api/v1/organizations/{organization_id}/permissions": {"get"},
        "/api/v1/organizations/{organization_id}/units": {"get", "post"},
        "/api/v1/organizations/{organization_id}/units/{unit_id}": {"patch"},
        "/api/v1/organizations/{organization_id}/units/{unit_id}/archive": {"post"},
        "/api/v1/organizations/{organization_id}/audit-events": {"get"},
    }
    for path, methods in expected.items():
        assert path in paths, f"Missing frontend API contract: {path}"
        assert methods.issubset(paths[path]), f"Missing methods for {path}: {methods - paths[path].keys()}"
