"""API integration tests using an isolated SQLite database and the public ASGI surface."""
import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_base import Base
from app.core.database import create_database_engine, create_session_factory
from app.identity.dependencies import get_identity_session
from app.identity.models import AuthSession, Permission, User
from app.identity.permissions import PERMISSIONS
from app.identity.security import token_digest
from app.main import create_app
from app.platform_config import models as platform_models  # noqa: F401
from app.identity import models as identity_models  # noqa: F401


def setup_app(tmp_path):
    engine = create_database_engine(Settings(database_url=f"sqlite+pysqlite:///{tmp_path / 'identity.db'}", _env_file=None))
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        session.add_all([Permission(key=key, description=value) for key, value in PERMISSIONS.items()])
        session.commit()
    app = create_app(Settings(allow_self_registration=True, _env_file=None))
    def override_session():
        with factory() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise
    app.dependency_overrides[get_identity_session] = override_session
    return app, engine, factory


def run(coro):
    return asyncio.run(coro)


async def request(app, method, path, **kwargs):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://oosys.test") as client:
        return await client.request(method, path, **kwargs)


def register_payload(email, slug):
    return {"email": email, "password": "a-strong-password-123", "full_name": "Test User",
            "organization_name": slug.title(), "organization_slug": slug}


def test_register_login_logout_and_revocation(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        created = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("one@example.com", "org-one")))
        assert created.status_code == 201
        token = created.json()["access_token"]
        assert token and "password_hash" not in created.text
        headers = {"Authorization": f"Bearer {token}"}
        assert run(request(app, "GET", "/api/v1/auth/me", headers=headers)).status_code == 200
        logged_out = run(request(app, "POST", "/api/v1/auth/logout", headers=headers))
        assert logged_out.status_code == 204
        assert run(request(app, "GET", "/api/v1/auth/me", headers=headers)).status_code == 401
        login = run(request(app, "POST", "/api/v1/auth/login", json={"email": "one@example.com", "password": "a-strong-password-123"}))
        assert login.status_code == 200
        login_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        changed = run(request(app, "POST", "/api/v1/auth/me/password", headers=login_headers,
            json={"current_password": "a-strong-password-123", "new_password": "a-different-password-456"}))
        assert changed.status_code == 204
        assert run(request(app, "GET", "/api/v1/auth/me", headers=login_headers)).status_code == 401
        relogin = run(request(app, "POST", "/api/v1/auth/login", json={"email": "one@example.com", "password": "a-different-password-456"}))
        assert relogin.status_code == 200
        bad = run(request(app, "POST", "/api/v1/auth/login", json={"email": "one@example.com", "password": "a-strong-password-123"}))
        assert bad.status_code == 401
    finally:
        engine.dispose()


def test_expired_session_and_cross_tenant_organisation_read_denied(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        a = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("a@example.com", "org-a"))).json()
        b = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("b@example.com", "org-b"))).json()
        token_a = a["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        target = run(request(app, "GET", f"/api/v1/organizations/{b['organization']['id']}", headers=headers_a))
        assert target.status_code == 404
        target_patch = run(request(app, "PATCH", "/api/v1/organizations/" + b["organization"]["id"],
                                   headers=headers_a, json={"name": "Stolen"}))
        assert target_patch.status_code == 404
        with factory() as session:
            auth_session = session.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(token_a)))
            auth_session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
        expired = run(request(app, "GET", "/api/v1/auth/me", headers=headers_a))
        assert expired.status_code == 401
    finally:
        engine.dispose()


def test_role_cannot_escalate_permissions_and_member_is_tenant_scoped(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        a = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("owner-a@example.com", "org-a"))).json()
        b = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("user-b@example.com", "org-b"))).json()
        headers_a = {"Authorization": f"Bearer {a['access_token']}"}
        org_a = a["organization"]["id"]
        role_response = run(request(app, "POST", f"/api/v1/organizations/{org_a}/roles", headers=headers_a,
            json={"name": "Limited", "description": "Restricted role", "permissions": ["members.read", "roles.create"]}))
        assert role_response.status_code == 201
        member = run(request(app, "POST", f"/api/v1/organizations/{org_a}/members", headers=headers_a,
            json={"user_id": b["user"]["id"], "role_id": role_response.json()["id"]}))
        assert member.status_code == 201
        login = run(request(app, "POST", "/api/v1/auth/login", json={"email": "user-b@example.com",
            "password": "a-strong-password-123", "organization_id": org_a}))
        assert login.status_code == 200
        limited_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        escalation = run(request(app, "POST", f"/api/v1/organizations/{org_a}/roles", headers=limited_headers,
            json={"name": "Escalation", "permissions": ["audit.read"]}))
        assert escalation.status_code == 403
        cross_tenant_members = run(request(app, "GET", f"/api/v1/organizations/{b['organization']['id']}/members", headers=limited_headers))
        assert cross_tenant_members.status_code == 404
    finally:
        engine.dispose()


def test_unauthenticated_and_invalid_registration_rejected(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        assert run(request(app, "GET", "/api/v1/auth/me")).status_code == 401
        invalid = run(request(app, "POST", "/api/v1/auth/register", json={**register_payload("bad@example.com", "bad-org"), "password": "weak"}))
        assert invalid.status_code == 422
    finally:
        engine.dispose()


def test_login_rate_limit_applies_to_repeated_failures(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        for _ in range(8):
            response = run(request(app, "POST", "/api/v1/auth/login", json={"email": "unknown@example.com", "password": "wrong-password"}))
            assert response.status_code == 401
        limited = run(request(app, "POST", "/api/v1/auth/login", json={"email": "unknown@example.com", "password": "wrong-password"}))
        assert limited.status_code == 429
    finally:
        engine.dispose()


def test_self_registration_is_disabled_by_default(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        app.state.settings = Settings(_env_file=None)
        response = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("blocked@example.com", "blocked-org")))
        assert response.status_code == 403
    finally:
        engine.dispose()
