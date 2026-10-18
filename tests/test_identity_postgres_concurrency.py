"""PostgreSQL concurrency regressions for one-time recovery credentials.

Run after migrations with OOSYS_RUN_POSTGRES_CONCURRENCY=1 and a restricted
non-superuser application database URL. Normal SQLite unit runs skip these.
"""
from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.identity import recovery_routes

pytestmark = pytest.mark.skipif(
    os.getenv("OOSYS_RUN_POSTGRES_CONCURRENCY") != "1",
    reason="requires migrated PostgreSQL and a restricted application role",
)


def _new_app():
    suffix = uuid4().hex[:12]
    settings = Settings(
        _env_file=None,
        database_url=SecretStr(os.environ["OOSYS_DATABASE_URL"]),
        allow_self_registration=True,
        smtp_host="localhost",
        email_from="noreply@example.com",
        password_reset_url="https://example.com/reset",
        invitation_accept_url="https://example.com/accept",
    )
    return create_app(settings), suffix


def _register(client, email: str, slug: str):
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Concurrent-Strong-Password-123",
        "full_name": "Concurrency Test",
        "organization_name": f"Concurrency {slug}",
        "organization_slug": slug,
    })
    assert response.status_code == 201, response.text
    return response.json()


def _post_concurrently(app, path: str, requests: list[tuple[dict[str, str], dict]]):
    def send(headers, payload):
        return TestClient(app).post(path, headers=headers, json=payload).status_code

    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        futures = [pool.submit(send, headers, payload) for headers, payload in requests]
        return sorted(future.result() for future in futures)


def test_concurrent_password_reset_confirmation_is_single_use(monkeypatch):
    app, suffix = _new_app()
    client = TestClient(app)
    email = f"reset-{suffix}@example.com"
    user = _register(client, email, f"reset-{suffix}")
    sent = []
    monkeypatch.setattr(
        recovery_routes, "send_password_reset",
        lambda settings, recipient, token: sent.append(token),
    )
    response = client.post("/api/v1/auth/password-reset/request", json={"email": email})
    assert response.status_code == 202
    assert len(sent) == 1

    payload = {"token": sent[0], "new_password": "Another-Strong-Password-456"}
    statuses = _post_concurrently(app, "/api/v1/auth/password-reset/confirm", [
        ({}, payload), ({}, payload),
    ])
    assert statuses == [204, 400]


def test_concurrent_invitation_acceptance_is_single_use(monkeypatch):
    app, suffix = _new_app()
    client = TestClient(app)
    owner = _register(client, f"owner-{suffix}@example.com", f"owner-{suffix}")
    invitee_email = f"invitee-{suffix}@example.com"
    invitee = _register(client, invitee_email, f"invitee-{suffix}")
    second_session = client.post("/api/v1/auth/login", json={
        "email": invitee_email,
        "password": "Concurrent-Strong-Password-123",
    })
    assert second_session.status_code == 200, second_session.text

    org_id = owner["organization"]["id"]
    owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
    roles = client.get(f"/api/v1/organizations/{org_id}/roles", headers=owner_headers)
    assert roles.status_code == 200, roles.text
    owner_role = next(role["id"] for role in roles.json() if role["name"] == "Owner")
    sent = []
    monkeypatch.setattr(
        recovery_routes, "send_invitation",
        lambda settings, recipient, token, organization_id: sent.append(token),
    )
    invitation = client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        headers=owner_headers,
        json={"email": invitee_email, "role_id": owner_role},
    )
    assert invitation.status_code == 202, invitation.text
    assert len(sent) == 1

    path = "/api/v1/auth/invitations/accept"
    payload = {"token": sent[0]}
    statuses = _post_concurrently(app, path, [
        ({"Authorization": f"Bearer {invitee['access_token']}"}, payload),
        ({"Authorization": f"Bearer {second_session.json()['access_token']}"}, payload),
    ])
    assert statuses == [201, 400]
