"""Create deployment-wide non-secret platform settings.

Revision ID: 20261018_0001
Revises:
Create Date: 2026-10-18
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261018_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial platform configuration table."""
    op.create_table(
        "platform_settings",
        sa.Column("setting_key", sa.String(length=100), primary_key=True),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("length(setting_key) > 0", name="ck_platform_settings_key_nonempty"),
    )


def downgrade() -> None:
    """Remove only the table introduced by this revision."""
    op.drop_table("platform_settings")
