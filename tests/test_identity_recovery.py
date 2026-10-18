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
        assert run(request(app, "POST", "/api/v1/auth/password-reset/request", json={"email": "reset@example.com"})).status_code == 202
        assert len(sent) == 1, "Reset requests should be throttled per account"
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


def test_invitation_can_be_revoked_before_acceptance(tmp_path, monkeypatch):
    app, engine, factory = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("revoke-owner@example.com", "revoke-owner-org"))).json()
        invitee = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("revoke-invitee@example.com", "revoke-invitee-org"))).json()
        org_id = owner["organization"]["id"]
        role_id = next(r["id"] for r in run(request(app, "GET", f"/api/v1/organizations/{org_id}/roles",
            headers={"Authorization": f"Bearer {owner['access_token']}"})).json() if r["name"] == "Owner")
        app.state.settings = Settings(_env_file=None, smtp_host="localhost", email_from="noreply@example.test",
            invitation_accept_url="https://example.test/accept")
        sent = []
        from app.identity import recovery_routes
        monkeypatch.setattr(recovery_routes, "send_invitation",
            lambda settings, recipient, token, organization_id: sent.append((recipient, token)))
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        created = run(request(app, "POST", f"/api/v1/organizations/{org_id}/invitations", headers=headers,
            json={"email": "revoke-invitee@example.com", "role_id": role_id}))
        assert created.status_code == 202
        with factory() as db:
            invitation = db.scalar(select(OrganizationInvitation).where(
                OrganizationInvitation.token_hash == token_digest(sent[0][1])))
            invitation_id = invitation.id
        revoked = run(request(app, "POST",
            f"/api/v1/organizations/{org_id}/invitations/{invitation_id}/revoke", headers=headers))
        assert revoked.status_code == 204
        accepted = run(request(app, "POST", "/api/v1/auth/invitations/accept",
            headers={"Authorization": f"Bearer {invitee['access_token']}"},
            json={"token": sent[0][1]}))
        assert accepted.status_code == 400
    finally:
        engine.dispose()
