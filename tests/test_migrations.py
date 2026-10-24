"""Migration tests use isolated SQLite databases, not PostgreSQL."""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.db_base import Base
from app.platform_config import models  # noqa: F401 - register metadata
from app.identity import models as identity_models  # noqa: F401 - register identity metadata
from app.inventory import models as inventory_models  # noqa: F401 - register inventory metadata

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
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM identity_permissions").scalar_one() == 22
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
            assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "20261024_0008"
        assert {"inventory_products", "inventory_stock_balances", "inventory_movements",
                "inventory_counts", "inventory_count_lines"}.issubset(inspector.get_table_names())
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


def test_migration_fails_closed_without_database_url(monkeypatch) -> None:
    monkeypatch.delenv("OOSYS_DATABASE_URL", raising=False)
    config = migration_config()
    config.set_main_option("sqlalchemy.url", "")
    with pytest.raises(RuntimeError, match="OOSYS_DATABASE_URL"):
        command.upgrade(config, "head")
