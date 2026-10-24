"""Allow inventory counts to snapshot lot and serial trace codes.

Revision ID: 20261024_0009
Revises: 20261024_0008
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0009"
down_revision: str | None = "20261024_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inventory_count_lines") as batch:
        batch.add_column(sa.Column("lot_code", sa.String(100), nullable=True))
        batch.add_column(sa.Column("serial_code", sa.String(100), nullable=True))
        batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.drop_constraint("uq_inventory_count_line_product", type_="unique")
        batch.create_unique_constraint(
            "uq_inventory_count_line_lot",
            ["organization_id", "count_id", "product_id", "lot_code"],
        )
        batch.create_unique_constraint(
            "uq_inventory_count_line_serial",
            ["organization_id", "count_id", "product_id", "serial_code"],
        )
        batch.create_check_constraint(
            "ck_inventory_count_line_one_trace_code",
            "lot_code IS NULL OR serial_code IS NULL",
        )


def downgrade() -> None:
    # The old contract had no trace-code fields and allowed one line per product.
    # Refuse downgrade rather than silently discard count evidence.
    bind = op.get_bind()
    traced_line = bind.execute(sa.text("""
        SELECT id FROM inventory_count_lines
        WHERE lot_code IS NOT NULL OR serial_code IS NOT NULL OR expires_at IS NOT NULL
        LIMIT 1
    """)).first()
    duplicate_products = bind.execute(sa.text("""
        SELECT organization_id, count_id, product_id FROM inventory_count_lines
        GROUP BY organization_id, count_id, product_id HAVING count(*) > 1 LIMIT 1
    """)).first()
    if traced_line is not None or duplicate_products is not None:
        raise RuntimeError("Cannot downgrade while traced or multi-line count evidence exists")
    with op.batch_alter_table("inventory_count_lines") as batch:
        batch.drop_constraint("ck_inventory_count_line_one_trace_code", type_="check")
        batch.drop_constraint("uq_inventory_count_line_lot", type_="unique")
        batch.drop_constraint("uq_inventory_count_line_serial", type_="unique")
        batch.create_unique_constraint(
            "uq_inventory_count_line_product",
            ["organization_id", "count_id", "product_id"],
        )
        batch.drop_column("expires_at")
        batch.drop_column("serial_code")
        batch.drop_column("lot_code")

