"""Add internal warehouse replenishment tasks."""
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0019"
down_revision: str | None = "20261024_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouse_replenishment_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("source_location_id", sa.String(36), nullable=False),
        sa.Column("destination_location_id", sa.String(36), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("lot_code", sa.String(100)),
        sa.Column("serial_code", sa.String(100)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("completed_by_user_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_replenishment_org_id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_replenishment_org_key"),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_replenishment_warehouse_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "source_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_replenishment_source_same_warehouse",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "destination_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_replenishment_destination_same_warehouse",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_warehouse_replenishment_quantity_positive"),
        sa.CheckConstraint("status IN ('pending','completed')", name="ck_warehouse_replenishment_status"),
        sa.CheckConstraint("source_location_id != destination_location_id",
                           name="ck_warehouse_replenishment_distinct_locations"),
        sa.CheckConstraint("lot_code IS NULL OR serial_code IS NULL",
                           name="ck_warehouse_replenishment_trace_unambiguous"),
        sa.CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL",
                           name="ck_warehouse_replenishment_expiry_requires_lot"),
    )
    op.create_index("ix_warehouse_replenishment_org_status_created", "warehouse_replenishment_tasks",
                    ["organization_id", "status", "created_at"])
    op.create_index("ix_warehouse_replenishment_org_product", "warehouse_replenishment_tasks",
                    ["organization_id", "product_id", "created_at"])
    permissions = [
        {"key": "warehouse.replenishment.read", "description": "View warehouse replenishment tasks"},
        {"key": "warehouse.replenishment.write", "description": "Create and complete warehouse replenishment tasks"},
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
        op.execute('ALTER TABLE "warehouse_replenishment_tasks" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "warehouse_replenishment_tasks" FORCE ROW LEVEL SECURITY')
        op.execute("""CREATE POLICY warehouse_replenishment_tenant ON warehouse_replenishment_tasks
            USING (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('DROP POLICY IF EXISTS warehouse_replenishment_tenant ON "warehouse_replenishment_tasks"')
        op.execute('ALTER TABLE "warehouse_replenishment_tasks" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "warehouse_replenishment_tasks" DISABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_roles" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" NO FORCE ROW LEVEL SECURITY')
    op.execute("DELETE FROM identity_role_permissions WHERE permission_key LIKE 'warehouse.replenishment.%'")
    op.execute("DELETE FROM identity_permissions WHERE key LIKE 'warehouse.replenishment.%'")
    op.drop_index("ix_warehouse_replenishment_org_product", table_name="warehouse_replenishment_tasks")
    op.drop_index("ix_warehouse_replenishment_org_status_created", table_name="warehouse_replenishment_tasks")
    op.drop_table("warehouse_replenishment_tasks")
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" FORCE ROW LEVEL SECURITY')
