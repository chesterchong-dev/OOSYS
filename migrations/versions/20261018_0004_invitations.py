"""Add invitation persistence and backfill hierarchy permissions for existing owners.

Revision ID: 20261018_0004
Revises: 20261018_0003
"""
from typing import Sequence
import uuid
from alembic import op
import sqlalchemy as sa

revision: str = "20261018_0004"
down_revision: str | None = "20261018_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("identity_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False), sa.Column("role_id", sa.String(36), nullable=False),
        sa.Column("invited_by_user_id", sa.String(36), sa.ForeignKey("identity_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id", "role_id"], ["identity_roles.organization_id", "identity_roles.id"],
            ondelete="RESTRICT", name="fk_identity_invitation_role_same_org"))
    op.create_index("ix_identity_invitation_org_email", "identity_invitations", ["organization_id", "email"])
    conn = op.get_bind()
    roles = conn.execute(sa.text("SELECT organization_id, id FROM identity_roles WHERE is_system IS TRUE AND name = 'Owner'")).all()
    keys = conn.execute(sa.text("SELECT key FROM identity_permissions WHERE key LIKE 'organization.units.%'")).scalars().all()
    for organization_id, role_id in roles:
        for key in keys:
            exists = conn.execute(sa.text("SELECT 1 FROM identity_role_permissions WHERE organization_id=:org AND role_id=:role AND permission_key=:key"),
                {"org": organization_id, "role": role_id, "key": key}).first()
            if not exists:
                conn.execute(sa.text("INSERT INTO identity_role_permissions (id, organization_id, role_id, permission_key) VALUES (:id,:org,:role,:key)"),
                    {"id": str(uuid.uuid4()), "org": organization_id, "role": role_id, "key": key})


def downgrade() -> None:
    op.drop_index("ix_identity_invitation_org_email", table_name="identity_invitations")
    op.drop_table("identity_invitations")
    op.execute("DELETE FROM identity_role_permissions WHERE permission_key LIKE 'organization.units.%'")
