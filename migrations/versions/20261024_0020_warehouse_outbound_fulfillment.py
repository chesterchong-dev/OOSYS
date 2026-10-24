"""Add warehouse pick, pack, and dispatch workflows."""
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0020"
down_revision: str | None = "20261024_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouse_outbound_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("order_number", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("external_reference", sa.String(160)),
        sa.Column("shipping_location_id", sa.String(36)),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("reserved_by_user_id", sa.String(36)),
        sa.Column("picked_by_user_id", sa.String(36)),
        sa.Column("packed_by_user_id", sa.String(36)),
        sa.Column("dispatched_by_user_id", sa.String(36)),
        sa.Column("cancelled_by_user_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True)),
        sa.Column("picked_at", sa.DateTime(timezone=True)),
        sa.Column("packed_at", sa.DateTime(timezone=True)),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_outbound_order_org_id"),
        sa.UniqueConstraint("organization_id", "warehouse_id", "id",
                            name="uq_warehouse_outbound_order_org_warehouse_id"),
        sa.UniqueConstraint("organization_id", "order_number", name="uq_warehouse_outbound_order_org_number"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_outbound_order_org_key"),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_outbound_order_warehouse_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "shipping_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_outbound_order_shipping_same_warehouse",
        ),
        sa.CheckConstraint("status IN ('draft','reserved','picked','packed','dispatched','cancelled')",
                           name="ck_warehouse_outbound_order_status"),
        sa.CheckConstraint(
            "(status IN ('draft','reserved','cancelled') AND shipping_location_id IS NULL) OR "
            "(status IN ('picked','packed','dispatched') AND shipping_location_id IS NOT NULL)",
            name="ck_warehouse_outbound_order_shipping_shape",
        ),
    )
    op.create_index("ix_warehouse_outbound_order_org_status_created", "warehouse_outbound_orders",
                    ["organization_id", "status", "created_at"])

    op.create_table(
        "warehouse_outbound_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("source_location_id", sa.String(36), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("lot_code", sa.String(100)),
        sa.Column("serial_code", sa.String(100)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_outbound_line_org_id"),
        sa.UniqueConstraint("organization_id", "order_id", "id", name="uq_warehouse_outbound_line_order_id"),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "order_id"],
            ["warehouse_outbound_orders.organization_id", "warehouse_outbound_orders.warehouse_id",
             "warehouse_outbound_orders.id"],
            ondelete="RESTRICT", name="fk_warehouse_outbound_line_order_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "source_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_outbound_line_location_same_org",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_warehouse_outbound_line_quantity_positive"),
        sa.CheckConstraint("lot_code IS NULL OR serial_code IS NULL",
                           name="ck_warehouse_outbound_line_trace_unambiguous"),
        sa.CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL",
                           name="ck_warehouse_outbound_line_expiry_requires_lot"),
    )
    op.create_index("ix_warehouse_outbound_line_org_order", "warehouse_outbound_lines",
                    ["organization_id", "order_id"])

    op.create_table(
        "warehouse_packages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("package_number", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="open"),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("sealed_by_user_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sealed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_package_org_id"),
        sa.UniqueConstraint("organization_id", "order_id", "id", name="uq_warehouse_package_order_id"),
        sa.UniqueConstraint("organization_id", "package_number", name="uq_warehouse_package_org_number"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_package_org_key"),
        sa.ForeignKeyConstraint(
            ["organization_id", "order_id"],
            ["warehouse_outbound_orders.organization_id", "warehouse_outbound_orders.id"],
            ondelete="RESTRICT", name="fk_warehouse_package_order_same_org",
        ),
        sa.CheckConstraint("status IN ('open','sealed')", name="ck_warehouse_package_status"),
    )
    op.create_index("ix_warehouse_package_org_order", "warehouse_packages", ["organization_id", "order_id"])

    op.create_table(
        "warehouse_package_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("package_id", sa.String(36), nullable=False),
        sa.Column("order_line_id", sa.String(36), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_package_line_org_id"),
        sa.UniqueConstraint("organization_id", "package_id", "order_line_id",
                            name="uq_warehouse_package_line_item"),
        sa.ForeignKeyConstraint(
            ["organization_id", "order_id", "package_id"],
            ["warehouse_packages.organization_id", "warehouse_packages.order_id",
             "warehouse_packages.id"],
            ondelete="RESTRICT", name="fk_warehouse_package_line_package_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "order_id", "order_line_id"],
            ["warehouse_outbound_lines.organization_id", "warehouse_outbound_lines.order_id",
             "warehouse_outbound_lines.id"],
            ondelete="RESTRICT", name="fk_warehouse_package_line_order_line_same_org",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_warehouse_package_line_quantity_positive"),
    )
    op.create_index("ix_warehouse_package_line_org_order_line", "warehouse_package_lines",
                    ["organization_id", "order_line_id"])

    permissions = [
        {"key": "warehouse.outbound.read", "description": "View warehouse outbound orders"},
        {"key": "warehouse.outbound.write", "description": "Create, reserve, pick, dispatch and cancel outbound orders"},
        {"key": "warehouse.packing.read", "description": "View warehouse packages"},
        {"key": "warehouse.packing.write", "description": "Pack and seal warehouse packages"},
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
        for table in ("warehouse_outbound_orders", "warehouse_outbound_lines",
                      "warehouse_packages", "warehouse_package_lines"):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(f"""CREATE POLICY {table}_tenant ON "{table}"
                USING (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))
                WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("warehouse_package_lines", "warehouse_packages",
                      "warehouse_outbound_lines", "warehouse_outbound_orders"):
            op.execute(f'DROP POLICY IF EXISTS {table}_tenant ON "{table}"')
            op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_roles" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" NO FORCE ROW LEVEL SECURITY')
    op.execute("DELETE FROM identity_role_permissions WHERE permission_key IN "
               "('warehouse.outbound.read','warehouse.outbound.write','warehouse.packing.read','warehouse.packing.write')")
    op.execute("DELETE FROM identity_permissions WHERE key IN "
               "('warehouse.outbound.read','warehouse.outbound.write','warehouse.packing.read','warehouse.packing.write')")
    op.drop_index("ix_warehouse_package_line_org_order_line", table_name="warehouse_package_lines")
    op.drop_table("warehouse_package_lines")
    op.drop_index("ix_warehouse_package_org_order", table_name="warehouse_packages")
    op.drop_table("warehouse_packages")
    op.drop_index("ix_warehouse_outbound_line_org_order", table_name="warehouse_outbound_lines")
    op.drop_table("warehouse_outbound_lines")
    op.drop_index("ix_warehouse_outbound_order_org_status_created", table_name="warehouse_outbound_orders")
    op.drop_table("warehouse_outbound_orders")
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" FORCE ROW LEVEL SECURITY')
