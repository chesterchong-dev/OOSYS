"""Shared SQLAlchemy metadata base for application-owned tables."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class whose metadata is the migration source of truth."""
