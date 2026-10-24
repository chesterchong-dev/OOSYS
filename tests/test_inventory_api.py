"""Local/API verification for tenant-scoped inventory and transactional stock movements."""
from decimal import Decimal

from sqlalchemy import select

from app.inventory.models import InventoryMovement, InventoryProduct, InventoryProductBarcode, InventoryStockBalance
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


def test_stock_movement_reversal_is_linked_idempotent_and_stock_safe(tmp_path):
    app, engine, factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        receipt = run(request(app, "POST", f"{base}/movements", headers=headers,
                              json=movement(product["id"], "receipt", "5", "reversal-receipt")))
        assert receipt.status_code == 200
        issue = run(request(app, "POST", f"{base}/movements", headers=headers,
                            json=movement(product["id"], "issue", "2", "reversal-issue")))
        assert issue.status_code == 200

        reverse_url = f"{base}/movements/{issue.json()['id']}/reverse"
        payload = {"idempotency_key": "undo-issue-001", "note": "Posted against wrong order"}
        reversed_response = run(request(app, "POST", reverse_url, headers=headers, json=payload))
        assert reversed_response.status_code == 200, reversed_response.text
        reversal = reversed_response.json()
        assert reversal["movement_type"] == "reversal"
        assert reversal["reversal_of_movement_id"] == issue.json()["id"]
        assert reversal["quantity_delta"] == "2.000000"

        replay = run(request(app, "POST", reverse_url, headers=headers, json=payload))
        assert replay.status_code == 200
        assert replay.json()["id"] == reversal["id"]
        duplicate = run(request(app, "POST", reverse_url, headers=headers,
                               json={"idempotency_key": "undo-issue-002", "note": "Second attempt"}))
        assert duplicate.status_code == 409

        reserved = run(request(app, "POST", f"{base}/movements", headers=headers,
                               json=movement(product["id"], "reserve", "1", "reversal-reserve")))
        assert reserved.status_code == 200

        blocked = run(request(app, "POST", f"{base}/movements/{receipt.json()['id']}/reverse",
                              headers=headers,
                              json={"idempotency_key": "undo-receipt-001", "note": "Would remove reserved stock"}))
        assert blocked.status_code == 409
        balance = run(request(app, "GET", f"{base}/balances", headers=headers)).json()["items"][0]
        assert balance["on_hand"] == "5.000000"
        with factory() as session:
            stored = session.scalar(select(InventoryStockBalance).where(
                InventoryStockBalance.product_id == product["id"]))
            ledger = session.scalars(select(InventoryMovement).where(
                InventoryMovement.product_id == product["id"])).all()
            assert stored.on_hand == sum((row.quantity_delta for row in ledger), Decimal("0"))
            assert sum(row.reversal_of_movement_id == issue.json()["id"] for row in ledger) == 1
    finally:
        engine.dispose()


def test_inventory_movement_pagination_is_stable_and_bounded(tmp_path):
    app, engine, _factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        for index in range(3):
            posted = run(request(app, "POST", f"{base}/movements", headers=headers,
                                 json=movement(product["id"], "receipt", "1", f"page-{index}-key")))
            assert posted.status_code == 200, posted.text

        first = run(request(app, "GET", f"{base}/movements?product_id={product['id']}&limit=1&offset=0",
                            headers=headers))
        second = run(request(app, "GET", f"{base}/movements?product_id={product['id']}&limit=1&offset=1",
                             headers=headers))
        assert first.status_code == second.status_code == 200
        assert len(first.json()["items"]) == len(second.json()["items"]) == 1
        assert first.json()["items"][0]["id"] != second.json()["items"][0]["id"]
        assert first.json()["limit"] == second.json()["limit"] == 1
        assert first.json()["offset"] == 0
        assert second.json()["offset"] == 1

        too_many = run(request(app, "GET", f"{base}/movements?limit=101", headers=headers))
        negative_offset = run(request(app, "GET", f"{base}/movements?offset=-1", headers=headers))
        assert too_many.status_code == 422
        assert negative_offset.status_code == 422
    finally:
        engine.dispose()


def test_location_ledger_projection_keeps_legacy_stock_unlocated(tmp_path):
    app, engine, _factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}"
    try:
        warehouse = run(request(app, "POST", f"{base}/warehouses", headers=headers,
                                json={"code": "WH-LOC", "name": "Location test"})).json()
        location = run(request(app, "POST", f"{base}/warehouses/{warehouse['id']}/locations",
                               headers=headers, json={"code": "BIN-1", "name": "Bin 1",
                                                     "location_type": "bin"})).json()
        legacy = run(request(app, "POST", f"{base}/inventory/movements", headers=headers,
                             json=movement(product["id"], "receipt", "3", "location-legacy")))
        unavailable_at_location = run(request(
            app, "POST", f"{base}/inventory/movements", headers=headers,
            json=movement(product["id"], "issue", "1", "location-empty-issue",
                          warehouse_location_id=location["id"]),
        ))
        assert unavailable_at_location.status_code == 409
        located = run(request(app, "POST", f"{base}/inventory/movements", headers=headers,
                              json=movement(product["id"], "receipt", "4", "location-known",
                                            warehouse_location_id=location["id"])))
        assert legacy.status_code == located.status_code == 200
        assert located.json()["warehouse_location_id"] == location["id"]

        projection = run(request(app, "GET", f"{base}/inventory/location-balances?product_id={product['id']}",
                                 headers=headers))
        assert projection.status_code == 200
        rows = {row["warehouse_location_id"]: row for row in projection.json()["items"]}
        assert rows[None]["unlocated"] is True
        assert rows[None]["on_hand"] == "3.000000"
        assert rows[location["id"]]["unlocated"] is False
        assert rows[location["id"]]["on_hand"] == "4.000000"
        aggregate = run(request(app, "GET", f"{base}/inventory/balances", headers=headers))
        assert aggregate.json()["items"][0]["on_hand"] == "7.000000"

        zone = run(request(app, "POST", f"{base}/warehouses/{warehouse['id']}/locations",
                           headers=headers, json={"code": "ZONE-1", "name": "Zone 1",
                                                 "location_type": "zone"})).json()
        rejected = run(request(app, "POST", f"{base}/inventory/movements", headers=headers,
                               json=movement(product["id"], "receipt", "1", "location-zone",
                                             warehouse_location_id=zone["id"])))
        assert rejected.status_code == 409
    finally:
        engine.dispose()


def test_warehouse_receipt_posts_once_to_inventory_location(tmp_path):
    app, engine, _factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}"
    try:
        warehouse = run(request(app, "POST", f"{base}/warehouses", headers=headers,
                                json={"code": "WH-RECEIVE", "name": "Receiving warehouse"})).json()
        location = run(request(app, "POST", f"{base}/warehouses/{warehouse['id']}/locations",
                               headers=headers, json={"code": "RECEIVE", "name": "Receiving bay",
                                                     "location_type": "receiving"})).json()
        bin_location = run(request(app, "POST", f"{base}/warehouses/{warehouse['id']}/locations",
                                   headers=headers, json={"code": "BIN-1", "name": "Storage bin",
                                                         "location_type": "bin"})).json()
        receipt_payload = {
            "receiving_location_id": location["id"],
            "idempotency_key": "receipt-create-001",
            "source_reference": "PO-EXTERNAL-17",
            "note": "Initial receipt",
            "lines": [{"product_id": product["id"], "quantity": "5", "unit_cost": "2.50"}],
        }
        created = run(request(app, "POST", f"{base}/warehouses/{warehouse['id']}/receipts",
                              headers=headers, json=receipt_payload))
        assert created.status_code == 201, created.text
        receipt = created.json()
        assert receipt["status"] == "draft"
        assert receipt["lines"][0]["quantity"] == "5.000000"

        replay = run(request(app, "POST", f"{base}/warehouses/{warehouse['id']}/receipts",
                             headers=headers, json=receipt_payload))
        assert replay.status_code == 201
        assert replay.json()["id"] == receipt["id"]
        conflict_payload = {**receipt_payload, "note": "Different request"}
        conflict = run(request(app, "POST", f"{base}/warehouses/{warehouse['id']}/receipts",
                               headers=headers, json=conflict_payload))
        assert conflict.status_code == 409

        post_url = f"{base}/warehouses/{warehouse['id']}/receipts/{receipt['id']}/post"
        posted = run(request(app, "POST", post_url, headers=headers))
        assert posted.status_code == 200, posted.text
        assert posted.json()["status"] == "posted"
        repeated_post = run(request(app, "POST", post_url, headers=headers))
        assert repeated_post.status_code == 200
        assert repeated_post.json()["id"] == receipt["id"]

        task_page = run(request(app, "GET", f"{base}/warehouses/{warehouse['id']}/putaway-tasks?status=pending",
                                headers=headers))
        assert task_page.status_code == 200
        task = task_page.json()["items"][0]
        assert task["status"] == "pending"
        assigned = run(request(app, "POST",
                               f"{base}/warehouses/{warehouse['id']}/putaway-tasks/{task['id']}/assign",
                               headers=headers, json={"destination_location_id": bin_location["id"]}))
        assert assigned.status_code == 200
        assert assigned.json()["status"] == "assigned"
        putaway_url = f"{base}/warehouses/{warehouse['id']}/putaway-tasks/{task['id']}/complete"
        completed = run(request(app, "POST", putaway_url, headers=headers))
        assert completed.status_code == 200, completed.text
        assert completed.json()["status"] == "completed"
        replay_putaway = run(request(app, "POST", putaway_url, headers=headers))
        assert replay_putaway.status_code == 200
        assert replay_putaway.json()["id"] == task["id"]

        balances = run(request(app, "GET", f"{base}/inventory/location-balances?product_id={product['id']}",
                               headers=headers)).json()["items"]
        by_location = {row["warehouse_location_id"]: row for row in balances}
        assert by_location[location["id"]]["on_hand"] == "0.000000"
        assert by_location[bin_location["id"]]["on_hand"] == "5.000000"
        movements = run(request(app, "GET", f"{base}/inventory/movements?product_id={product['id']}",
                                headers=headers)).json()["items"]
        assert len(movements) == 3
        assert {movement["warehouse_location_id"] for movement in movements} == {
            location["id"], bin_location["id"],
        }
    finally:
        engine.dispose()


def test_warehouse_transfer_tracks_in_transit_stock_and_receives_once(tmp_path):
    app, engine, _factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}"
    try:
        locations = []
        for code in ("SOURCE", "DEST"):
            warehouse = run(request(app, "POST", f"{base}/warehouses", headers=headers,
                                    json={"code": f"WH-{code}", "name": f"{code} warehouse"})).json()
            location = run(request(app, "POST", f"{base}/warehouses/{warehouse['id']}/locations",
                                   headers=headers, json={"code": f"{code}-BIN", "name": f"{code} bin",
                                                         "location_type": "bin"})).json()
            locations.append((warehouse, location))
        (source_warehouse, source), (destination_warehouse, destination) = locations
        receipt = run(request(app, "POST", f"{base}/inventory/movements", headers=headers,
                              json=movement(product["id"], "receipt", "4", "transfer-source-stock",
                                            warehouse_location_id=source["id"])))
        assert receipt.status_code == 200
        create_payload = {
            "source_warehouse_id": source_warehouse["id"], "source_location_id": source["id"],
            "destination_warehouse_id": destination_warehouse["id"],
            "destination_location_id": destination["id"],
            "product_id": product["id"], "quantity": "3",
            "idempotency_key": "transfer-create-001", "external_reference": "MOVE-EXT-1",
        }
        created = run(request(app, "POST", f"{base}/warehouse-transfers", headers=headers,
                              json=create_payload))
        assert created.status_code == 201, created.text
        transfer = created.json()
        dispatch_url = f"{base}/warehouse-transfers/{transfer['id']}/dispatch"
        dispatched = run(request(app, "POST", dispatch_url, headers=headers))
        assert dispatched.status_code == 200, dispatched.text
        transit_id = dispatched.json()["in_transit_location_id"]
        assert dispatched.json()["status"] == "in_transit"

        interim = run(request(app, "GET", f"{base}/inventory/location-balances?product_id={product['id']}",
                              headers=headers)).json()["items"]
        interim_by_location = {row["warehouse_location_id"]: row for row in interim}
        assert interim_by_location[source["id"]]["on_hand"] == "1.000000"
        assert interim_by_location[transit_id]["on_hand"] == "3.000000"
        assert run(request(app, "GET", f"{base}/inventory/balances", headers=headers)).json()["items"][0]["on_hand"] == "4.000000"

        receive_url = f"{base}/warehouse-transfers/{transfer['id']}/receive"
        received = run(request(app, "POST", receive_url, headers=headers))
        assert received.status_code == 200, received.text
        assert received.json()["status"] == "received"
        replay = run(request(app, "POST", receive_url, headers=headers))
        assert replay.status_code == 200
        assert replay.json()["id"] == transfer["id"]

        final = run(request(app, "GET", f"{base}/inventory/location-balances?product_id={product['id']}",
                            headers=headers)).json()["items"]
        final_by_location = {row["warehouse_location_id"]: row for row in final}
        assert final_by_location[source["id"]]["on_hand"] == "1.000000"
        assert final_by_location[transit_id]["on_hand"] == "0.000000"
        assert final_by_location[destination["id"]]["on_hand"] == "3.000000"
        assert run(request(app, "GET", f"{base}/inventory/balances", headers=headers)).json()["items"][0]["on_hand"] == "4.000000"
        ledger = run(request(app, "GET", f"{base}/inventory/movements?product_id={product['id']}",
                             headers=headers)).json()["items"]
        assert len(ledger) == 5
    finally:
        engine.dispose()


def test_product_barcodes_are_tenant_unique_searchable_and_managed_safely(tmp_path):
    app, engine, factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        assert len(product["barcodes"]) == 1
        assert product["barcodes"][0]["barcode"] == "1234567890"
        assert product["barcodes"][0]["is_primary"] is True
        alternate = run(request(app, "POST", f"{base}/products/{product['id']}/barcodes",
                                headers=headers, json={"barcode": "ALT-123"}))
        assert alternate.status_code == 201, alternate.text
        assert alternate.json()["is_primary"] is False

        searched = run(request(app, "GET", f"{base}/products?search=ALT-123", headers=headers))
        assert [row["id"] for row in searched.json()["items"]] == [product["id"]]
        duplicate = run(request(app, "POST", f"{base}/products/{product['id']}/barcodes",
                                headers=headers, json={"barcode": "ALT-123"}))
        assert duplicate.status_code == 409
        duplicate_primary = run(request(app, "POST", f"{base}/products/{product['id']}/barcodes",
                                        headers=headers, json={"barcode": "1234567890"}))
        assert duplicate_primary.status_code == 409
        remove_primary = run(request(
            app, "DELETE", f"{base}/products/{product['id']}/barcodes/{product['barcodes'][0]['id']}",
            headers=headers,
        ))
        assert remove_primary.status_code == 409

        second = run(request(app, "POST", "/api/v1/auth/register",
                             json=register_payload("other-stock@example.com", "other-stock-org"))).json()
        second_headers = {"Authorization": f"Bearer {second['access_token']}"}
        second_org = second["organization"]["id"]
        unit = run(request(app, "POST", f"/api/v1/organizations/{second_org}/inventory/units",
                           headers=second_headers,
                           json={"code": "EA", "name": "Each", "decimal_places": 0})).json()
        same_code_other_tenant = run(request(
            app, "POST", f"/api/v1/organizations/{second_org}/inventory/products",
            headers=second_headers,
            json={"sku": "OTHER-1", "name": "Other tenant item", "unit_id": unit["id"],
                  "barcode": "ALT-123"},
        ))
        assert same_code_other_tenant.status_code == 201, same_code_other_tenant.text

        removed = run(request(
            app, "DELETE", f"{base}/products/{product['id']}/barcodes/{alternate.json()['id']}",
            headers=headers,
        ))
        assert removed.status_code == 204
        with factory() as session:
            assert session.scalar(select(InventoryProductBarcode).where(
                InventoryProductBarcode.organization_id == org_id,
                InventoryProductBarcode.product_id == product["id"],
                InventoryProductBarcode.barcode == "ALT-123",
            )) is None

        changed_primary = run(request(
            app, "PATCH", f"{base}/products/{product['id']}", headers=headers,
            json={"barcode": "NEW-PRIMARY"},
        ))
        assert changed_primary.status_code == 200, changed_primary.text
        assert changed_primary.json()["barcode"] == "NEW-PRIMARY"
        assert [(item["barcode"], item["is_primary"])
                for item in changed_primary.json()["barcodes"]] == [("NEW-PRIMARY", True)]
        cleared_primary = run(request(
            app, "PATCH", f"{base}/products/{product['id']}", headers=headers,
            json={"barcode": None},
        ))
        assert cleared_primary.status_code == 200, cleared_primary.text
        assert cleared_primary.json()["barcodes"] == []
    finally:
        engine.dispose()


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
        reconciliation = run(request(app, "GET", f"{base}/reconciliation", headers=headers))
        assert reconciliation.status_code == 200
        assert reconciliation.json()["reconciled"] is True
        assert reconciliation.json()["mismatch_count"] == 0
        assert reconciliation.json()["items"][0]["ledger_on_hand"] == "4.000000"
        with factory.begin() as session:
            stored = session.scalar(select(InventoryStockBalance).where(
                InventoryStockBalance.product_id == product["id"]))
            stored.on_hand = Decimal("5")
        mismatch = run(request(app, "GET", f"{base}/reconciliation", headers=headers))
        assert mismatch.status_code == 200
        assert mismatch.json()["reconciled"] is False
        assert mismatch.json()["mismatch_count"] == 1
        assert mismatch.json()["items"][0]["reconciled"] is False
        assert mismatch.json()["items"][0]["balance_on_hand"] == "5.000000"
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


def test_product_families_have_stockable_variants_and_tenant_safe_lifecycle(tmp_path):
    app, engine, _factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        family_response = run(request(app, "POST", f"{base}/products", headers=headers, json={
            "sku": "METER-FAMILY", "name": "Industrial meter", "kind": "family",
            "unit_id": product["unit_id"],
        }))
        assert family_response.status_code == 201, family_response.text
        family = family_response.json()
        assert family["kind"] == "family"
        assert family["family_id"] is None
        assert family["variant_attributes"] == {}

        incomplete_variant = run(request(app, "POST", f"{base}/products", headers=headers, json={
            "sku": "METER-INCOMPLETE", "name": "Meter without variant values",
            "family_id": family["id"], "unit_id": product["unit_id"],
        }))
        assert incomplete_variant.status_code == 422

        variant_response = run(request(app, "POST", f"{base}/products", headers=headers, json={
            "sku": "METER-RED-100", "name": "Red meter, 0–100", "family_id": family["id"],
            "variant_attributes": {"Colour": "Red", "Range": "0–100"},
            "unit_id": product["unit_id"],
        }))
        assert variant_response.status_code == 201, variant_response.text
        variant = variant_response.json()
        assert variant["kind"] == "sku"
        assert variant["family_id"] == family["id"]
        assert variant["variant_attributes"] == {"Colour": "Red", "Range": "0–100"}

        base_product_family_attempt = run(request(app, "POST", f"{base}/products", headers=headers, json={
            "sku": "BAD-NESTED", "name": "Invalid child", "family_id": product["id"],
            "variant_attributes": {"Colour": "Blue"}, "unit_id": product["unit_id"],
        }))
        assert base_product_family_attempt.status_code == 422

        family_movement = run(request(app, "POST", f"{base}/movements", headers=headers, json=movement(
            family["id"], "receipt", "1", "family-stock-blocked",
        )))
        assert family_movement.status_code == 409
        family_archive = run(request(app, "POST", f"{base}/products/{family['id']}/archive", headers=headers))
        assert family_archive.status_code == 409

        balances = run(request(app, "GET", f"{base}/balances", headers=headers)).json()["items"]
        assert {row["product_id"] for row in balances} == {product["id"], variant["id"]}
        variant_archive = run(request(app, "POST", f"{base}/products/{variant['id']}/archive", headers=headers))
        assert variant_archive.status_code == 204
        family_archive = run(request(app, "POST", f"{base}/products/{family['id']}/archive", headers=headers))
        assert family_archive.status_code == 204
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
        original_receipt = run(request(
            app, "POST", f"/api/v1/organizations/{org_id}/inventory/movements", headers=headers,
            json=movement(product["id"], "receipt", "2", "tenant-reversal-source"),
        ))
        assert original_receipt.status_code == 200
        other = run(request(app, "POST", "/api/v1/auth/register",
                            json=register_payload("other-stock@example.com", "other-stock-org"))).json()
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        other_org = other["organization"]["id"]
        cross_tenant = run(request(app, "GET", f"/api/v1/organizations/{other_org}/inventory/products",
                                   headers=headers))
        assert cross_tenant.status_code == 404
        cross_tenant_reconciliation = run(request(
            app, "GET", f"/api/v1/organizations/{other_org}/inventory/reconciliation", headers=headers))
        assert cross_tenant_reconciliation.status_code == 404
        cross_tenant_reversal = run(request(
            app, "POST",
            f"/api/v1/organizations/{other_org}/inventory/movements/{original_receipt.json()['id']}/reverse",
            headers=other_headers,
            json={"idempotency_key": "tenant-reversal", "note": "Cross-tenant attempt"},
        ))
        assert cross_tenant_reversal.status_code == 404

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
        reconciliation_denied = run(request(
            app, "GET", f"/api/v1/organizations/{org_id}/inventory/reconciliation",
            headers=reader_headers))
        assert reconciliation_denied.status_code == 403
        reversal_denied = run(request(
            app, "POST",
            f"/api/v1/organizations/{org_id}/inventory/movements/{original_receipt.json()['id']}/reverse",
            headers=reader_headers,
            json={"idempotency_key": "reader-reversal", "note": "Permission check"},
        ))
        assert reversal_denied.status_code == 403
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
        assert response.json()["error"]["code"] == "http_error"
        balance = run(request(app, "GET", f"{base}/balances", headers=headers)).json()["items"][0]
        assert balance["on_hand"] == "1.000000"
    finally:
        engine.dispose()


def test_traced_count_supports_multiple_lots_serials_and_full_stocktake_validation(tmp_path):
    app, engine, _factory, org_id, headers, product = setup_inventory(tmp_path)
    base = f"/api/v1/organizations/{org_id}/inventory"
    try:
        lot_product = run(request(app, "POST", f"{base}/products", headers=headers, json={
            "sku": "LOT-100", "name": "Lot tracked item", "unit_id": product["unit_id"],
            "tracking_mode": "lot",
        })).json()
        serial_product = run(request(app, "POST", f"{base}/products", headers=headers, json={
            "sku": "SER-100", "name": "Serialized item", "unit_id": product["unit_id"],
            "tracking_mode": "serial",
        })).json()
        for lot_code, quantity in (("LOT-A", "4"), ("LOT-B", "3")):
            received = run(request(app, "POST", f"{base}/movements", headers=headers, json=movement(
                lot_product["id"], "receipt", quantity, f"receive-{lot_code}", lot_code=lot_code,
            )))
            assert received.status_code == 200
        serial_receipt = run(request(app, "POST", f"{base}/movements", headers=headers, json=movement(
            serial_product["id"], "receipt", "1", "receive-SN-100", serial_code="SN-100",
        )))
        assert serial_receipt.status_code == 200

        count = run(request(app, "POST", f"{base}/counts", headers=headers, json={
            "count_type": "cycle", "note": "Trace-code recount", "lines": [
                {"product_id": lot_product["id"], "lot_code": "LOT-A", "counted_quantity": "3",
                 "reason_code": "damage"},
                {"product_id": lot_product["id"], "lot_code": "LOT-B", "counted_quantity": "3",
                 "reason_code": "no_variance"},
                {"product_id": serial_product["id"], "serial_code": "SN-100", "counted_quantity": "0",
                 "reason_code": "loss"},
            ],
        }))
        assert count.status_code == 201, count.text
        count_body = count.json()
        assert len(count_body["lines"]) == 3
        expected_by_trace = {line["lot_code"] or line["serial_code"]: line["expected_on_hand"]
                             for line in count_body["lines"]}
        assert expected_by_trace == {"LOT-A": "4.000000", "LOT-B": "3.000000", "SN-100": "1.000000"}
        assert run(request(app, "POST", f"{base}/counts/{count_body['id']}/submit", headers=headers)).status_code == 200

        other = run(request(app, "POST", "/api/v1/auth/register",
                            json=register_payload("trace-approver@example.com", "trace-approver"))).json()
        role = run(request(app, "POST", f"/api/v1/organizations/{org_id}/roles", headers=headers,
                           json={"name": "Trace count approver", "permissions": [
                               "inventory.counts.read", "inventory.counts.approve"]})).json()
        run(request(app, "POST", f"/api/v1/organizations/{org_id}/members", headers=headers,
                    json={"user_id": other["user"]["id"], "role_id": role["id"]}))
        login = run(request(app, "POST", "/api/v1/auth/login", json={
            "email": "trace-approver@example.com", "password": "a-strong-password-123",
            "organization_id": org_id,
        })).json()
        approver_headers = {"Authorization": f"Bearer {login['access_token']}"}
        approved = run(request(app, "POST", f"{base}/counts/{count_body['id']}/approve",
                               headers=approver_headers))
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"
        balances = run(request(app, "GET", f"{base}/balances", headers=headers)).json()["items"]
        by_product = {row["product_id"]: row["on_hand"] for row in balances}
        assert by_product[lot_product["id"]] == "6.000000"
        assert by_product[serial_product["id"]] == "0.000000"

        incomplete = run(request(app, "POST", f"{base}/counts", headers=headers, json={
            "count_type": "full_stocktake", "lines": [
                {"product_id": product["id"], "counted_quantity": "0", "reason_code": "no_variance"},
                {"product_id": lot_product["id"], "lot_code": "LOT-A", "counted_quantity": "3", "reason_code": "no_variance"},
            ],
        }))
        assert incomplete.status_code == 422

        full = run(request(app, "POST", f"{base}/counts", headers=headers, json={
            "count_type": "full_stocktake", "lines": [
                {"product_id": product["id"], "counted_quantity": "0", "reason_code": "no_variance"},
                {"product_id": lot_product["id"], "lot_code": "LOT-A", "counted_quantity": "3", "reason_code": "no_variance"},
                {"product_id": lot_product["id"], "lot_code": "LOT-B", "counted_quantity": "3", "reason_code": "no_variance"},
            ],
        }))
        assert full.status_code == 201, full.text
        assert full.json()["count_type"] == "full_stocktake"
    finally:
        engine.dispose()
