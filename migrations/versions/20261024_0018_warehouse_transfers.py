"""Add two-step, location-aware warehouse transfers."""
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0018"
down_revision: str | None = "20261024_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouse_transfers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("transfer_number", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("source_warehouse_id", sa.String(36), nullable=False),
        sa.Column("source_location_id", sa.String(36), nullable=False),
        sa.Column("destination_warehouse_id", sa.String(36), nullable=False),
        sa.Column("destination_location_id", sa.String(36), nullable=False),
        sa.Column("in_transit_location_id", sa.String(36)),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("lot_code", sa.String(100)),
        sa.Column("serial_code", sa.String(100)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("external_reference", sa.String(160)),
        sa.Column("status", sa.String(12), nullable=False, server_default="draft"),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("dispatched_by_user_id", sa.String(36)),
        sa.Column("received_by_user_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_transfer_org_id"),
        sa.UniqueConstraint("organization_id", "transfer_number", name="uq_warehouse_transfer_org_number"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_transfer_org_key"),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_source_warehouse_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_warehouse_id", "source_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_source_location_same_warehouse",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "destination_warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_destination_warehouse_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "destination_warehouse_id", "destination_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_destination_location_same_warehouse",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_warehouse_id", "in_transit_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_transit_location_same_warehouse",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_warehouse_transfer_quantity_positive"),
        sa.CheckConstraint("status IN ('draft','in_transit','received')", name="ck_warehouse_transfer_status"),
        sa.CheckConstraint("source_location_id != destination_location_id", name="ck_warehouse_transfer_distinct_locations"),
        sa.CheckConstraint("lot_code IS NULL OR serial_code IS NULL", name="ck_warehouse_transfer_trace_unambiguous"),
        sa.CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL", name="ck_warehouse_transfer_expiry_requires_lot"),
        sa.CheckConstraint(
            "(status = 'draft' AND in_transit_location_id IS NULL) OR "
            "(status IN ('in_transit','received') AND in_transit_location_id IS NOT NULL)",
            name="ck_warehouse_transfer_transit_shape",
        ),
    )
    op.create_index("ix_warehouse_transfer_org_status_created", "warehouse_transfers",
                    ["organization_id", "status", "created_at"])
    op.create_index("ix_warehouse_transfer_org_product", "warehouse_transfers",
                    ["organization_id", "product_id", "created_at"])
    permissions = [
        {"key": "warehouse.transfers.read", "description": "View warehouse transfers"},
        {"key": "warehouse.transfers.write", "description": "Create, dispatch and receive warehouse transfers"},
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
        op.execute('ALTER TABLE "warehouse_transfers" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "warehouse_transfers" FORCE ROW LEVEL SECURITY')
        op.execute("""CREATE POLICY warehouse_transfers_tenant ON warehouse_transfers
            USING (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('DROP POLICY IF EXISTS warehouse_transfers_tenant ON "warehouse_transfers"')
        op.execute('ALTER TABLE "warehouse_transfers" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "warehouse_transfers" DISABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_roles" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" NO FORCE ROW LEVEL SECURITY')
    op.execute("DELETE FROM identity_role_permissions WHERE permission_key LIKE 'warehouse.transfers.%'")
    op.execute("DELETE FROM identity_permissions WHERE key LIKE 'warehouse.transfers.%'")
    op.drop_index("ix_warehouse_transfer_org_product", table_name="warehouse_transfers")
    op.drop_index("ix_warehouse_transfer_org_status_created", table_name="warehouse_transfers")
    op.drop_table("warehouse_transfers")
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" FORCE ROW LEVEL SECURITY')
