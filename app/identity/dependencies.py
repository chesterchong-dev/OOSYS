"""Request-scoped identity session and trusted principal dependencies."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generator

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import create_database_engine, create_session_factory
from app.identity.models import AuthSession, Membership, MembershipRole, Organization, RolePermission, User
from app.identity.security import token_digest


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    organization_id: str
    membership_id: str
    permissions: frozenset[str]


def get_identity_session(request: Request) -> Generator[Session, None, None]:
    factory = getattr(request.app.state, "identity_session_factory", None)
    if factory is None:
        settings: Settings = request.app.state.settings
        engine = create_database_engine(settings)
        factory = create_session_factory(engine)
        request.app.state.identity_engine = engine
        request.app.state.identity_session_factory = factory
    with factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def get_principal(request: Request, session: Session = Depends(get_identity_session)) -> Principal:
    authorization = request.headers.get("Authorization", "")
    scheme, _, raw = authorization.partition(" ")
    if scheme.lower() != "bearer" or not raw.strip():
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    now = datetime.now(timezone.utc)
    auth_session = session.scalar(select(AuthSession).where(
        AuthSession.token_hash == token_digest(raw.strip()), AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > now))
    if auth_session is None:
        raise HTTPException(401, "Invalid or expired session", headers={"WWW-Authenticate": "Bearer"})
    user = session.get(User, auth_session.user_id)
    if user is None or not user.is_active or user.archived_at is not None:
        raise HTTPException(401, "Account unavailable")
    org_id = auth_session.active_organization_id
    if not org_id:
        raise HTTPException(403, "No active organisation")
    organization = session.get(Organization, org_id)
    membership = session.scalar(select(Membership).where(
        Membership.organization_id == org_id, Membership.user_id == user.id,
        Membership.status == "active"))
    if organization is None or organization.status != "active" or organization.archived_at is not None or membership is None:
        raise HTTPException(403, "Organisation membership unavailable")
    keys = session.scalars(select(RolePermission.permission_key)
        .join(MembershipRole, (MembershipRole.organization_id == RolePermission.organization_id)
              & (MembershipRole.role_id == RolePermission.role_id))
        .where(MembershipRole.organization_id == org_id, MembershipRole.membership_id == membership.id)).all()
    auth_session.last_seen_at = now
    return Principal(user.id, user.email, org_id, membership.id, frozenset(keys))


def require_permission(permission: str):
    def check(principal: Principal = Depends(get_principal)) -> Principal:
        if permission not in principal.permissions:
            raise HTTPException(403, "Insufficient permission")
        return principal
    return check
