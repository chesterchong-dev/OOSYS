"""Integration tests for tenant-scoped hierarchy operations."""
from tests.test_identity_api import register_payload, request, run, setup_app


def test_hierarchy_parent_validation_and_tenant_isolation(tmp_path):
    app, engine, _ = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("unit@example.com", "unit-org"))).json()
        other = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("otherunit@example.com", "other-unit-org"))).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        org = owner["organization"]["id"]
        root = run(request(app, "POST", f"/api/v1/organizations/{org}/units", headers=headers,
            json={"unit_type": "business_unit", "name": "Retail", "code": "RETAIL"}))
        assert root.status_code == 201
        loc = run(request(app, "POST", f"/api/v1/organizations/{org}/units", headers=headers,
            json={"unit_type": "location", "name": "KL Store", "parent_id": root.json()["id"]}))
        assert loc.status_code == 201
        assert run(request(app, "POST", f"/api/v1/organizations/{org}/units", headers=headers,
            json={"unit_type": "team", "name": "Orphan"})).status_code == 422
        assert run(request(app, "POST", f"/api/v1/organizations/{org}/units", headers=headers,
            json={"unit_type": "location", "name": "Cross", "parent_id": other["organization"]["id"]})).status_code == 422
        assert len(run(request(app, "GET", f"/api/v1/organizations/{org}/units", headers=headers)).json()["items"]) == 2
        assert run(request(app, "GET", f"/api/v1/organizations/{other['organization']['id']}/units", headers=headers)).status_code == 404
        assert run(request(app, "POST", f"/api/v1/organizations/{org}/units/{root.json()['id']}/archive", headers=headers)).status_code == 409
    finally:
        engine.dispose()
