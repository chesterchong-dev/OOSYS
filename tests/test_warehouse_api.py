"""API coverage for tenant-scoped warehouse and location master data."""
from tests.test_identity_api import register_payload, request, run, setup_app


def test_warehouse_hierarchy_validation_pagination_and_lifecycle(tmp_path):
    app, engine, _factory = setup_app(tmp_path)
    owner = run(request(app, "POST", "/api/v1/auth/register",
                        json=register_payload("warehouse@example.com", "warehouse-org"))).json()
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    organization_id = owner["organization"]["id"]
    base = f"/api/v1/organizations/{organization_id}/warehouses"
    try:
        created = run(request(app, "POST", base, headers=headers, json={
            "code": " north-01 ", "name": "North warehouse", "description": "Main site",
        }))
        assert created.status_code == 201, created.text
        warehouse = created.json()
        assert warehouse["code"] == "NORTH-01"
        assert warehouse["status"] == "active"

        duplicate = run(request(app, "POST", base, headers=headers,
                                json={"code": "north-01", "name": "Duplicate"}))
        assert duplicate.status_code == 409
        blank_name = run(request(app, "POST", base, headers=headers,
                                 json={"code": "WH-BLANK", "name": "   "}))
        assert blank_name.status_code == 422

        zone = run(request(app, "POST", f"{base}/{warehouse['id']}/locations", headers=headers, json={
            "code": "zone-a", "name": "Zone A", "location_type": "zone",
        }))
        assert zone.status_code == 201, zone.text
        bin_location = run(request(app, "POST", f"{base}/{warehouse['id']}/locations", headers=headers, json={
            "code": "bin-a-01", "name": "Bin A-01", "location_type": "bin",
            "parent_location_id": zone.json()["id"], "capacity_limit": "200", "capacity_unit": "kg",
        }))
        assert bin_location.status_code == 201, bin_location.text
        assert bin_location.json()["parent_location_id"] == zone.json()["id"]
        assert bin_location.json()["capacity_limit"] == "200.000000"

        blank_location_name = run(request(app, "POST", f"{base}/{warehouse['id']}/locations",
                                           headers=headers, json={
            "code": "BLANK-NAME", "name": " ", "location_type": "bin",
        }))
        assert blank_location_name.status_code == 422

        missing_parent = run(request(app, "POST", f"{base}/{warehouse['id']}/locations", headers=headers, json={
            "code": "bad-child", "name": "Wrong parent", "location_type": "bin",
            "parent_location_id": "another-tenant-location",
        }))
        assert missing_parent.status_code == 404
        incomplete_capacity = run(request(app, "POST", f"{base}/{warehouse['id']}/locations", headers=headers, json={
            "code": "bad-capacity", "name": "Bad capacity", "location_type": "bin",
            "capacity_limit": "50",
        }))
        assert incomplete_capacity.status_code == 422

        locations = run(request(app, "GET", f"{base}/{warehouse['id']}/locations?location_type=bin",
                                headers=headers))
        assert locations.status_code == 200
        assert [row["id"] for row in locations.json()["items"]] == [bin_location.json()["id"]]
        too_many = run(request(app, "GET", f"{base}/{warehouse['id']}/locations?limit=101", headers=headers))
        assert too_many.status_code == 422

        block_zone = run(request(app, "PATCH", f"{base}/{warehouse['id']}/locations/{zone.json()['id']}",
                                 headers=headers, json={"status": "blocked"}))
        assert block_zone.status_code == 409
        block_bin = run(request(app, "PATCH", f"{base}/{warehouse['id']}/locations/{bin_location.json()['id']}",
                                headers=headers, json={"status": "blocked"}))
        assert block_bin.status_code == 200
        block_zone = run(request(app, "PATCH", f"{base}/{warehouse['id']}/locations/{zone.json()['id']}",
                                 headers=headers, json={"status": "blocked"}))
        assert block_zone.status_code == 200
        deactivate = run(request(app, "PATCH", f"{base}/{warehouse['id']}", headers=headers,
                                 json={"status": "inactive"}))
        assert deactivate.status_code == 200
        add_location = run(request(app, "POST", f"{base}/{warehouse['id']}/locations", headers=headers, json={
            "code": "late", "name": "Late bin", "location_type": "bin",
        }))
        assert add_location.status_code == 409
    finally:
        engine.dispose()


def test_warehouse_endpoints_enforce_tenant_scope_and_permissions(tmp_path):
    app, engine, _factory = setup_app(tmp_path)
    owner = run(request(app, "POST", "/api/v1/auth/register",
                        json=register_payload("warehouse-owner@example.com", "warehouse-owner"))).json()
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    organization_id = owner["organization"]["id"]
    base = f"/api/v1/organizations/{organization_id}/warehouses"
    try:
        warehouse = run(request(app, "POST", base, headers=headers,
                                json={"code": "WH-A", "name": "A warehouse"})).json()
        other = run(request(app, "POST", "/api/v1/auth/register",
                            json=register_payload("warehouse-other@example.com", "warehouse-other"))).json()
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        other_org = other["organization"]["id"]
        cross_tenant = run(request(app, "GET", f"/api/v1/organizations/{other_org}/warehouses/{warehouse['id']}",
                                   headers=other_headers))
        assert cross_tenant.status_code == 404

        role = run(request(app, "POST", f"/api/v1/organizations/{organization_id}/roles", headers=headers,
                           json={"name": "Warehouse viewer", "permissions": ["warehouse.locations.read"]}))
        assert role.status_code == 201
        member = run(request(app, "POST", f"/api/v1/organizations/{organization_id}/members", headers=headers,
                             json={"user_id": other["user"]["id"], "role_id": role.json()["id"]}))
        assert member.status_code == 201
        login = run(request(app, "POST", "/api/v1/auth/login", json={
            "email": "warehouse-other@example.com", "password": "a-strong-password-123",
            "organization_id": organization_id,
        })).json()
        reader_headers = {"Authorization": f"Bearer {login['access_token']}"}
        listed = run(request(app, "GET", f"/api/v1/organizations/{organization_id}/warehouses",
                             headers=reader_headers))
        assert listed.status_code == 200
        denied = run(request(app, "POST", f"/api/v1/organizations/{organization_id}/warehouses",
                             headers=reader_headers, json={"code": "WH-B", "name": "No permission"}))
        assert denied.status_code == 403
    finally:
        engine.dispose()
