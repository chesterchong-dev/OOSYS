"""Add tenant-scoped inventory catalog, balances, and immutable movements.

Revision ID: 20261024_0007
Revises: 20261018_0006
"""
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0007"
down_revision: str | None = "20261018_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("inventory_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(60), nullable=False), sa.Column("name", sa.String(120), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_inventory_category_org_id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_inventory_category_org_code"),
        sa.CheckConstraint("length(trim(code)) > 0", name="ck_inventory_category_code_nonempty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_inventory_category_name_nonempty"))
    op.create_index("ix_inventory_category_org_name", "inventory_categories", ["organization_id", "name"])

    op.create_table("inventory_units",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(24), nullable=False), sa.Column("name", sa.String(80), nullable=False),
        sa.Column("decimal_places", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_inventory_unit_org_id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_inventory_unit_org_code"),
        sa.CheckConstraint("length(trim(code)) > 0", name="ck_inventory_unit_code_nonempty"),
        sa.CheckConstraint("decimal_places BETWEEN 0 AND 6", name="ck_inventory_unit_decimal_places"))
    op.create_index("ix_inventory_unit_org_name", "inventory_units", ["organization_id", "name"])

    op.create_table("inventory_products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sku", sa.String(80), nullable=False), sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("category_id", sa.String(36)), sa.Column("unit_id", sa.String(36), nullable=False),
        sa.Column("barcode", sa.String(120)), sa.Column("tracking_mode", sa.String(12), nullable=False, server_default="none"),
        sa.Column("cost_currency", sa.String(3), nullable=False, server_default="MYR"),
        sa.Column("average_cost", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_inventory_product_org_id"),
        sa.UniqueConstraint("organization_id", "sku", name="uq_inventory_product_org_sku"),
        sa.UniqueConstraint("organization_id", "barcode", name="uq_inventory_product_org_barcode"),
        sa.ForeignKeyConstraint(["organization_id", "category_id"], ["inventory_categories.organization_id", "inventory_categories.id"], ondelete="RESTRICT", name="fk_inventory_product_category_same_org"),
        sa.ForeignKeyConstraint(["organization_id", "unit_id"], ["inventory_units.organization_id", "inventory_units.id"], ondelete="RESTRICT", name="fk_inventory_product_unit_same_org"),
        sa.CheckConstraint("length(trim(sku)) > 0", name="ck_inventory_product_sku_nonempty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_inventory_product_name_nonempty"),
        sa.CheckConstraint("tracking_mode IN ('none','lot','serial')", name="ck_inventory_product_tracking_mode"),
        sa.CheckConstraint("cost_currency = upper(cost_currency) AND length(cost_currency) = 3", name="ck_inventory_product_currency"),
        sa.CheckConstraint("average_cost >= 0", name="ck_inventory_product_average_cost_nonnegative"))
    op.create_index("ix_inventory_product_org_name", "inventory_products", ["organization_id", "name"])
    op.create_index("ix_inventory_product_org_category", "inventory_products", ["organization_id", "category_id"])

    op.create_table("inventory_stock_balances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False), sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("on_hand", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_inventory_balance_org_id"),
        sa.UniqueConstraint("organization_id", "product_id", name="uq_inventory_balance_org_product"),
        sa.ForeignKeyConstraint(["organization_id", "product_id"], ["inventory_products.organization_id", "inventory_products.id"], ondelete="RESTRICT", name="fk_inventory_balance_product_same_org"),
        sa.CheckConstraint("on_hand >= 0", name="ck_inventory_balance_on_hand_nonnegative"),
        sa.CheckConstraint("reserved >= 0 AND reserved <= on_hand", name="ck_inventory_balance_reserved_range"))
    op.create_index("ix_inventory_balance_org_product", "inventory_stock_balances", ["organization_id", "product_id"])

    op.create_table("inventory_movements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False), sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("movement_type", sa.String(16), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(20, 6), nullable=False),
        sa.Column("reserved_delta", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(20, 6)), sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False), sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("lot_code", sa.String(100)), sa.Column("serial_code", sa.String(100)),
        sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("note", sa.String(500), nullable=False, server_default=""),
        sa.Column("actor_user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_inventory_movement_org_id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_inventory_movement_org_idempotency"),
        sa.ForeignKeyConstraint(["organization_id", "product_id"], ["inventory_products.organization_id", "inventory_products.id"], ondelete="RESTRICT", name="fk_inventory_movement_product_same_org"),
        sa.CheckConstraint("movement_type IN ('receipt','issue','adjustment','count','reserve','release')", name="ck_inventory_movement_type"),
        sa.CheckConstraint("quantity_delta != 0 OR reserved_delta != 0 OR movement_type = 'count'", name="ck_inventory_movement_nonzero"),
        sa.CheckConstraint("reserved_delta >= 0 OR movement_type = 'release'", name="ck_inventory_movement_reserve_delta"),
        sa.CheckConstraint("unit_cost IS NULL OR unit_cost >= 0", name="ck_inventory_movement_cost_nonnegative"),
        sa.CheckConstraint("length(currency_code) = 3 AND currency_code = upper(currency_code)", name="ck_inventory_movement_currency"))
    op.create_index("ix_inventory_movement_org_product_created", "inventory_movements", ["organization_id", "product_id", "created_at"])
    op.create_index("ix_inventory_movement_org_lot", "inventory_movements", ["organization_id", "product_id", "lot_code"])
    op.create_index("ix_inventory_movement_org_serial", "inventory_movements", ["organization_id", "product_id", "serial_code"])

    permissions = [
        {"key": "inventory.products.read", "description": "View inventory products, categories and units"},
        {"key": "inventory.products.write", "description": "Create and update inventory products, categories and units"},
        {"key": "inventory.stock.read", "description": "View stock balances and movement history"},
        {"key": "inventory.stock.write", "description": "Post stock movements, counts and reservations"},
    ]
    op.bulk_insert(sa.table("identity_permissions", sa.column("key", sa.String(120)),
                            sa.column("description", sa.String(255))), permissions)
    conn = op.get_bind()
    owners = conn.execute(sa.text("SELECT organization_id, id FROM identity_roles WHERE name = 'Owner' AND is_system = TRUE")).mappings().all()
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
        for table in ("inventory_categories", "inventory_units", "inventory_products",
                      "inventory_stock_balances", "inventory_movements"):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(f"""CREATE POLICY {table}_tenant ON {table}
                USING (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))
                WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        for table in ("inventory_movements", "inventory_stock_balances", "inventory_products",
                      "inventory_units", "inventory_categories"):
            op.execute(f'DROP POLICY IF EXISTS {table}_tenant ON "{table}"')
            op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    op.execute("DELETE FROM identity_role_permissions WHERE permission_key LIKE 'inventory.%'")
    op.execute("DELETE FROM identity_permissions WHERE key LIKE 'inventory.%'")
    op.drop_index("ix_inventory_movement_org_serial", table_name="inventory_movements")
    op.drop_index("ix_inventory_movement_org_lot", table_name="inventory_movements")
    op.drop_index("ix_inventory_movement_org_product_created", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_index("ix_inventory_balance_org_product", table_name="inventory_stock_balances")
    op.drop_table("inventory_stock_balances")
    op.drop_index("ix_inventory_product_org_category", table_name="inventory_products")
    op.drop_index("ix_inventory_product_org_name", table_name="inventory_products")
    op.drop_table("inventory_products")
    op.drop_index("ix_inventory_unit_org_name", table_name="inventory_units")
    op.drop_table("inventory_units")
    op.drop_index("ix_inventory_category_org_name", table_name="inventory_categories")
    op.drop_table("inventory_categories")

