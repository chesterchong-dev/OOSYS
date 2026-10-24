"""Add approval-controlled inventory count sessions.

Revision ID: 20261024_0008
Revises: 20261024_0007
"""
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0008"
down_revision: str | None = "20261024_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_counts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("count_number", sa.String(40), nullable=False),
        sa.Column("count_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("note", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("submitted_by_user_id", sa.String(36)),
        sa.Column("approved_by_user_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "id", name="uq_inventory_count_org_id"),
        sa.UniqueConstraint("organization_id", "count_number", name="uq_inventory_count_org_number"),
        sa.CheckConstraint("count_type IN ('cycle','full_stocktake')", name="ck_inventory_count_type"),
        sa.CheckConstraint("status IN ('draft','submitted','approved','rejected')", name="ck_inventory_count_status"),
    )
    op.create_index("ix_inventory_count_org_status_created", "inventory_counts",
                    ["organization_id", "status", "created_at"])

    op.create_table(
        "inventory_count_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("count_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("expected_on_hand", sa.Numeric(20, 6), nullable=False),
        sa.Column("counted_quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("balance_version", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(24), nullable=False),
        sa.Column("reason_note", sa.String(300), nullable=False, server_default=""),
        sa.UniqueConstraint("organization_id", "id", name="uq_inventory_count_line_org_id"),
        sa.UniqueConstraint("organization_id", "count_id", "product_id", name="uq_inventory_count_line_product"),
        sa.ForeignKeyConstraint(["organization_id", "count_id"], ["inventory_counts.organization_id", "inventory_counts.id"], ondelete="RESTRICT", name="fk_inventory_count_line_count_same_org"),
        sa.ForeignKeyConstraint(["organization_id", "product_id"], ["inventory_products.organization_id", "inventory_products.id"], ondelete="RESTRICT", name="fk_inventory_count_line_product_same_org"),
        sa.CheckConstraint("expected_on_hand >= 0 AND counted_quantity >= 0", name="ck_inventory_count_line_quantities_nonnegative"),
        sa.CheckConstraint("reason_code IN ('no_variance','damage','loss','found','data_correction','other')", name="ck_inventory_count_line_reason"),
    )
    op.create_index("ix_inventory_count_line_org_count", "inventory_count_lines",
                    ["organization_id", "count_id"])

    permissions = [
        {"key": "inventory.counts.read", "description": "View inventory counts and variance history"},
        {"key": "inventory.counts.write", "description": "Create and submit inventory counts"},
        {"key": "inventory.counts.approve", "description": "Approve inventory count variances"},
    ]
    op.bulk_insert(sa.table("identity_permissions", sa.column("key", sa.String(120)),
                            sa.column("description", sa.String(255))), permissions)
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" NO FORCE ROW LEVEL SECURITY')
    owners = conn.execute(sa.text(
        "SELECT organization_id, id FROM identity_roles WHERE name = 'Owner' AND is_system = TRUE"
    )).mappings().all()
    for owner in owners:
        conn.execute(sa.text("""
            INSERT INTO identity_role_permissions (id, organization_id, role_id, permission_key)
            VALUES (:id, :organization_id, :role_id, :permission_key)
        """), [
            {"id": str(uuid4()), "organization_id": owner["organization_id"],
             "role_id": owner["id"], "permission_key": permission["key"]}
            for permission in permissions
        ])
    if conn.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" FORCE ROW LEVEL SECURITY')
        for table in ("inventory_counts", "inventory_count_lines"):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(f"""CREATE POLICY {table}_tenant ON {table}
                USING (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))
                WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        for table in ("inventory_count_lines", "inventory_counts"):
            op.execute(f'DROP POLICY IF EXISTS {table}_tenant ON "{table}"')
            op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    op.execute("DELETE FROM identity_role_permissions WHERE permission_key LIKE 'inventory.counts.%'")
    op.execute("DELETE FROM identity_permissions WHERE key LIKE 'inventory.counts.%'")
    op.drop_index("ix_inventory_count_line_org_count", table_name="inventory_count_lines")
    op.drop_table("inventory_count_lines")
    op.drop_index("ix_inventory_count_org_status_created", table_name="inventory_counts")
    op.drop_table("inventory_counts")
