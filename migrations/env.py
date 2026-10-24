"""Alembic environment with explicit connections and no import-time DB access."""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.core.db_base import Base
from app.core.config import Settings
from app.platform_config import models  # noqa: F401 - registers mapped tables
from app.identity import models as identity_models  # noqa: F401 - register identity tables
from app.inventory import models as inventory_models  # noqa: F401 - register inventory tables

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without creating a database connection."""
    url = config.get_main_option("sqlalchemy.url") or os.getenv("OOSYS_DATABASE_URL")
    if not url:
        database_url = Settings().database_url
        url = database_url.get_secret_value() if database_url else None
    if not url:
        raise RuntimeError("Set OOSYS_DATABASE_URL before running migrations.")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Use a supplied test/host connection or create an explicit migration engine."""
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
        return

    url = config.get_main_option("sqlalchemy.url") or os.getenv("OOSYS_DATABASE_URL")
    if not url:
        database_url = Settings().database_url
        url = database_url.get_secret_value() if database_url else None
    if not url:
        raise RuntimeError("Set OOSYS_DATABASE_URL before running migrations.")

    engine = create_engine(url, poolclass=NullPool, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
