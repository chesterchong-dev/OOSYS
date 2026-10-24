"""Add tenant-safe links for controlled inventory movement reversals."""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0012"
down_revision: str | None = "20261024_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inventory_movements") as batch:
        batch.add_column(sa.Column("reversal_of_movement_id", sa.String(36), nullable=True))
        batch.drop_constraint("ck_inventory_movement_type", type_="check")
        batch.create_check_constraint(
            "ck_inventory_movement_type",
            "movement_type IN ('receipt','issue','adjustment','count','reserve','release','reversal')",
        )
        batch.drop_constraint("ck_inventory_movement_reserve_delta", type_="check")
        batch.create_check_constraint(
            "ck_inventory_movement_reserve_delta",
            "reserved_delta >= 0 OR movement_type IN ('release','reversal')",
        )
        batch.create_unique_constraint(
            "uq_inventory_movement_org_reversal_target",
            ["organization_id", "reversal_of_movement_id"],
        )
        batch.create_foreign_key(
            "fk_inventory_movement_reversal_same_org",
            "inventory_movements",
            ["organization_id", "reversal_of_movement_id"],
            ["organization_id", "id"],
            ondelete="RESTRICT",
        )
        batch.create_check_constraint(
            "ck_inventory_movement_reversal_link",
            "(movement_type = 'reversal') = (reversal_of_movement_id IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("inventory_movements") as batch:
        batch.drop_constraint("ck_inventory_movement_reversal_link", type_="check")
        batch.drop_constraint("fk_inventory_movement_reversal_same_org", type_="foreignkey")
        batch.drop_constraint("uq_inventory_movement_org_reversal_target", type_="unique")
        batch.drop_constraint("ck_inventory_movement_type", type_="check")
        batch.create_check_constraint(
            "ck_inventory_movement_type",
            "movement_type IN ('receipt','issue','adjustment','count','reserve','release')",
        )
        batch.drop_constraint("ck_inventory_movement_reserve_delta", type_="check")
        batch.create_check_constraint(
            "ck_inventory_movement_reserve_delta",
            "reserved_delta >= 0 OR movement_type = 'release'",
        )
        batch.drop_column("reversal_of_movement_id")
