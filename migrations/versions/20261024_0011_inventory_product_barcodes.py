"""Add tenant-unique product barcodes with legacy-code backfill."""
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0011"
down_revision: str | None = "20261024_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_product_barcodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("barcode", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_inventory_product_barcode_org_id"),
        sa.UniqueConstraint("organization_id", "barcode", name="uq_inventory_product_barcode_org_code"),
        sa.ForeignKeyConstraint(
            ["organization_id", "product_id"],
            ["inventory_products.organization_id", "inventory_products.id"],
            ondelete="RESTRICT", name="fk_inventory_product_barcode_product_same_org",
        ),
        sa.CheckConstraint("length(trim(barcode)) > 0", name="ck_inventory_product_barcode_nonempty"),
    )
    op.create_index(
        "ix_inventory_product_barcode_org_product", "inventory_product_barcodes",
        ["organization_id", "product_id"],
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Backfill legacy barcodes with the schema-owner connection while the
        # inventory_products RLS policy is active but not FORCE-applied.
        op.execute('ALTER TABLE "inventory_products" NO FORCE ROW LEVEL SECURITY')
    existing = bind.execute(sa.text("""
        SELECT organization_id, id AS product_id, barcode
        FROM inventory_products
        WHERE barcode IS NOT NULL
    """)).mappings().all()
    if existing:
        table = sa.table(
            "inventory_product_barcodes",
            sa.column("id", sa.String(36)),
            sa.column("organization_id", sa.String(36)),
            sa.column("product_id", sa.String(36)),
            sa.column("barcode", sa.String(120)),
        )
        op.bulk_insert(table, [
            {"id": str(uuid4()), "organization_id": row["organization_id"],
             "product_id": row["product_id"], "barcode": row["barcode"]}
            for row in existing
        ])
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "inventory_products" FORCE ROW LEVEL SECURITY')

    with op.batch_alter_table("inventory_products") as batch:
        batch.create_check_constraint(
            "ck_inventory_product_family_no_barcode", "kind = 'sku' OR barcode IS NULL",
        )

    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "inventory_product_barcodes" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "inventory_product_barcodes" FORCE ROW LEVEL SECURITY')
        op.execute("""CREATE POLICY inventory_product_barcodes_tenant
            ON inventory_product_barcodes
            USING (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('DROP POLICY IF EXISTS inventory_product_barcodes_tenant ON "inventory_product_barcodes"')
        op.execute('ALTER TABLE "inventory_product_barcodes" NO FORCE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "inventory_product_barcodes" DISABLE ROW LEVEL SECURITY')
    op.drop_index("ix_inventory_product_barcode_org_product", table_name="inventory_product_barcodes")
    op.drop_table("inventory_product_barcodes")
    with op.batch_alter_table("inventory_products") as batch:
        batch.drop_constraint("ck_inventory_product_family_no_barcode", type_="check")

