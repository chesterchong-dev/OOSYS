"""Identity and tenant persistence models. Passwords and session tokens are never stored raw."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
                        Index, Integer, JSON, String, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "identity_users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Organization(Base):
    __tablename__ = "identity_organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("status IN ('active','suspended','archived')", name="ck_identity_org_status"),)


class Membership(Base):
    __tablename__ = "identity_memberships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("identity_users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_identity_membership_org_user"),
        UniqueConstraint("organization_id", "id", name="uq_identity_membership_org_id"),
        CheckConstraint("status IN ('invited','active','suspended','revoked')", name="ck_identity_membership_status"),
        Index("ix_identity_membership_user_status", "user_id", "status"),
    )


class Role(Base):
    __tablename__ = "identity_roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_identity_role_org_name"),
                      UniqueConstraint("organization_id", "id", name="uq_identity_role_org_id"))


class Permission(Base):
    __tablename__ = "identity_permissions"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")


class RolePermission(Base):
    __tablename__ = "identity_role_permissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), nullable=False)
    permission_key: Mapped[str] = mapped_column(ForeignKey("identity_permissions.key", ondelete="RESTRICT"), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["organization_id", "role_id"], ["identity_roles.organization_id", "identity_roles.id"], ondelete="CASCADE", name="fk_identity_role_permission_same_org"),
        UniqueConstraint("organization_id", "role_id", "permission_key", name="uq_identity_role_permission"),
    )


class MembershipRole(Base):
    __tablename__ = "identity_membership_roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    membership_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["organization_id", "membership_id"], ["identity_memberships.organization_id", "identity_memberships.id"], ondelete="CASCADE", name="fk_identity_membership_role_same_org"),
        ForeignKeyConstraint(["organization_id", "role_id"], ["identity_roles.organization_id", "identity_roles.id"], ondelete="CASCADE", name="fk_identity_membership_role_role_same_org"),
        UniqueConstraint("organization_id", "membership_id", "role_id", name="uq_identity_membership_role"),
    )


class AuthSession(Base):
    __tablename__ = "identity_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("identity_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    active_organization_id: Mapped[str | None] = mapped_column(ForeignKey("identity_organizations.id", ondelete="RESTRICT"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoginAttempt(Base):
    __tablename__ = "identity_login_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class AuditEvent(Base):
    __tablename__ = "identity_audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(36))
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    correlation_id: Mapped[str | None] = mapped_column(String(100))
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class PasswordResetToken(Base):
    __tablename__ = "identity_password_reset_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("identity_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrganizationUnit(Base):
    """Tenant-scoped business unit, location, department or team."""
    __tablename__ = "identity_organization_units"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36))
    unit_type: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        ForeignKeyConstraint(["organization_id", "parent_id"], ["identity_organization_units.organization_id", "identity_organization_units.id"], ondelete="RESTRICT", name="fk_identity_unit_parent_same_org"),
        UniqueConstraint("organization_id", "id", name="uq_identity_unit_org_id"),
        UniqueConstraint("organization_id", "code", name="uq_identity_unit_org_code"),
        CheckConstraint("unit_type IN ('business_unit','location','department','team')", name="ck_identity_unit_type"),
        CheckConstraint("status IN ('active','archived')", name="ck_identity_unit_status"),
        Index("ix_identity_unit_org_type", "organization_id", "unit_type"),
    )


class OrganizationInvitation(Base):
    """One-time email invitation; only a digest of the token is stored."""
    __tablename__ = "identity_invitations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), nullable=False)
    invited_by_user_id: Mapped[str] = mapped_column(ForeignKey("identity_users.id", ondelete="RESTRICT"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(["organization_id", "role_id"], ["identity_roles.organization_id", "identity_roles.id"], ondelete="RESTRICT", name="fk_identity_invitation_role_same_org"),
        Index("ix_identity_invitation_org_email", "organization_id", "email"),
    )
