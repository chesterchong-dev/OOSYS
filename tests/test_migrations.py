"""Migration tests use isolated SQLite databases, not PostgreSQL."""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.db_base import Base
from app.platform_config import models  # noqa: F401 - register metadata
from app.identity import models as identity_models  # noqa: F401 - register identity metadata
from app.inventory import models as inventory_models  # noqa: F401 - register inventory metadata
from app.warehouse import models as warehouse_models  # noqa: F401 - register warehouse metadata

ROOT = Path(__file__).resolve().parents[1]


def migration_config():
    """Build an Alembic config rooted at the checked-out project."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def upgrade(config: Config, engine) -> None:
    """Run Alembic using an explicit test connection."""
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        config.attributes.pop("connection", None)


def test_initial_migration_creates_expected_schema_and_is_repeatable(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    try:
        assert "platform_settings" not in inspect(engine).get_table_names()
        config = migration_config()
        upgrade(config, engine)
        upgrade(config, engine)

        inspector = inspect(engine)
        assert "platform_settings" in inspector.get_table_names()
        assert "identity_users" in inspector.get_table_names()
        assert "identity_organizations" in inspector.get_table_names()
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM identity_permissions").scalar_one() == 26
        columns = {column["name"]: column for column in inspector.get_columns("platform_settings")}
        assert set(columns) == {
            "setting_key", "value_json", "description", "created_at", "updated_at"
        }
        assert columns["setting_key"]["primary_key"] == 1
        assert columns["value_json"]["nullable"] is False
        assert columns["description"]["nullable"] is True
        assert any(
            item["name"] == "ck_platform_settings_key_nonempty"
            for item in inspector.get_check_constraints("platform_settings")
        )
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "20261024_0015"
        assert {"inventory_products", "inventory_product_barcodes", "inventory_stock_balances", "inventory_movements",
                "inventory_counts", "inventory_count_lines", "warehouses", "warehouse_locations"}.issubset(
                    inspector.get_table_names())
        assert {"lot_code", "serial_code", "expires_at"}.issubset(
            {column["name"] for column in inspector.get_columns("inventory_count_lines")}
        )
        product_columns = {column["name"] for column in inspector.get_columns("inventory_products")}
        assert {"kind", "family_id", "variant_attributes"}.issubset(product_columns)
        barcode_columns = {column["name"] for column in inspector.get_columns("inventory_product_barcodes")}
        assert {"id", "organization_id", "product_id", "barcode", "created_at"}.issubset(barcode_columns)
        movement_columns = {column["name"] for column in inspector.get_columns("inventory_movements")}
        assert {"reversal_of_movement_id", "warehouse_location_id"}.issubset(movement_columns)
        location_columns = {column["name"] for column in inspector.get_columns("warehouse_locations")}
        assert {"organization_id", "warehouse_id", "parent_location_id", "location_type",
                "capacity_limit", "capacity_unit"}.issubset(location_columns)
        assert "platform_settings" in Base.metadata.tables
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO platform_settings "
                    "(setting_key, value_json) VALUES (:key, :value)"
                ),
                {"key": "valid.setting", "value": '"ok"'},
            )
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO platform_settings "
                        "(setting_key, value_json) VALUES (:key, :value)"
                    ),
                    {"key": "", "value": '"invalid"'},
                )
    finally:
        engine.dispose()


def test_migration_can_downgrade_and_upgrade_again(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'cycle.db'}")
    try:
        config = migration_config()
        upgrade(config, engine)
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "base")
            config.attributes.pop("connection", None)
        assert "platform_settings" not in inspect(engine).get_table_names()
        upgrade(config, engine)
        assert "platform_settings" in inspect(engine).get_table_names()
        assert "identity_users" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_product_barcode_migration_backfills_existing_primary_codes(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'barcode-backfill.db'}")
    try:
        config = migration_config()
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "20261024_0010")
            config.attributes.pop("connection", None)
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO identity_organizations (id, name, slug, status)
                VALUES ('org-1', 'Test', 'test-org', 'active')
            """))
            connection.execute(text("""
                INSERT INTO inventory_units (id, organization_id, code, name, decimal_places)
                VALUES ('unit-1', 'org-1', 'EA', 'Each', 0)
            """))
            connection.execute(text("""
                INSERT INTO inventory_products (id, organization_id, sku, name, unit_id, barcode)
                VALUES ('product-1', 'org-1', 'P-1', 'Test item', 'unit-1', 'LEGACY-001')
            """))
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            config.attributes.pop("connection", None)
        with engine.connect() as connection:
            row = connection.execute(text("""
                SELECT organization_id, product_id, barcode
                FROM inventory_product_barcodes
            """)).mappings().one()
            assert row == {"organization_id": "org-1", "product_id": "product-1",
                           "barcode": "LEGACY-001"}
    finally:
        engine.dispose()


def test_inventory_ledger_rejects_direct_update_and_delete(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'ledger-append-only.db'}")
    try:
        upgrade(migration_config(), engine)
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys = OFF")
            connection.commit()
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO inventory_movements
                    (id, organization_id, product_id, movement_type, quantity_delta,
                     reserved_delta, currency_code, idempotency_key, request_hash, note, actor_user_id)
                VALUES ('movement-1', 'org-1', 'product-1', 'receipt', 1, 0,
                        'MYR', 'migration-key', :request_hash, '', 'actor-1')
            """), {"request_hash": "0" * 64})

        with pytest.raises(DBAPIError, match="append-only"):
            with engine.begin() as connection:
                connection.execute(text(
                    "UPDATE inventory_movements SET note = 'tampered' WHERE id = 'movement-1'"
                ))
        with pytest.raises(DBAPIError, match="append-only"):
            with engine.begin() as connection:
                connection.execute(text(
                    "DELETE FROM inventory_movements WHERE id = 'movement-1'"
                ))
        with engine.connect() as connection:
            row = connection.execute(text(
                "SELECT note FROM inventory_movements WHERE id = 'movement-1'"
            )).scalar_one()
            assert row == ""
    finally:
        engine.dispose()


def test_migration_fails_closed_without_database_url(monkeypatch) -> None:
    monkeypatch.delenv("OOSYS_DATABASE_URL", raising=False)
    config = migration_config()
    config.set_main_option("sqlalchemy.url", "")
    with pytest.raises(RuntimeError, match="OOSYS_DATABASE_URL"):
        command.upgrade(config, "head")

