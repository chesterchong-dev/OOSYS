"""Cover hierarchy filtering, updates, validation and archival lifecycle."""
from tests.test_identity_api import register_payload, request, run, setup_app


def test_hierarchy_update_filter_and_archive_lifecycle(tmp_path):
    app, engine, _ = setup_app(tmp_path)
    try:
        owner = run(request(app, "POST", "/api/v1/auth/register", json=register_payload("unitcrud@example.com", "unitcrud-org"))).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        org = owner["organization"]["id"]
        root = run(request(app, "POST", f"/api/v1/organizations/{org}/units", headers=headers,
            json={"unit_type": "business_unit", "name": "Sales"})).json()
        loc = run(request(app, "POST", f"/api/v1/organizations/{org}/units", headers=headers,
            json={"unit_type": "location", "name": "HQ", "parent_id": root["id"]})).json()
        team = run(request(app, "POST", f"/api/v1/organizations/{org}/units", headers=headers,
            json={"unit_type": "department", "name": "Operations", "parent_id": root["id"]})).json()
        filtered = run(request(app, "GET", f"/api/v1/organizations/{org}/units?unit_type=location&limit=500", headers=headers))
        assert filtered.status_code == 200 and len(filtered.json()["items"]) == 1 and filtered.json()["limit"] == 100
        invalid = run(request(app, "GET", f"/api/v1/organizations/{org}/units?unit_type=unknown", headers=headers))
        assert invalid.status_code == 422
        changed = run(request(app, "PATCH", f"/api/v1/organizations/{org}/units/{loc['id']}", headers=headers, json={"name":"HQ West"}))
        assert changed.status_code == 200 and changed.json()["name"] == "HQ West"
        self_parent = run(request(app, "PATCH", f"/api/v1/organizations/{org}/units/{loc['id']}", headers=headers, json={"parent_id":loc["id"]}))
        assert self_parent.status_code == 422
        bad_parent = run(request(app, "PATCH", f"/api/v1/organizations/{org}/units/{loc['id']}", headers=headers, json={"parent_id":team["id"]}))
        assert bad_parent.status_code == 422
        assert run(request(app, "POST", f"/api/v1/organizations/{org}/units/{loc['id']}/archive", headers=headers)).status_code == 204
        assert run(request(app, "POST", f"/api/v1/organizations/{org}/units/{team['id']}/archive", headers=headers)).status_code == 204
        assert run(request(app, "POST", f"/api/v1/organizations/{org}/units/{root['id']}/archive", headers=headers)).status_code == 204
    finally:
        engine.dispose()
