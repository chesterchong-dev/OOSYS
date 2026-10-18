"""Integration tests for tenant administration, RBAC and account lifecycle."""
from sqlalchemy import select

from app.core.config import Settings
from app.identity.models import AuthSession, Membership, Organization, User
from app.identity.security import token_digest
from tests.test_identity_api import register_payload, request, run, setup_app


def test_organization_lifecycle_roles_and_audit_api(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("admin@example.com", "admin-org"))).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        org_id = owner["organization"]["id"]
        assert run(request(app, "GET", f"/api/v1/organizations/{org_id}", headers=headers)).status_code == 200
        changed = run(request(app, "PATCH", f"/api/v1/organizations/{org_id}", headers=headers, json={"name": "Renamed Org"}))
        assert changed.status_code == 200 and changed.json()["name"] == "Renamed Org"
        created = run(request(app, "POST", f"/api/v1/organizations/{org_id}/roles", headers=headers,
            json={"name": "Auditor", "description": "Audit access", "permissions": ["audit.read"]}))
        assert created.status_code == 201
        duplicate = run(request(app, "POST", f"/api/v1/organizations/{org_id}/roles", headers=headers,
            json={"name": "Auditor", "permissions": ["audit.read"]}))
        assert duplicate.status_code == 409
        updated = run(request(app, "PATCH", f"/api/v1/organizations/{org_id}/roles/{created.json()['id']}", headers=headers,
            json={"description": "Updated description", "permissions": ["audit.read", "roles.read"]}))
        assert updated.status_code == 200 and updated.json()["description"] == "Updated description"
        roles = run(request(app, "GET", f"/api/v1/organizations/{org_id}/roles", headers=headers)).json()
        assert {role["name"] for role in roles} >= {"Owner", "Auditor"}
        perms = run(request(app, "GET", f"/api/v1/organizations/{org_id}/permissions", headers=headers)).json()
        assert any(item["key"] == "audit.read" for item in perms)
        archived = run(request(app, "POST", f"/api/v1/organizations/{org_id}/roles/{created.json()['id']}/archive", headers=headers))
        assert archived.status_code == 204
        roles_after = run(request(app, "GET", f"/api/v1/organizations/{org_id}/roles", headers=headers)).json()
        assert "Auditor" not in {role["name"] for role in roles_after}
        audit = run(request(app, "GET", f"/api/v1/organizations/{org_id}/audit-events", headers=headers))
        assert audit.status_code == 200
        assert any(item["action"] == "role.archive" for item in audit.json()["items"])
    finally:
        engine.dispose()


def test_membership_status_role_assignment_and_escalation_denial(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("owner@example.com", "tenant-a"))).json()
        member_user = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("member@example.com", "tenant-b"))).json()
        owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
        org_id = owner["organization"]["id"]
        owner_role = next(role for role in run(request(app, "GET", f"/api/v1/organizations/{org_id}/roles", headers=owner_headers)).json() if role["name"] == "Owner")
        limited = run(request(app, "POST", f"/api/v1/organizations/{org_id}/roles", headers=owner_headers,
            json={"name": "Limited", "permissions": ["members.read", "members.update", "roles.create"]})).json()
        member = run(request(app, "POST", f"/api/v1/organizations/{org_id}/members", headers=owner_headers,
            json={"user_id": member_user["user"]["id"], "role_id": limited["id"]}))
        assert member.status_code == 201
        member_login = run(request(app, "POST", "/api/v1/auth/login", json={"email": "member@example.com",
            "password": "a-strong-password-123", "organization_id": org_id})).json()
        member_headers = {"Authorization": f"Bearer {member_login['access_token']}"}
        escalation = run(request(app, "PATCH", f"/api/v1/organizations/{org_id}/members/{member_user['user']['id']}",
            headers=member_headers, json={"role_id": owner_role["id"]}))
        assert escalation.status_code == 403
        self_suspend = run(request(app, "PATCH", f"/api/v1/organizations/{org_id}/members/{member_user['user']['id']}",
            headers=member_headers, json={"status": "suspended"}))
        assert self_suspend.status_code == 400
        changed = run(request(app, "PATCH", f"/api/v1/organizations/{org_id}/members/{member_user['user']['id']}",
            headers=owner_headers, json={"status": "suspended"}))
        assert changed.status_code == 200
        assert run(request(app, "GET", "/api/v1/auth/me", headers=member_headers)).status_code == 401
        reactivated = run(request(app, "PATCH", f"/api/v1/organizations/{org_id}/members/{member_user['user']['id']}",
            headers=owner_headers, json={"status": "active", "role_id": limited["id"]}))
        assert reactivated.status_code == 200
        assert run(request(app, "GET", f"/api/v1/organizations/{org_id}/members", headers=owner_headers)).status_code == 200
    finally:
        engine.dispose()


def test_account_profile_deactivation_and_organization_suspension(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("life@example.com", "lifecycle-org"))).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        profile = run(request(app, "PATCH", "/api/v1/auth/me", headers=headers, json={"full_name": "Updated Name"}))
        assert profile.status_code == 200 and profile.json()["full_name"] == "Updated Name"
        org_id = owner["organization"]["id"]
        suspended = run(request(app, "PATCH", f"/api/v1/organizations/{org_id}", headers=headers, json={"status": "suspended"}))
        assert suspended.status_code == 200 and suspended.json()["status"] == "suspended"
        assert run(request(app, "GET", "/api/v1/auth/me", headers=headers)).status_code == 401
        assert run(request(app, "POST", "/api/v1/auth/login", json={"email": "life@example.com", "password": "a-strong-password-123"})).status_code == 403

        second = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("archive@example.com", "archive-org"))).json()
        second_headers = {"Authorization": f"Bearer {second['access_token']}"}
        archived = run(request(app, "POST", f"/api/v1/organizations/{second['organization']['id']}/archive", headers=second_headers))
        assert archived.status_code == 204
        assert run(request(app, "GET", "/api/v1/auth/me", headers=second_headers)).status_code == 401

        third = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("deactivate@example.com", "deactivate-org"))).json()
        third_headers = {"Authorization": f"Bearer {third['access_token']}"}
        deactivated = run(request(app, "POST", "/api/v1/auth/me/deactivate", headers=third_headers))
        assert deactivated.status_code == 204
        assert run(request(app, "GET", "/api/v1/auth/me", headers=third_headers)).status_code == 401
    finally:
        engine.dispose()


def test_multi_organization_login_and_switching(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    try:
        first = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("first@example.com", "first-org"))).json()
        second = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("second@example.com", "second-org"))).json()
        first_headers = {"Authorization": f"Bearer {first['access_token']}"}
        first_org_id = first["organization"]["id"]
        owner_role = next(role for role in run(request(app, "GET", f"/api/v1/organizations/{first_org_id}/roles", headers=first_headers)).json() if role["name"] == "Owner")
        added = run(request(app, "POST", f"/api/v1/organizations/{first_org_id}/members", headers=first_headers,
            json={"user_id": second["user"]["id"], "role_id": owner_role["id"]}))
        assert added.status_code == 201
        selection = run(request(app, "POST", "/api/v1/auth/login", json={"email": "second@example.com", "password": "a-strong-password-123"}))
        assert selection.status_code == 200 and selection.json()["requires_organization_selection"] is True
        login = run(request(app, "POST", "/api/v1/auth/login", json={"email": "second@example.com",
            "password": "a-strong-password-123", "organization_id": second["organization"]["id"]})).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        switched = run(request(app, "POST", f"/api/v1/auth/switch-organization/{first_org_id}", headers=headers))
        assert switched.status_code == 200
        assert run(request(app, "GET", f"/api/v1/organizations/{first_org_id}", headers=headers)).status_code == 200
    finally:
        engine.dispose()
