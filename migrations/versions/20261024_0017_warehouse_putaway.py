"""Add putaway tasks for moving posted receipts to warehouse storage locations."""
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0017"
down_revision: str | None = "20261024_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouse_putaway_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("receipt_id", sa.String(36), nullable=False),
        sa.Column("receipt_line_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("source_location_id", sa.String(36), nullable=False),
        sa.Column("destination_location_id", sa.String(36)),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("lot_code", sa.String(100)),
        sa.Column("serial_code", sa.String(100)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("assigned_by_user_id", sa.String(36)),
        sa.Column("completed_by_user_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_putaway_task_org_id"),
        sa.UniqueConstraint("organization_id", "receipt_line_id", name="uq_warehouse_putaway_task_line"),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_task_warehouse_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "receipt_id"], ["warehouse_receipts.organization_id", "warehouse_receipts.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_task_receipt_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "receipt_line_id"],
            ["warehouse_receipt_lines.organization_id", "warehouse_receipt_lines.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_task_line_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "source_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_source_same_warehouse",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "destination_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_destination_same_warehouse",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_warehouse_putaway_quantity_positive"),
        sa.CheckConstraint("status IN ('pending','assigned','completed')", name="ck_warehouse_putaway_status"),
        sa.CheckConstraint("lot_code IS NULL OR serial_code IS NULL", name="ck_warehouse_putaway_trace_unambiguous"),
        sa.CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL", name="ck_warehouse_putaway_expiry_requires_lot"),
        sa.CheckConstraint(
            "(status = 'pending' AND destination_location_id IS NULL) OR "
            "(status IN ('assigned','completed') AND destination_location_id IS NOT NULL)",
            name="ck_warehouse_putaway_assignment_shape",
        ),
        sa.CheckConstraint(
            "destination_location_id IS NULL OR destination_location_id != source_location_id",
            name="ck_warehouse_putaway_distinct_locations",
        ),
    )
    op.create_index("ix_warehouse_putaway_org_status_created", "warehouse_putaway_tasks",
                    ["organization_id", "status", "created_at"])
    permissions = [
        {"key": "warehouse.putaway.read", "description": "View putaway tasks"},
        {"key": "warehouse.putaway.write", "description": "Assign and complete putaway tasks"},
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
        op.execute('ALTER TABLE "warehouse_putaway_tasks" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "warehouse_putaway_tasks" FORCE ROW LEVEL SECURITY')
        op.execute("""CREATE POLICY warehouse_putaway_tasks_tenant ON warehouse_putaway_tasks
            USING (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('DROP POLICY IF EXISTS warehouse_putaway_tasks_tenant ON "warehouse_putaway_tasks"')
        op.execute('ALTER TABLE "warehouse_putaway_tasks" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "warehouse_putaway_tasks" DISABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_roles" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" NO FORCE ROW LEVEL SECURITY')
    op.execute("DELETE FROM identity_role_permissions WHERE permission_key LIKE 'warehouse.putaway.%'")
    op.execute("DELETE FROM identity_permissions WHERE key LIKE 'warehouse.putaway.%'")
    op.drop_index("ix_warehouse_putaway_org_status_created", table_name="warehouse_putaway_tasks")
    op.drop_table("warehouse_putaway_tasks")
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" FORCE ROW LEVEL SECURITY')

