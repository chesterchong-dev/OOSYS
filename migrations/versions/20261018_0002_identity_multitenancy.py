"""Add identity, authentication, RBAC and organisation tenancy tables.

Revision ID: 20261018_0002
Revises: 20261018_0001
"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20261018_0002"
down_revision: str | None = "20261018_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("identity_users", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("identity_organizations", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False), sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active','suspended','archived')", name="ck_identity_org_status"))
    op.create_table("identity_memberships", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("identity_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_identity_membership_org_user"),
        sa.UniqueConstraint("organization_id", "id", name="uq_identity_membership_org_id"),
        sa.CheckConstraint("status IN ('invited','active','suspended','revoked')", name="ck_identity_membership_status"))
    op.create_index("ix_identity_memberships_organization_id", "identity_memberships", ["organization_id"])
    op.create_index("ix_identity_memberships_user_id", "identity_memberships", ["user_id"])
    op.create_index("ix_identity_membership_user_status", "identity_memberships", ["user_id", "status"])
    op.create_table("identity_roles", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False), sa.Column("description", sa.String(255), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False), sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "name", name="uq_identity_role_org_name"),
        sa.UniqueConstraint("organization_id", "id", name="uq_identity_role_org_id"))
    op.create_index("ix_identity_roles_organization_id", "identity_roles", ["organization_id"])
    op.create_table("identity_permissions", sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("description", sa.String(255), nullable=False))
    op.bulk_insert(
        sa.table("identity_permissions", sa.column("key", sa.String(120)), sa.column("description", sa.String(255))),
        [
            {"key": "organization.read", "description": "View the active organization"},
            {"key": "organization.update", "description": "Update the active organization"},
            {"key": "organization.archive", "description": "Archive the active organization"},
            {"key": "members.read", "description": "List organization members"},
            {"key": "members.invite", "description": "Add an existing user to the organization"},
            {"key": "members.update", "description": "Change membership status or roles"},
            {"key": "roles.read", "description": "View organization roles"},
            {"key": "roles.create", "description": "Create organization roles"},
            {"key": "roles.update", "description": "Update organization roles"},
            {"key": "roles.archive", "description": "Archive organization roles"},
            {"key": "audit.read", "description": "Read organization audit events"},
        ],
    )
    op.create_table("identity_role_permissions", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False), sa.Column("role_id", sa.String(36), nullable=False),
        sa.Column("permission_key", sa.String(120), sa.ForeignKey("identity_permissions.key", ondelete="RESTRICT"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id", "role_id"], ["identity_roles.organization_id", "identity_roles.id"], ondelete="CASCADE", name="fk_identity_role_permission_same_org"),
        sa.UniqueConstraint("organization_id", "role_id", "permission_key", name="uq_identity_role_permission"))
    op.create_index("ix_identity_role_permissions_organization_id", "identity_role_permissions", ["organization_id"])
    op.create_table("identity_membership_roles", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False), sa.Column("membership_id", sa.String(36), nullable=False),
        sa.Column("role_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["organization_id", "membership_id"], ["identity_memberships.organization_id", "identity_memberships.id"], ondelete="CASCADE", name="fk_identity_membership_role_same_org"),
        sa.ForeignKeyConstraint(["organization_id", "role_id"], ["identity_roles.organization_id", "identity_roles.id"], ondelete="CASCADE", name="fk_identity_membership_role_role_same_org"),
        sa.UniqueConstraint("organization_id", "membership_id", "role_id", name="uq_identity_membership_role"))
    op.create_index("ix_identity_membership_roles_organization_id", "identity_membership_roles", ["organization_id"])
    op.create_table("identity_sessions", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("identity_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("active_organization_id", sa.String(36), sa.ForeignKey("identity_organizations.id", ondelete="RESTRICT")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_identity_sessions_user_id", "identity_sessions", ["user_id"])
    op.create_index("ix_identity_sessions_expires_at", "identity_sessions", ["expires_at"])
    op.create_table("identity_login_attempts", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email_key", sa.String(64), nullable=False), sa.Column("ip_key", sa.String(64), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False), sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_identity_login_attempts_email_key", "identity_login_attempts", ["email_key"])
    op.create_index("ix_identity_login_attempts_ip_key", "identity_login_attempts", ["ip_key"])
    op.create_index("ix_identity_login_attempts_attempted_at", "identity_login_attempts", ["attempted_at"])
    op.create_table("identity_audit_events", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36)), sa.Column("actor_user_id", sa.String(36)),
        sa.Column("action", sa.String(120), nullable=False), sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(36)), sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("correlation_id", sa.String(100)), sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_identity_audit_events_organization_id", "identity_audit_events", ["organization_id"])
    op.create_index("ix_identity_audit_events_actor_user_id", "identity_audit_events", ["actor_user_id"])
    op.create_index("ix_identity_audit_events_action", "identity_audit_events", ["action"])
    op.create_index("ix_identity_audit_events_created_at", "identity_audit_events", ["created_at"])
    op.create_table("identity_password_reset_tokens", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("identity_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_identity_password_reset_tokens_user_id", "identity_password_reset_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_table("identity_password_reset_tokens")
    op.drop_index("ix_identity_audit_events_created_at", table_name="identity_audit_events")
    op.drop_index("ix_identity_audit_events_action", table_name="identity_audit_events")
    op.drop_index("ix_identity_audit_events_actor_user_id", table_name="identity_audit_events")
    op.drop_index("ix_identity_audit_events_organization_id", table_name="identity_audit_events")
    op.drop_table("identity_audit_events")
    op.drop_index("ix_identity_login_attempts_attempted_at", table_name="identity_login_attempts")
    op.drop_index("ix_identity_login_attempts_ip_key", table_name="identity_login_attempts")
    op.drop_index("ix_identity_login_attempts_email_key", table_name="identity_login_attempts")
    op.drop_table("identity_login_attempts")
    op.drop_index("ix_identity_sessions_expires_at", table_name="identity_sessions")
    op.drop_index("ix_identity_sessions_user_id", table_name="identity_sessions")
    op.drop_table("identity_sessions")
    op.drop_index("ix_identity_membership_roles_organization_id", table_name="identity_membership_roles")
    op.drop_table("identity_membership_roles")
    op.drop_index("ix_identity_role_permissions_organization_id", table_name="identity_role_permissions")
    op.drop_table("identity_role_permissions")
    op.drop_table("identity_permissions")
    op.drop_index("ix_identity_roles_organization_id", table_name="identity_roles")
    op.drop_table("identity_roles")
    op.drop_index("ix_identity_membership_user_status", table_name="identity_memberships")
    op.drop_index("ix_identity_memberships_user_id", table_name="identity_memberships")
    op.drop_index("ix_identity_memberships_organization_id", table_name="identity_memberships")
    op.drop_table("identity_memberships")
    op.drop_table("identity_organizations")
    op.drop_table("identity_users")
