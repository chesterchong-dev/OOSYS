"""Enforce append-only inventory ledger rows in the database."""
from typing import Sequence

from alembic import op

revision: str = "20261024_0013"
down_revision: str | None = "20261024_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION reject_inventory_movement_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'inventory movements are append-only'
                    USING ERRCODE = '55000';
            END;
            $$
        """)
        op.execute("""
            CREATE TRIGGER inventory_movements_append_only
            BEFORE UPDATE OR DELETE ON inventory_movements
            FOR EACH ROW EXECUTE FUNCTION reject_inventory_movement_mutation()
        """)
    elif bind.dialect.name == "sqlite":
        op.execute("""
            CREATE TRIGGER inventory_movements_no_update
            BEFORE UPDATE ON inventory_movements
            BEGIN
                SELECT RAISE(ABORT, 'inventory movements are append-only');
            END
        """)
        op.execute("""
            CREATE TRIGGER inventory_movements_no_delete
            BEFORE DELETE ON inventory_movements
            BEGIN
                SELECT RAISE(ABORT, 'inventory movements are append-only');
            END
        """)
    else:
        raise RuntimeError(f"Unsupported database dialect for inventory append-only guard: {bind.dialect.name}")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER inventory_movements_append_only ON inventory_movements")
        op.execute("DROP FUNCTION reject_inventory_movement_mutation()")
    elif bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER inventory_movements_no_update")
        op.execute("DROP TRIGGER inventory_movements_no_delete")
