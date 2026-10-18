"""Tests for explicit, lazy database infrastructure construction."""
import socket

import pytest
from sqlalchemy import text

from app.core.config import Settings
from app.core.database import (
    create_database_engine,
    create_session_factory,
    session_dependency,
)


def test_database_engine_requires_explicit_database_url() -> None:
    with pytest.raises(RuntimeError, match="OOSYS_DATABASE_URL"):
        create_database_engine(Settings(_env_file=None))


def test_engine_construction_does_not_connect_to_external_services(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("engine construction must not connect to the database")

    monkeypatch.setattr(socket.socket, "connect", fail_if_called)
    settings = Settings(
        database_url="postgresql+psycopg://user:secret@127.0.0.1/oosys",
        _env_file=None,
    )

    engine = create_database_engine(settings)
    try:
        assert engine.url.database == "oosys"
        assert "secret" not in repr(settings)
    finally:
        engine.dispose()


def test_session_factory_executes_against_explicit_engine() -> None:
    settings = Settings(database_url="sqlite+pysqlite:///:memory:", _env_file=None)
    engine = create_database_engine(settings)
    try:
        factory = create_session_factory(engine)
        with factory() as session:
            assert session.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()


def test_session_dependency_rolls_back_when_use_case_raises() -> None:
    settings = Settings(database_url="sqlite+pysqlite:///:memory:", _env_file=None)
    engine = create_database_engine(settings)
    try:
        dependency = session_dependency(create_session_factory(engine))
        generator = dependency()
        session = next(generator)
        session.execute(text("SELECT 1"))

        with pytest.raises(RuntimeError, match="use case failed"):
            generator.throw(RuntimeError("use case failed"))

        assert not session.in_transaction()
    finally:
        engine.dispose()
