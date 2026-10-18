"""Tests for lazy DB wiring and fail-closed principal validation."""
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from sqlalchemy import select, text
from starlette.requests import Request
from app.core.config import Settings
from app.identity.dependencies import get_identity_session
from app.identity.models import AuthSession, Membership, Organization, User
from app.identity.security import token_digest
from tests.test_identity_api import register_payload, request, run, setup_app


def test_identity_session_factory_is_created_lazily(tmp_path):
    app = FastAPI()
    app.state.settings = Settings(database_url=f"sqlite+pysqlite:///{tmp_path / 'lazy.db'}", _env_file=None)
    app.state.identity_engine = None
    app.state.identity_session_factory = None
    request_scope = Request({"type": "http", "app": app, "headers": [], "method": "GET", "path": "/"})
    generator = get_identity_session(request_scope)
    session = next(generator)
    try:
        assert session.scalar(text("SELECT 1")) == 1
        assert app.state.identity_session_factory is not None
    finally:
        generator.close()
        app.state.identity_engine.dispose()


def test_inactive_user_membership_organization_and_missing_tenant_fail_closed(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        created = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("guard@example.com", "guard-org"))).json()
        headers = {"Authorization": f"Bearer {created['access_token']}"}
        user_id, org_id = created["user"]["id"], created["organization"]["id"]
        with factory() as session:
            user = session.get(User, user_id)
            user.is_active = False
            session.commit()
        assert run(request(app, "GET", "/api/v1/auth/me", headers=headers)).status_code == 401
        with factory() as session:
            session.get(User, user_id).is_active = True
            session.commit()
            membership = session.scalar(select(Membership).where(Membership.user_id == user_id, Membership.organization_id == org_id))
            membership.status = "suspended"
            session.commit()
        assert run(request(app, "GET", "/api/v1/auth/me", headers=headers)).status_code == 403
        with factory() as session:
            session.scalar(select(Membership).where(Membership.user_id == user_id, Membership.organization_id == org_id)).status = "active"
            session.get(Organization, org_id).status = "suspended"
            session.commit()
        assert run(request(app, "GET", "/api/v1/auth/me", headers=headers)).status_code == 403
        with factory() as session:
            session.get(Organization, org_id).status = "active"
            auth = session.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(created["access_token"])))
            auth.active_organization_id = None
            session.commit()
        assert run(request(app, "GET", "/api/v1/auth/me", headers=headers)).status_code == 403
    finally:
        engine.dispose()
