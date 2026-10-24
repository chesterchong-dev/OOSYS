"""Add inventory product families and stockable SKU variants.

Revision ID: 20261024_0010
Revises: 20261024_0009
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0010"
down_revision: str | None = "20261024_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inventory_products") as batch:
        batch.add_column(sa.Column(
            "kind", sa.String(8), nullable=False, server_default="sku",
        ))
        batch.add_column(sa.Column("family_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column(
            "variant_attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'"),
        ))
        batch.create_foreign_key(
            "fk_inventory_product_family_same_org",
            "inventory_products",
            ["organization_id", "family_id"],
            ["organization_id", "id"],
            ondelete="RESTRICT",
        )
        batch.create_check_constraint(
            "ck_inventory_product_kind", "kind IN ('family','sku')",
        )
        batch.create_check_constraint(
            "ck_inventory_product_family_shape",
            "family_id IS NULL OR kind = 'sku'",
        )
        batch.create_check_constraint(
            "ck_inventory_product_not_own_family",
            "family_id IS NULL OR family_id != id",
        )
    op.create_index(
        "ix_inventory_product_org_family", "inventory_products",
        ["organization_id", "family_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    family = bind.execute(sa.text("""
        SELECT id FROM inventory_products
        WHERE kind = 'family' OR family_id IS NOT NULL
        LIMIT 1
    """)).first()
    variant_data = bind.execute(sa.text("""
        SELECT id FROM inventory_products
        WHERE variant_attributes IS NOT NULL
          AND CAST(variant_attributes AS TEXT) != '{}'
        LIMIT 1
    """)).first()
    if family is not None or variant_data is not None:
        raise RuntimeError("Cannot downgrade while product family or variant data exists")
    op.drop_index("ix_inventory_product_org_family", table_name="inventory_products")
    with op.batch_alter_table("inventory_products") as batch:
        batch.drop_constraint("ck_inventory_product_not_own_family", type_="check")
        batch.drop_constraint("ck_inventory_product_family_shape", type_="check")
        batch.drop_constraint("ck_inventory_product_kind", type_="check")
        batch.drop_constraint("fk_inventory_product_family_same_org", type_="foreignkey")
        batch.drop_column("variant_attributes")
        batch.drop_column("family_id")
        batch.drop_column("kind")

