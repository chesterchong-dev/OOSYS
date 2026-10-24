"""Local/API verification for tenant-scoped inventory and transactional stock movements."""
from decimal import Decimal

from sqlalchemy import select

from app.inventory.models import InventoryMovement, InventoryProduct, InventoryStockBalance
from tests.test_identity_api import register_payload, request, run, setup_app


def setup_inventory(tmp_path):
    app, engine, factory = setup_app(tmp_path)
    owner = run(request(app, "POST", "/api/v1/auth/register",
                        json=register_payload("stock@example.com", "stock-org"))).json()
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    org_id = owner["organization"]["id"]
    unit = run(request(app, "POST", f"/api/v1/organizations/{org_id}/inventory/units", headers=headers,
                       json={"code": "EA", "name": "Each", "decimal_places": 0}))
    assert unit.status_code == 201
    category = run(request(app, "POST", f"/api/v1/organizations/{org_id}/inventory/categories", headers=headers,
                           json={"code": "PARTS", "name": "Parts"}))
    assert category.status_code == 201
    product = run(request(app, "POST", f"/api/v1/organizations/{org_id}/inventory/products", headers=headers,
                          json={"sku": "P-100", "name": "Bearing", "unit_id": unit.json()["id"],
                                "category_id": category.json()["id"], "barcode": "1234567890",
                                "cost_currency": "MYR"}))
    assert product.status_code == 201
    return app, engine, factory, org_id, headers, product.json()


def movement(product_id, kind, quantity, key, **extra):
    return {"product_id": product_id, "movement_type": kind, "quantity": quantity,
            "idempotency_key": key, **extra}


def test_inventory_master_data_stock_ledger_reservation_idempotency_and_cost(tmp_path):
    app, engine, factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        receipt_body = movement(product["id"], "receipt", "10", "receipt-001", unit_cost="2.500000")
        receipt = run(request(app, "POST", f"{base}/movements", headers=headers, json=receipt_body))
        assert receipt.status_code == 200
        assert receipt.json()["quantity_delta"] == "10.000000"
        assert receipt.json()["unit_cost"] == "2.500000"
        replay = run(request(app, "POST", f"{base}/movements", headers=headers, json=receipt_body))
        assert replay.status_code == 200
        assert replay.json()["id"] == receipt.json()["id"]

        mismatch = run(request(app, "POST", f"{base}/movements", headers=headers,
                              json=movement(product["id"], "receipt", "11", "receipt-001", unit_cost="2.5")))
        assert mismatch.status_code == 409

        reserve = run(request(app, "POST", f"{base}/movements", headers=headers,
                              json=movement(product["id"], "reserve", "4", "reserve-001")))
        assert reserve.status_code == 200
        insufficient = run(request(app, "POST", f"{base}/movements", headers=headers,
                                   json=movement(product["id"], "issue", "7", "issue-blocked")))
        assert insufficient.status_code == 409
        issue = run(request(app, "POST", f"{base}/movements", headers=headers,
                            json=movement(product["id"], "issue", "6", "issue-001")))
        assert issue.status_code == 200
        release = run(request(app, "POST", f"{base}/movements", headers=headers,
                              json=movement(product["id"], "release", "4", "release-001")))
        assert release.status_code == 200

        balances = run(request(app, "GET", f"{base}/balances", headers=headers))
        assert balances.status_code == 200
        balance = balances.json()["items"][0]
        assert balance["on_hand"] == "4.000000"
        assert balance["reserved"] == "0.000000"
        assert balance["available"] == "4.000000"
        assert balance["average_cost"] == "2.500000"
        history = run(request(app, "GET", f"{base}/movements?product_id={product['id']}", headers=headers))
        assert history.status_code == 200
        assert len(history.json()["items"]) == 4
        with factory() as session:
            stored = session.scalar(select(InventoryStockBalance).where(
                InventoryStockBalance.product_id == product["id"]))
            ledger = session.scalars(select(InventoryMovement).where(
                InventoryMovement.product_id == product["id"])).all()
            assert stored.on_hand == sum((row.quantity_delta for row in ledger), Decimal("0"))
            assert stored.reserved == sum((row.reserved_delta for row in ledger), Decimal("0"))
    finally:
        engine.dispose()


def test_negative_stock_and_precision_are_rejected(tmp_path):
    app, engine, factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        issue = run(request(app, "POST", f"{base}/movements", headers=headers,
                            json=movement(product["id"], "issue", "1", "empty-issue")))
        assert issue.status_code == 409
        too_precise = run(request(app, "POST", f"{base}/movements", headers=headers,
                                  json=movement(product["id"], "receipt", "1.5", "bad-precision")))
        assert too_precise.status_code == 422
    finally:
        engine.dispose()


def test_serial_tracking_requires_unique_in_stock_serial_and_one_unit(tmp_path):
    app, engine, factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        product = run(request(app, "POST", f"{base}/products", headers=headers,
                              json={"sku": "SER-1", "name": "Meter", "unit_id": product["unit_id"],
                                    "tracking_mode": "serial"})).json()
        missing_serial = run(request(app, "POST", f"{base}/movements", headers=headers,
                                     json=movement(product["id"], "receipt", "1", "serial-missing")))
        assert missing_serial.status_code == 422
        receipt = run(request(app, "POST", f"{base}/movements", headers=headers,
                              json=movement(product["id"], "receipt", "1", "serial-receipt",
                                            serial_code="SN-100", unit_cost="30")))
        assert receipt.status_code == 200
        duplicate = run(request(app, "POST", f"{base}/movements", headers=headers,
                                json=movement(product["id"], "receipt", "1", "serial-repeat",
                                              serial_code="SN-100", unit_cost="30")))
        assert duplicate.status_code == 409
        issue = run(request(app, "POST", f"{base}/movements", headers=headers,
                            json=movement(product["id"], "issue", "1", "serial-issue", serial_code="SN-100")))
        assert issue.status_code == 200
    finally:
        engine.dispose()


def test_inventory_is_tenant_scoped_and_permission_checked(tmp_path):
    app, engine, factory, org_id, headers, product = setup_inventory(tmp_path)
    try:
        other = run(request(app, "POST", "/api/v1/auth/register",
                            json=register_payload("other-stock@example.com", "other-stock-org"))).json()
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        other_org = other["organization"]["id"]
        cross_tenant = run(request(app, "GET", f"/api/v1/organizations/{other_org}/inventory/products",
                                   headers=headers))
        assert cross_tenant.status_code == 404

        limited = run(request(app, "POST", f"/api/v1/organizations/{org_id}/roles", headers=headers,
                              json={"name": "Inventory reader", "permissions": ["inventory.products.read"]}))
        assert limited.status_code == 201
        membership = run(request(app, "POST", f"/api/v1/organizations/{org_id}/members", headers=headers,
                                 json={"user_id": other["user"]["id"], "role_id": limited.json()["id"]}))
        assert membership.status_code == 201
        login = run(request(app, "POST", "/api/v1/auth/login", json={
            "email": "other-stock@example.com", "password": "a-strong-password-123", "organization_id": org_id,
        })).json()
        reader_headers = {"Authorization": f"Bearer {login['access_token']}"}
        assert run(request(app, "GET", f"/api/v1/organizations/{org_id}/inventory/products",
                           headers=reader_headers)).status_code == 200
        denied = run(request(app, "POST", f"/api/v1/organizations/{org_id}/inventory/movements",
                             headers=reader_headers,
                             json=movement(product["id"], "receipt", "1", "reader-forbidden")))
        assert denied.status_code == 403
    finally:
        engine.dispose()


def test_inventory_count_requires_separate_approval_and_posts_immutable_variance(tmp_path):
    app, engine, factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        receipt = run(request(app, "POST", f"{base}/movements", headers=headers,
                              json=movement(product["id"], "receipt", "10", "count-seed")))
        assert receipt.status_code == 200

        # A direct count movement would bypass the variance approval workflow.
        direct = run(request(app, "POST", f"{base}/movements", headers=headers,
                             json=movement(product["id"], "count", "8", "direct-count")))
        assert direct.status_code == 409

        created = run(request(app, "POST", f"{base}/counts", headers=headers, json={
            "count_type": "cycle", "note": "Aisle A", "lines": [{
                "product_id": product["id"], "counted_quantity": "8", "reason_code": "damage",
            }],
        }))
        assert created.status_code == 201
        count = created.json()
        assert count["status"] == "draft"
        assert count["lines"][0]["expected_on_hand"] == "10.000000"
        assert count["lines"][0]["variance"] == "-2.000000"

        submitted = run(request(app, "POST", f"{base}/counts/{count['id']}/submit", headers=headers))
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "submitted"
        self_approve = run(request(app, "POST", f"{base}/counts/{count['id']}/approve", headers=headers))
        assert self_approve.status_code == 403

        other = run(request(app, "POST", "/api/v1/auth/register",
                            json=register_payload("counter-approver@example.com", "counter-approver"))).json()
        role = run(request(app, "POST", f"/api/v1/organizations/{org_id}/roles", headers=headers,
                           json={"name": "Count approver", "permissions": [
                               "inventory.counts.read", "inventory.counts.approve"]}))
        assert role.status_code == 201
        member = run(request(app, "POST", f"/api/v1/organizations/{org_id}/members", headers=headers,
                             json={"user_id": other["user"]["id"], "role_id": role.json()["id"]}))
        assert member.status_code == 201
        login = run(request(app, "POST", "/api/v1/auth/login", json={
            "email": "counter-approver@example.com", "password": "a-strong-password-123",
            "organization_id": org_id,
        })).json()
        approver_headers = {"Authorization": f"Bearer {login['access_token']}"}
        approved = run(request(app, "POST", f"{base}/counts/{count['id']}/approve",
                               headers=approver_headers))
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        assert approved.json()["approved_by_user_id"] == other["user"]["id"]

        balances = run(request(app, "GET", f"{base}/balances", headers=headers)).json()
        assert balances["items"][0]["on_hand"] == "8.000000"
        with factory() as session:
            movements = session.scalars(select(InventoryMovement).where(
                InventoryMovement.product_id == product["id"],
                InventoryMovement.movement_type == "count",
            )).all()
            assert len(movements) == 1
            assert movements[0].quantity_delta == Decimal("-2")
            assert movements[0].note.startswith(f"Count {count['count_number']}: damage")
    finally:
        engine.dispose()


def test_inventory_count_rejects_stale_stock_snapshot(tmp_path):
    app, engine, factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        created = run(request(app, "POST", f"{base}/counts", headers=headers, json={
            "lines": [{"product_id": product["id"], "counted_quantity": "3",
                       "reason_code": "found"}],
        })).json()
        assert run(request(app, "POST", f"{base}/counts/{created['id']}/submit", headers=headers)).status_code == 200
        run(request(app, "POST", f"{base}/movements", headers=headers,
                    json=movement(product["id"], "receipt", "1", "after-count")))
        # Owner cannot approve their own count; the stale snapshot is also checked by an independent approver.
        other = run(request(app, "POST", "/api/v1/auth/register",
                            json=register_payload("stale-approver@example.com", "stale-approver"))).json()
        role = run(request(app, "POST", f"/api/v1/organizations/{org_id}/roles", headers=headers,
                           json={"name": "Stale count approver", "permissions": ["inventory.counts.approve"]})).json()
        run(request(app, "POST", f"/api/v1/organizations/{org_id}/members", headers=headers,
                    json={"user_id": other["user"]["id"], "role_id": role["id"]}))
        login = run(request(app, "POST", "/api/v1/auth/login", json={
            "email": "stale-approver@example.com", "password": "a-strong-password-123",
            "organization_id": org_id,
        })).json()
        response = run(request(app, "POST", f"{base}/counts/{created['id']}/approve",
                               headers={"Authorization": f"Bearer {login['access_token']}"}))
        assert response.status_code == 409
        assert "Stock changed" in response.json()["detail"]
        balance = run(request(app, "GET", f"{base}/balances", headers=headers)).json()["items"][0]
        assert balance["on_hand"] == "1.000000"
    finally:
        engine.dispose()
