"""Add stable WMS location references to inventory ledger movements."""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0015"
down_revision: str | None = "20261024_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("inventory_movements", sa.Column("warehouse_location_id", sa.String(36), nullable=True))
    op.create_index(
        "ix_inventory_movement_org_product_location", "inventory_movements",
        ["organization_id", "product_id", "warehouse_location_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_movement_org_product_location", table_name="inventory_movements")
    op.drop_column("inventory_movements", "warehouse_location_id")


