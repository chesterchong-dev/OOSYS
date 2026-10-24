"""Add tenant-scoped warehouse and physical location master data."""
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0014"
down_revision: str | None = "20261024_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("status", sa.String(12), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_org_id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_warehouse_org_code"),
        sa.ForeignKeyConstraint(["organization_id"], ["identity_organizations.id"],
                                ondelete="RESTRICT", name="fk_warehouse_organization"),
        sa.CheckConstraint("length(trim(code)) > 0", name="ck_warehouse_code_nonempty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_warehouse_name_nonempty"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_warehouse_status"),
    )
    op.create_index("ix_warehouse_org_name", "warehouses", ["organization_id", "name"])

    op.create_table(
        "warehouse_locations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("parent_location_id", sa.String(36), nullable=True),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("location_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="active"),
        sa.Column("capacity_limit", sa.Numeric(20, 6), nullable=True),
        sa.Column("capacity_unit", sa.String(24), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_warehouse_location_org_id"),
        sa.UniqueConstraint("organization_id", "warehouse_id", "id",
                            name="uq_warehouse_location_org_warehouse_id"),
        sa.UniqueConstraint("organization_id", "warehouse_id", "code",
                            name="uq_warehouse_location_org_warehouse_code"),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_location_warehouse_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "parent_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_location_parent_same_warehouse",
        ),
        sa.CheckConstraint("length(trim(code)) > 0", name="ck_warehouse_location_code_nonempty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_warehouse_location_name_nonempty"),
        sa.CheckConstraint(
            "location_type IN ('zone','bin','receiving','staging','shipping','quarantine','unassigned')",
            name="ck_warehouse_location_type",
        ),
        sa.CheckConstraint("status IN ('active','blocked','inactive')", name="ck_warehouse_location_status"),
        sa.CheckConstraint("parent_location_id IS NULL OR parent_location_id != id",
                           name="ck_warehouse_location_not_own_parent"),
        sa.CheckConstraint(
            "(capacity_limit IS NULL AND capacity_unit IS NULL) OR "
            "(capacity_limit > 0 AND capacity_unit IS NOT NULL AND length(trim(capacity_unit)) > 0)",
            name="ck_warehouse_location_capacity_shape",
        ),
    )
    op.create_index("ix_warehouse_location_org_warehouse_parent", "warehouse_locations",
                    ["organization_id", "warehouse_id", "parent_location_id"])
    op.create_index("ix_warehouse_location_org_status", "warehouse_locations",
                    ["organization_id", "status"])

    permissions = [
        {"key": "warehouse.locations.read", "description": "View warehouses and locations"},
        {"key": "warehouse.locations.write", "description": "Create and update warehouses and locations"},
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
        for table in ("warehouses", "warehouse_locations"):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(f"""CREATE POLICY {table}_tenant ON {table}
                USING (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))
                WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("warehouse_locations", "warehouses"):
            op.execute(f'DROP POLICY IF EXISTS {table}_tenant ON "{table}"')
            op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_roles" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" NO FORCE ROW LEVEL SECURITY')
    op.execute("DELETE FROM identity_role_permissions WHERE permission_key LIKE 'warehouse.%'")
    op.execute("DELETE FROM identity_permissions WHERE key LIKE 'warehouse.%'")
    op.drop_index("ix_warehouse_location_org_status", table_name="warehouse_locations")
    op.drop_index("ix_warehouse_location_org_warehouse_parent", table_name="warehouse_locations")
    op.drop_table("warehouse_locations")
    op.drop_index("ix_warehouse_org_name", table_name="warehouses")
    op.drop_table("warehouses")
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "identity_roles" FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "identity_role_permissions" FORCE ROW LEVEL SECURITY')
