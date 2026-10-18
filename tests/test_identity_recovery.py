"""Integration tests for password reset and invitation security."""
from datetime import timedelta
from sqlalchemy import select
from app.core.config import Settings
from app.identity.models import OrganizationInvitation, PasswordResetToken
from app.identity.security import issue_token, token_digest, utc_now
from tests.test_identity_api import register_payload, request, run, setup_app


def test_password_reset_is_single_use_and_revokes_sessions(tmp_path, monkeypatch):
    app, engine, factory = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("reset@example.com", "reset-org"))).json()
        app.state.settings = Settings(_env_file=None, smtp_host="localhost", email_from="noreply@example.test", password_reset_url="https://example.test/reset")
        sent = []
        from app.identity import recovery_routes
        monkeypatch.setattr(recovery_routes, "send_password_reset", lambda settings, recipient, token: sent.append((recipient, token)))
        assert run(request(app, "POST", "/api/v1/auth/password-reset/request", json={"email": "reset@example.com"})).status_code == 202
        raw = sent[0][1]
        with factory() as db:
            assert db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_digest(raw))) is not None
        result = run(request(app, "POST", "/api/v1/auth/password-reset/confirm", json={"token": raw, "new_password": "new-strong-password-123"}))
        assert result.status_code == 204
        assert run(request(app, "GET", "/api/v1/auth/me", headers={"Authorization": f"Bearer {owner['access_token']}"})).status_code == 401
        assert run(request(app, "POST", "/api/v1/auth/password-reset/confirm", json={"token": raw, "new_password": "other-strong-password-123"})).status_code == 400
        assert run(request(app, "POST", "/api/v1/auth/login", json={"email": "reset@example.com", "password": "new-strong-password-123"})).status_code == 200
    finally:
        engine.dispose()


def test_invitation_acceptance_checks_email_and_prevents_replay(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("inviter@example.com", "invite-org"))).json()
        member = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("invitee@example.com", "invitee-org"))).json()
        org_id = owner["organization"]["id"]
        role_id = next(r["id"] for r in run(request(app, "GET", f"/api/v1/organizations/{org_id}/roles",
            headers={"Authorization": f"Bearer {owner['access_token']}"})).json() if r["name"] == "Owner")
        raw, digest = issue_token()
        with factory() as db:
            db.add(OrganizationInvitation(organization_id=org_id, email="invitee@example.com", role_id=role_id,
                invited_by_user_id=owner["user"]["id"], token_hash=digest, expires_at=utc_now()+timedelta(days=1)))
            db.commit()
        wrong = run(request(app, "POST", "/api/v1/auth/invitations/accept",
            headers={"Authorization": f"Bearer {owner['access_token']}"}, json={"token": raw}))
        assert wrong.status_code == 400
        headers = {"Authorization": f"Bearer {member['access_token']}"}
        accepted = run(request(app, "POST", "/api/v1/auth/invitations/accept", headers=headers, json={"token": raw}))
        assert accepted.status_code == 201 and accepted.json()["organization_id"] == org_id
        assert run(request(app, "POST", "/api/v1/auth/invitations/accept", headers=headers, json={"token": raw})).status_code == 400
    finally:
        engine.dispose()


def test_reset_configuration_unknown_account_and_expiry_paths(tmp_path, monkeypatch):
    app, engine, factory = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("expiry@example.com", "expiry-org"))).json()
        unconfigured = run(request(app, "POST", "/api/v1/auth/password-reset/request", json={"email": "expiry@example.com"}))
        assert unconfigured.status_code == 503
        app.state.settings = Settings(_env_file=None, smtp_host="localhost", email_from="noreply@example.test", password_reset_url="https://example.test/reset")
        from app.identity import recovery_routes
        monkeypatch.setattr(recovery_routes, "send_password_reset", lambda *args: None)
        unknown = run(request(app, "POST", "/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"}))
        assert unknown.status_code == 202
        assert unknown.json() == recovery_routes.RESET_MESSAGE
        with factory() as db:
            raw, digest = issue_token()
            db.add(PasswordResetToken(user_id=owner["user"]["id"], token_hash=digest, expires_at=utc_now()-timedelta(minutes=1)))
            db.commit()
        expired = run(request(app, "POST", "/api/v1/auth/password-reset/confirm",
            json={"token": raw, "new_password": "expired-strong-password-123"}))
        assert expired.status_code == 400
    finally:
        engine.dispose()


def test_invitation_creation_delivery_and_acceptance(tmp_path, monkeypatch):
    app, engine, factory = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("ownerinvite@example.com", "owner-invite-org"))).json()
        invitee = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("targetinvite@example.com", "target-invite-org"))).json()
        app.state.settings = Settings(_env_file=None, allow_self_registration=True, smtp_host="localhost", email_from="noreply@example.test",
            invitation_accept_url="https://example.test/accept")
        sent = []
        from app.identity import recovery_routes
        monkeypatch.setattr(recovery_routes, "send_invitation", lambda settings, email, token, org: sent.append((email, token, org)))
        org = owner["organization"]["id"]
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        owner_role = next(x["id"] for x in run(request(app, "GET", f"/api/v1/organizations/{org}/roles", headers=headers)).json() if x["name"] == "Owner")
        response = run(request(app, "POST", f"/api/v1/organizations/{org}/invitations", headers=headers,
            json={"email": "targetinvite@example.com", "role_id": owner_role}))
        assert response.status_code == 202 and sent[0][0] == "targetinvite@example.com"
        with factory() as db:
            invite = db.scalar(select(OrganizationInvitation).where(OrganizationInvitation.token_hash == token_digest(sent[0][1])))
            assert invite is not None and sent[0][1] != invite.token_hash
        accepted = run(request(app, "POST", "/api/v1/auth/invitations/accept",
            headers={"Authorization": f"Bearer {invitee['access_token']}"}, json={"token": sent[0][1]}))
        assert accepted.status_code == 201 and accepted.json()["organization_id"] == org
    finally:
        engine.dispose()


def test_invitation_delivery_failure_revokes_token_and_rejects_unknown_user(tmp_path, monkeypatch):
    app, engine, factory = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("ownerfail@example.com", "owner-fail-org"))).json()
        app.state.settings = Settings(_env_file=None, allow_self_registration=True, smtp_host="localhost", email_from="noreply@example.test",
            invitation_accept_url="https://example.test/accept")
        from app.identity import recovery_routes
        org = owner["organization"]["id"]
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        role_id = next(x["id"] for x in run(request(app, "GET", f"/api/v1/organizations/{org}/roles", headers=headers)).json() if x["name"] == "Owner")
        unknown = run(request(app, "POST", f"/api/v1/organizations/{org}/invitations", headers=headers,
            json={"email": "missing@example.com", "role_id": role_id}))
        assert unknown.status_code == 404
        monkeypatch.setattr(recovery_routes, "send_invitation", lambda *args: (_ for _ in ()).throw(RuntimeError("SMTP unavailable")))
        invitee = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("existinginvite@example.com", "existing-invite-org"))).json()
        failed = run(request(app, "POST", f"/api/v1/organizations/{org}/invitations", headers=headers,
            json={"email": "existinginvite@example.com", "role_id": role_id}))
        assert failed.status_code == 503
        with factory() as db:
            invitations = db.scalars(select(OrganizationInvitation).where(OrganizationInvitation.organization_id == org)).all()
            assert invitations and all(item.revoked_at is not None for item in invitations)
    finally:
        engine.dispose()
