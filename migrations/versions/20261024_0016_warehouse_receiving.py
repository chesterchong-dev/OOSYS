"""Add transactional inbound receipt workflows owned by WMS."""
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0016"
down_revision: str | None = "20261024_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouse_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("receiving_location_id", sa.String(36), nullable=False),
        sa.Column("receipt_number", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("source_reference", sa.String(160)),
        sa.Column("status", sa.String(12), nullable=False, server_default="draft"),
        sa.Column("note", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("posted_by_user_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_receipt_org_id"),
        sa.UniqueConstraint("organization_id", "receipt_number", name="uq_warehouse_receipt_org_number"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_receipt_org_key"),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_receipt_warehouse_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "receiving_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_receipt_location_same_warehouse",
        ),
        sa.CheckConstraint("status IN ('draft','posted')", name="ck_warehouse_receipt_status"),
        sa.CheckConstraint("length(trim(receipt_number)) > 0", name="ck_warehouse_receipt_number_nonempty"),
    )
    op.create_index("ix_warehouse_receipt_org_status_created", "warehouse_receipts",
                    ["organization_id", "status", "created_at"])
    op.create_table(
        "warehouse_receipt_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("receipt_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("unit_cost", sa.Numeric(20, 6)),
        sa.Column("lot_code", sa.String(100)),
        sa.Column("serial_code", sa.String(100)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_receipt_line_org_id"),
        sa.ForeignKeyConstraint(
            ["organization_id", "receipt_id"], ["warehouse_receipts.organization_id", "warehouse_receipts.id"],
            ondelete="RESTRICT", name="fk_warehouse_receipt_line_receipt_same_org",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_warehouse_receipt_line_quantity_positive"),
        sa.CheckConstraint("unit_cost IS NULL OR unit_cost >= 0", name="ck_warehouse_receipt_line_cost_nonnegative"),
        sa.CheckConstraint("lot_code IS NULL OR serial_code IS NULL", name="ck_warehouse_receipt_line_trace_unambiguous"),
        sa.CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL", name="ck_warehouse_receipt_line_expiry_requires_lot"),
    )
    op.create_index("ix_warehouse_receipt_line_org_receipt", "warehouse_receipt_lines",
                    ["organization_id", "receipt_id"])
    op.create_index("ix_warehouse_receipt_line_org_product", "warehouse_receipt_lines",
                    ["organization_id", "product_id"])

    permissions = [
        {"key": "warehouse.receiving.read", "description": "View warehouse receipts"},
        {"key": "warehouse.receiving.write", "description": "Create and post warehouse receipts"},
    ]
    op.bulk_insert(sa.table("identity_permissions", sa.column("key", sa.String(120)),
                            sa.column("description", sa.String(255))), permissions)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" NO FORCE ROW LEVEL SECURITY')
    owners = bind.execute(sa.text(
        "SELECT organization_id, id FROM identity_roles WHERE name = 'Owner' AND is_system = TRUE"
    )).mappings().all()
    for owner in owners:
        bind.execute(sa.text("""
            INSERT INTO identity_role_permissions (id, organization_id, role_id, permission_key)
            VALUES (:id, :organization_id, :role_id, :permission_key)
        """), [
            {"id": str(uuid4()), "organization_id": owner["organization_id"],
             "role_id": owner["id"], "permission_key": permission["key"]}
            for permission in permissions
        ])
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" FORCE ROW LEVEL SECURITY')
        for table in ("warehouse_receipts", "warehouse_receipt_lines"):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(f"""CREATE POLICY {table}_tenant ON {table}
                USING (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))
                WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("warehouse_receipt_lines", "warehouse_receipts"):
            op.execute(f'DROP POLICY IF EXISTS {table}_tenant ON "{table}"')
            op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_roles" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" NO FORCE ROW LEVEL SECURITY')
    op.execute("DELETE FROM identity_role_permissions WHERE permission_key LIKE 'warehouse.receiving.%'")
    op.execute("DELETE FROM identity_permissions WHERE key LIKE 'warehouse.receiving.%'")
    op.drop_index("ix_warehouse_receipt_line_org_product", table_name="warehouse_receipt_lines")
    op.drop_index("ix_warehouse_receipt_line_org_receipt", table_name="warehouse_receipt_lines")
    op.drop_table("warehouse_receipt_lines")
    op.drop_index("ix_warehouse_receipt_org_status_created", table_name="warehouse_receipts")
    op.drop_table("warehouse_receipts")
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" FORCE ROW LEVEL SECURITY')

