"""Explicitly constructed SQLAlchemy engine and request-scoped sessions.

Importing this module never opens a connection or creates a global engine.
"""
from collections.abc import Generator
from typing import Callable

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    """Build an engine on demand; fail closed when no URL is configured."""
    if settings.database_url is None:
        raise RuntimeError("OOSYS_DATABASE_URL must be configured before database use")

    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create sessions bound to the supplied engine; transaction policy stays in use cases."""
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def session_dependency(
    factory: sessionmaker[Session],
) -> Callable[[], Generator[Session, None, None]]:
    """Create a FastAPI-compatible dependency with rollback and close guarantees."""
    def get_session() -> Generator[Session, None, None]:
        with factory() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    return get_session
