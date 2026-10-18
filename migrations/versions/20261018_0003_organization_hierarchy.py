"""Add organisation hierarchy.

Revision ID: 20261018_0003
Revises: 20261018_0002
"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20261018_0003"
down_revision: str | None = "20261018_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("identity_organization_units",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("parent_id", sa.String(36)), sa.Column("unit_type", sa.String(24), nullable=False),
        sa.Column("name", sa.String(160), nullable=False), sa.Column("code", sa.String(60)),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id", "parent_id"],
            ["identity_organization_units.organization_id", "identity_organization_units.id"],
            ondelete="RESTRICT", name="fk_identity_unit_parent_same_org"),
        sa.UniqueConstraint("organization_id", "id", name="uq_identity_unit_org_id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_identity_unit_org_code"),
        sa.CheckConstraint("unit_type IN ('business_unit','location','department','team')", name="ck_identity_unit_type"),
        sa.CheckConstraint("status IN ('active','archived')", name="ck_identity_unit_status"))
    op.create_index("ix_identity_unit_org_type", "identity_organization_units", ["organization_id", "unit_type"])
    op.bulk_insert(sa.table("identity_permissions", sa.column("key", sa.String(120)), sa.column("description", sa.String(255))), [
        {"key": "organization.units.read", "description": "View organisation hierarchy"},
        {"key": "organization.units.create", "description": "Create organisation hierarchy records"},
        {"key": "organization.units.update", "description": "Update organisation hierarchy records"},
        {"key": "organization.units.archive", "description": "Archive organisation hierarchy records"},
    ])


def downgrade() -> None:
    op.drop_index("ix_identity_unit_org_type", table_name="identity_organization_units")
    op.drop_table("identity_organization_units")
    op.execute("DELETE FROM identity_permissions WHERE key LIKE 'organization.units.%'")
