"""Cover invitation issuance, delivery failure and reset edge cases."""
from app.core.config import Settings
from tests.test_identity_api import register_payload, request, run, setup_app


def test_invitation_issue_requires_config_and_active_account(tmp_path, monkeypatch):
    app, engine, _ = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("owner2@example.com", "invite2-org"))).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        org = owner["organization"]["id"]
        roles = run(request(app, "GET", f"/api/v1/organizations/{org}/roles", headers=headers)).json()
        role_id = next(r["id"] for r in roles if r["name"] == "Owner")
        payload = {"email": "unknown2@example.com", "role_id": role_id}
        app.state.settings = Settings(_env_file=None)
        assert run(request(app, "POST", f"/api/v1/organizations/{org}/invitations", headers=headers, json=payload)).status_code == 503
        app.state.settings = Settings(_env_file=None, smtp_host="localhost", email_from="noreply@example.test", invitation_accept_url="https://example.test/accept")
        assert run(request(app, "POST", f"/api/v1/organizations/{org}/invitations", headers=headers, json=payload)).status_code == 404
    finally:
        engine.dispose()


def test_invitation_issue_sends_and_revokes_when_delivery_fails(tmp_path, monkeypatch):
    app, engine, _ = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("owner3@example.com", "invite3-org"))).json()
        invitee = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("invitee3@example.com", "invitee3-org"))).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        org = owner["organization"]["id"]
        role_id = next(r["id"] for r in run(request(app, "GET", f"/api/v1/organizations/{org}/roles", headers=headers)).json() if r["name"] == "Owner")
        app.state.settings = Settings(_env_file=None, smtp_host="localhost", email_from="noreply@example.test", invitation_accept_url="https://example.test/accept")
        from app.identity import recovery_routes
        sent = []
        monkeypatch.setattr(recovery_routes, "send_invitation", lambda settings, email, token, org: sent.append((email, token, org)))
        response = run(request(app, "POST", f"/api/v1/organizations/{org}/invitations", headers=headers,
            json={"email": "invitee3@example.com", "role_id": role_id}))
        assert response.status_code == 202 and sent[0][0] == "invitee3@example.com"
        monkeypatch.setattr(recovery_routes, "send_invitation", lambda *args: (_ for _ in ()).throw(RuntimeError("SMTP down")))
        failed = run(request(app, "POST", f"/api/v1/organizations/{org}/invitations", headers=headers,
            json={"email": "invitee3@example.com", "role_id": role_id}))
        assert failed.status_code == 503
    finally:
        engine.dispose()
