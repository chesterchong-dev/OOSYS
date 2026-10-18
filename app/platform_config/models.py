"""Persistence model for deployment-wide non-secret platform settings."""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base


class PlatformSetting(Base):
    """A non-secret setting shared by one OOSYS deployment.

    Credentials and tenant/user-specific preferences belong in their
    dedicated secret/configuration mechanisms, not this table.
    """

    __tablename__ = "platform_settings"

    setting_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
