"""Enable PostgreSQL RLS on identity tenant-owned tables.

Revision ID: 20261018_0005
Revises: 20261018_0004
"""
from typing import Sequence
from alembic import op
revision: str = "20261018_0005"
down_revision: str | None = "20261018_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICIES = {
"identity_sessions": """CREATE POLICY identity_sessions_owner ON identity_sessions USING (user_id = NULLIF(current_setting('app.user_id', true), '') OR token_hash = NULLIF(current_setting('app.session_token_hash', true), '')) WITH CHECK (user_id = NULLIF(current_setting('app.user_id', true), ''))""",
"identity_organizations": """CREATE POLICY identity_organizations_tenant ON identity_organizations USING (id = NULLIF(current_setting('app.tenant_id', true), '') OR (NULLIF(current_setting('app.tenant_id', true), '') IS NULL AND id IN (SELECT organization_id FROM identity_memberships WHERE user_id = NULLIF(current_setting('app.user_id', true), '')))) WITH CHECK (id = NULLIF(current_setting('app.tenant_id', true), ''))""",
"identity_memberships": """CREATE POLICY identity_memberships_tenant ON identity_memberships USING (organization_id = NULLIF(current_setting('app.tenant_id', true), '') OR (NULLIF(current_setting('app.tenant_id', true), '') IS NULL AND user_id = NULLIF(current_setting('app.user_id', true), ''))) WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), '') OR (NULLIF(current_setting('app.tenant_id', true), '') IS NULL AND user_id = NULLIF(current_setting('app.user_id', true), '')))""",
"identity_roles": """CREATE POLICY identity_roles_tenant ON identity_roles USING (organization_id = NULLIF(current_setting('app.tenant_id', true), '')) WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""",
"identity_role_permissions": """CREATE POLICY identity_role_permissions_tenant ON identity_role_permissions USING (organization_id = NULLIF(current_setting('app.tenant_id', true), '')) WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""",
"identity_membership_roles": """CREATE POLICY identity_membership_roles_tenant ON identity_membership_roles USING (organization_id = NULLIF(current_setting('app.tenant_id', true), '')) WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""",
"identity_audit_events": """CREATE POLICY identity_audit_events_tenant ON identity_audit_events USING (organization_id = NULLIF(current_setting('app.tenant_id', true), '') OR (organization_id IS NULL AND actor_user_id = NULLIF(current_setting('app.user_id', true), ''))) WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), '') OR (organization_id IS NULL AND (actor_user_id = NULLIF(current_setting('app.user_id', true), '') OR actor_user_id IS NULL)))""",
"identity_password_reset_tokens": """CREATE POLICY identity_password_reset_tokens_owner ON identity_password_reset_tokens USING (user_id = NULLIF(current_setting('app.user_id', true), '') OR token_hash = NULLIF(current_setting('app.reset_token_hash', true), '')) WITH CHECK (user_id = NULLIF(current_setting('app.user_id', true), ''))""",
"identity_organization_units": """CREATE POLICY identity_organization_units_tenant ON identity_organization_units USING (organization_id = NULLIF(current_setting('app.tenant_id', true), '')) WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""",
"identity_invitations": """CREATE POLICY identity_invitations_tenant ON identity_invitations USING (organization_id = NULLIF(current_setting('app.tenant_id', true), '') OR (NULLIF(current_setting('app.tenant_id', true), '') IS NULL AND email = NULLIF(current_setting('app.user_email', true), ''))) WITH CHECK (organization_id = NULLIF(current_setting('app.tenant_id', true), ''))""",
}


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, policy in POLICIES.items():
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(policy)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, policy in reversed(list(POLICIES.items())):
        name = policy.split("CREATE POLICY ", 1)[1].split(" ", 1)[0]
        op.execute(f'DROP POLICY IF EXISTS "{name}" ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
