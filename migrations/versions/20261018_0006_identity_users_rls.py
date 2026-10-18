"""Add row-level security for shared identity user records.

Revision ID: 20261018_0006
Revises: 20261018_0005
"""
from typing import Sequence
from alembic import op

revision: str = "20261018_0006"
down_revision: str | None = "20261018_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute('ALTER TABLE "identity_users" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "identity_users" FORCE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY identity_users_scope ON identity_users
        USING (
            id = NULLIF(current_setting('app.user_id', true), '')
            OR email = NULLIF(current_setting('app.user_email', true), '')
            OR id = NULLIF(current_setting('app.lookup_user_id', true), '')
            OR id IN (
                SELECT user_id FROM identity_memberships
                WHERE organization_id = NULLIF(current_setting('app.tenant_id', true), '')
            )
        )
        WITH CHECK (
            id = NULLIF(current_setting('app.user_id', true), '')
            OR email = NULLIF(current_setting('app.user_email', true), '')
        )
    """)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP POLICY IF EXISTS identity_users_scope ON identity_users")
    op.execute('ALTER TABLE "identity_users" NO FORCE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "identity_users" DISABLE ROW LEVEL SECURITY')
