"""PostgreSQL inventory RLS and stock-posting concurrency regressions."""
from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.skipif(
    os.getenv("OOSYS_RUN_INVENTORY_POSTGRES") != "1",
    reason="requires migrated PostgreSQL and a restricted application role",
)


def _new_app():
    settings = Settings(
        _env_file=None,
        database_url=SecretStr(os.environ["OOSYS_DATABASE_URL"]),
        allow_self_registration=True,
        smtp_host="localhost",
        email_from="noreply@example.com",
        invitation_accept_url="https://example.com/accept",
    )
    return create_app(settings), uuid4().hex[:12]


def _register(client: TestClient, email: str, slug: str) -> dict:
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Inventory-Strong-Password-123",
        "full_name": "Inventory Test",
        "organization_name": f"Inventory {slug}",
        "organization_slug": slug,
    })
    assert response.status_code == 201, response.text
    return response.json()


def _product(client: TestClient, account: dict, sku: str) -> dict:
    organization_id = account["organization"]["id"]
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    unit = client.post(
        f"/api/v1/organizations/{organization_id}/inventory/units",
        headers=headers,
        json={"code": "EA", "name": "Each", "decimal_places": 0},
    )
    assert unit.status_code == 201, unit.text
    product = client.post(
        f"/api/v1/organizations/{organization_id}/inventory/products",
        headers=headers,
        json={"sku": sku, "name": "Test item", "unit_id": unit.json()["id"],
              "barcode": f"BC-{sku}"},
    )
    assert product.status_code == 201, product.text
    return product.json()


def _warehouse(client: TestClient, account: dict, code: str) -> tuple[dict, dict]:
    organization_id = account["organization"]["id"]
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    warehouse = client.post(
        f"/api/v1/organizations/{organization_id}/warehouses",
        headers=headers,
        json={"code": code, "name": f"Warehouse {code}"},
    )
    assert warehouse.status_code == 201, warehouse.text
    location = client.post(
        f"/api/v1/organizations/{organization_id}/warehouses/{warehouse.json()['id']}/locations",
        headers=headers,
        json={"code": "RECEIVE-A", "name": "Receiving A", "location_type": "receiving"},
    )
    assert location.status_code == 201, location.text
    return warehouse.json(), location.json()


def _post_receipt(app, organization_id: str, token: str, product_id: str,
                  quantity: str, idempotency_key: str) -> tuple[int, dict]:
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/organizations/{organization_id}/inventory/movements",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": product_id, "movement_type": "receipt",
                  "quantity": quantity, "idempotency_key": idempotency_key},
        )
        return response.status_code, response.json()


def test_inventory_rls_hides_other_organization_products():
    app, suffix = _new_app()
    with TestClient(app) as client:
        first = _register(client, f"inv-a-{suffix}@example.com", f"inv-a-{suffix}")
        second = _register(client, f"inv-b-{suffix}@example.com", f"inv-b-{suffix}")
        product_a = _product(client, first, f"A-{suffix}")
        product_b = _product(client, second, f"B-{suffix}")
        warehouse_a, location_a = _warehouse(client, first, f"WA-{suffix}")
        warehouse_b, location_b = _warehouse(client, second, f"WB-{suffix}")
        receipt_a = client.post(
            f"/api/v1/organizations/{first['organization']['id']}/warehouses/{warehouse_a['id']}/receipts",
            headers={"Authorization": f"Bearer {first['access_token']}"},
            json={"receiving_location_id": location_a["id"], "idempotency_key": f"rls-receipt-a-{suffix}",
                  "lines": [{"product_id": product_a["id"], "quantity": "1"}]},
        )
        receipt_b = client.post(
            f"/api/v1/organizations/{second['organization']['id']}/warehouses/{warehouse_b['id']}/receipts",
            headers={"Authorization": f"Bearer {second['access_token']}"},
            json={"receiving_location_id": location_b["id"], "idempotency_key": f"rls-receipt-b-{suffix}",
                  "lines": [{"product_id": product_b["id"], "quantity": "1"}]},
        )
        assert receipt_a.status_code == receipt_b.status_code == 201
        destination_a = client.post(
            f"/api/v1/organizations/{first['organization']['id']}/warehouses/{warehouse_a['id']}/locations",
            headers={"Authorization": f"Bearer {first['access_token']}"},
            json={"code": "DEST-A", "name": "Destination A", "location_type": "bin"},
        )
        destination_b = client.post(
            f"/api/v1/organizations/{second['organization']['id']}/warehouses/{warehouse_b['id']}/locations",
            headers={"Authorization": f"Bearer {second['access_token']}"},
            json={"code": "DEST-B", "name": "Destination B", "location_type": "bin"},
        )
        assert destination_a.status_code == destination_b.status_code == 201
        transfer_a = client.post(
            f"/api/v1/organizations/{first['organization']['id']}/warehouse-transfers",
            headers={"Authorization": f"Bearer {first['access_token']}"},
            json={"source_warehouse_id": warehouse_a["id"], "source_location_id": location_a["id"],
                  "destination_warehouse_id": warehouse_a["id"],
                  "destination_location_id": destination_a.json()["id"],
                  "product_id": product_a["id"], "quantity": "1",
                  "idempotency_key": f"rls-transfer-a-{suffix}"},
        )
        transfer_b = client.post(
            f"/api/v1/organizations/{second['organization']['id']}/warehouse-transfers",
            headers={"Authorization": f"Bearer {second['access_token']}"},
            json={"source_warehouse_id": warehouse_b["id"], "source_location_id": location_b["id"],
                  "destination_warehouse_id": warehouse_b["id"],
                  "destination_location_id": destination_b.json()["id"],
                  "product_id": product_b["id"], "quantity": "1",
                  "idempotency_key": f"rls-transfer-b-{suffix}"},
        )
        assert transfer_a.status_code == transfer_b.status_code == 201
        outbound_a = client.post(
            f"/api/v1/organizations/{first['organization']['id']}/warehouses/{warehouse_a['id']}/outbound-orders",
            headers={"Authorization": f"Bearer {first['access_token']}"},
            json={"idempotency_key": f"rls-outbound-a-{suffix}",
                  "lines": [{"product_id": product_a["id"],
                             "source_location_id": destination_a.json()["id"], "quantity": "1"}]},
        )
        outbound_b = client.post(
            f"/api/v1/organizations/{second['organization']['id']}/warehouses/{warehouse_b['id']}/outbound-orders",
            headers={"Authorization": f"Bearer {second['access_token']}"},
            json={"idempotency_key": f"rls-outbound-b-{suffix}",
                  "lines": [{"product_id": product_b["id"],
                             "source_location_id": destination_b.json()["id"], "quantity": "1"}]},
        )
        assert outbound_a.status_code == outbound_b.status_code == 201
        receipt_a_posted = client.post(
            f"/api/v1/organizations/{first['organization']['id']}/warehouses/{warehouse_a['id']}"
            f"/receipts/{receipt_a.json()['id']}/post",
            headers={"Authorization": f"Bearer {first['access_token']}"},
        )
        assert receipt_a_posted.status_code == 200, receipt_a_posted.text

        # Exercise the PostgreSQL policy directly using the restricted app role,
        # bypassing the route's explicit organization check.
        with app.state.identity_engine.begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"),
                               {"tenant": first["organization"]["id"]})
            visible = connection.execute(text(
                "SELECT id FROM inventory_products WHERE id IN (:a, :b) ORDER BY id"
            ), {"a": product_a["id"], "b": product_b["id"]}).scalars().all()
            assert visible == [product_a["id"]]
            visible_barcodes = connection.execute(text(
                "SELECT product_id FROM inventory_product_barcodes "
                "WHERE product_id IN (:a, :b) ORDER BY product_id"
            ), {"a": product_a["id"], "b": product_b["id"]}).scalars().all()
            assert visible_barcodes == [product_a["id"]]
            visible_warehouses = connection.execute(text(
                "SELECT id FROM warehouses WHERE id IN (:a, :b) ORDER BY id"
            ), {"a": warehouse_a["id"], "b": warehouse_b["id"]}).scalars().all()
            assert visible_warehouses == [warehouse_a["id"]]
            visible_locations = connection.execute(text(
                "SELECT id FROM warehouse_locations WHERE id IN (:a, :b) ORDER BY id"
            ), {"a": location_a["id"], "b": location_b["id"]}).scalars().all()
            assert visible_locations == [location_a["id"]]
            visible_receipts = connection.execute(text(
                "SELECT id FROM warehouse_receipts WHERE id IN (:a, :b) ORDER BY id"
            ), {"a": receipt_a.json()["id"], "b": receipt_b.json()["id"]}).scalars().all()
            assert visible_receipts == [receipt_a.json()["id"]]
            visible_putaway = connection.execute(text(
                "SELECT id FROM warehouse_putaway_tasks WHERE receipt_id = :receipt_id"
            ), {"receipt_id": receipt_a.json()["id"]}).scalars().all()
            assert len(visible_putaway) == 1
            visible_transfers = connection.execute(text(
                "SELECT id FROM warehouse_transfers WHERE id IN (:a, :b) ORDER BY id"
            ), {"a": transfer_a.json()["id"], "b": transfer_b.json()["id"]}).scalars().all()
            assert visible_transfers == [transfer_a.json()["id"]]
            visible_outbound = connection.execute(text(
                "SELECT id FROM warehouse_outbound_orders WHERE id IN (:a, :b) ORDER BY id"
            ), {"a": outbound_a.json()["id"], "b": outbound_b.json()["id"]}).scalars().all()
            assert visible_outbound == [outbound_a.json()["id"]]


def test_concurrent_inventory_receipts_preserve_balance_and_replay_once():
    app, suffix = _new_app()
    with TestClient(app) as client:
        owner = _register(client, f"inv-race-{suffix}@example.com", f"inv-race-{suffix}")
        product = _product(client, owner, f"R-{suffix}")
        organization_id = owner["organization"]["id"]
        token = owner["access_token"]

        # Distinct keys must serialize on the balance row without losing updates.
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda key: _post_receipt(
                app, organization_id, token, product["id"], "5", key
            ), (f"receipt-a-{suffix}", f"receipt-b-{suffix}")))
        assert [status for status, _ in results] == [200, 200]
        headers = {"Authorization": f"Bearer {token}"}
        balances = client.get(
            f"/api/v1/organizations/{organization_id}/inventory/balances", headers=headers
        )
        assert balances.status_code == 200, balances.text
        balance = next(item for item in balances.json()["items"]
                       if item["product_id"] == product["id"])
        assert balance["on_hand"] == "10.000000"

        # Concurrent retries with one key return one immutable ledger row.
        with ThreadPoolExecutor(max_workers=2) as pool:
            retries = list(pool.map(lambda _: _post_receipt(
                app, organization_id, token, product["id"], "3", f"same-key-{suffix}"
            ), range(2)))
        assert [status for status, _ in retries] == [200, 200]
        assert retries[0][1]["id"] == retries[1][1]["id"]
        final = client.get(
            f"/api/v1/organizations/{organization_id}/inventory/balances", headers=headers
        )
        balance = next(item for item in final.json()["items"]
                       if item["product_id"] == product["id"])
        assert balance["on_hand"] == "13.000000"


def test_inventory_ledger_rejects_direct_update_and_delete():
    app, suffix = _new_app()
    with TestClient(app) as client:
        owner = _register(client, f"inv-append-{suffix}@example.com", f"inv-append-{suffix}")
        product = _product(client, owner, f"APPEND-{suffix}")
        organization_id = owner["organization"]["id"]
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        posted = client.post(
            f"/api/v1/organizations/{organization_id}/inventory/movements",
            headers=headers,
            json={"product_id": product["id"], "movement_type": "receipt",
                  "quantity": "1", "idempotency_key": f"append-{suffix}"},
        )
        assert posted.status_code == 200, posted.text
        movement_id = posted.json()["id"]

        with pytest.raises(DBAPIError, match="append-only"):
            with app.state.identity_engine.begin() as connection:
                connection.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"),
                                   {"tenant": organization_id})
                connection.execute(text("""
                    UPDATE inventory_movements SET note = 'tampered'
                    WHERE organization_id = :tenant AND id = :movement_id
                """), {"tenant": organization_id, "movement_id": movement_id})
        with pytest.raises(DBAPIError, match="append-only"):
            with app.state.identity_engine.begin() as connection:
                connection.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"),
                                   {"tenant": organization_id})
                connection.execute(text("""
                    DELETE FROM inventory_movements
                    WHERE organization_id = :tenant AND id = :movement_id
                """), {"tenant": organization_id, "movement_id": movement_id})
