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


def test_hierarchy_updates_filters_duplicates_and_leaf_archival(tmp_path):
    app, engine, _ = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("hierarchy2@example.com", "hierarchy2-org"))).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        org = owner["organization"]["id"]
        def create(kind, name, parent=None, code=None):
            return run(request(app, "POST", f"/api/v1/organizations/{org}/units", headers=headers,
                json={"unit_type": kind, "name": name, "parent_id": parent, "code": code}))
        root = create("business_unit", "Retail", code="RETAIL")
        location = create("location", "KL", root.json()["id"])
        department = create("department", "Sales", location.json()["id"])
        team = create("team", "Inside Sales", department.json()["id"])
        assert all(x.status_code == 201 for x in (root, location, department, team))
        assert create("business_unit", "Duplicate", code="RETAIL").status_code == 409
        patched = run(request(app, "PATCH", f"/api/v1/organizations/{org}/units/{team.json()['id']}",
            headers=headers, json={"name": "Outbound Sales", "code": "OUTBOUND"}))
        assert patched.status_code == 200 and patched.json()["name"] == "Outbound Sales"
        assert run(request(app, "PATCH", f"/api/v1/organizations/{org}/units/{team.json()['id']}",
            headers=headers, json={"parent_id": root.json()["id"]})).status_code == 422
        assert run(request(app, "PATCH", f"/api/v1/organizations/{org}/units/missing",
            headers=headers, json={"name": "Missing"})).status_code == 404
        assert run(request(app, "GET", f"/api/v1/organizations/{org}/units?unit_type=team",
            headers=headers)).json()["items"][0]["id"] == team.json()["id"]
        assert run(request(app, "GET", f"/api/v1/organizations/{org}/units?unit_type=invalid",
            headers=headers)).status_code == 422
        assert run(request(app, "PATCH", f"/api/v1/organizations/{org}/units/{location.json()['id']}",
            headers=headers, json={"parent_id": root.json()["id"]})).status_code == 409
        assert run(request(app, "POST", f"/api/v1/organizations/{org}/units/missing/archive",
            headers=headers)).status_code == 404
        for unit in (team, department, location, root):
            archived = run(request(app, "POST", f"/api/v1/organizations/{org}/units/{unit.json()['id']}/archive", headers=headers))
            assert archived.status_code == 204
    finally:
        engine.dispose()
