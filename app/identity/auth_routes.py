"""Registration and login endpoints."""
from datetime import datetime, timedelta
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.identity.audit import record_event
from app.identity.dependencies import get_identity_session
from app.identity.models import AuthSession, LoginAttempt, Membership, MembershipRole, Organization, Role, RolePermission, User, new_id
from app.identity.permissions import OWNER_PERMISSIONS, PERMISSIONS
from app.identity.schemas import LoginRequest, RegisterRequest, UserOut, OrganizationOut
from app.identity.security import DUMMY_PASSWORD_HASH, hash_password, opaque_key, session_expiry, utc_now, verify_password
from app.identity.services import _new_session, _owner_role
from app.identity.tenant_context import set_tenant_context
router = APIRouter()

@router.post("/auth/register", status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_identity_session)):
    """Bootstrap an owner and organisation when self-service registration is explicitly enabled."""
    if not request.app.state.settings.allow_self_registration:
        raise HTTPException(403, "Self-service registration is disabled")
    email = str(payload.email).lower()
    set_tenant_context(db, None, user_email=email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    if db.scalar(select(Organization.id).where(Organization.slug == payload.organization_slug)):
        raise HTTPException(409, "Organisation slug already registered")
    user = User(email=email, password_hash=hash_password(payload.password), full_name=payload.full_name)
    org = Organization(id=new_id(), name=payload.organization_name, slug=payload.organization_slug)
    set_tenant_context(db, org.id, user.id, email)
    db.add_all([user, org])
    try:
        with db.begin_nested():
            db.flush()
            set_tenant_context(db, org.id, user.id, email)
            membership = Membership(organization_id=org.id, user_id=user.id, status="active")
            db.add(membership)
            db.flush()
            role = _owner_role(db, org.id)
            db.add(MembershipRole(organization_id=org.id, membership_id=membership.id, role_id=role.id))
            raw, expires = _new_session(db, user, org.id, request.app.state.settings.session_ttl_hours)
            record_event(db, action="identity.register", target_type="user", organization_id=org.id,
                         actor_user_id=user.id, target_id=user.id, correlation_id=request.headers.get("X-Request-ID"))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Account or organisation already exists") from exc
    return {"access_token": raw, "token_type": "bearer", "expires_at": expires,
            "user": UserOut(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active),
            "organization": OrganizationOut(id=org.id, name=org.name, slug=org.slug, status=org.status)}

@router.post("/auth/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_identity_session)):
    email = str(payload.email).lower()
    cutoff = utc_now() - timedelta(minutes=request.app.state.settings.login_window_minutes)
    email_key = opaque_key(email)
    ip = request.client.host if request.client else "unknown"
    ip_key = opaque_key(ip)
    # Bound attempt history and serialize checks across PostgreSQL workers.
    db.query(LoginAttempt).filter(LoginAttempt.attempted_at < cutoff - timedelta(days=7)).delete(synchronize_session=False)
    if db.bind and db.bind.dialect.name == "postgresql":
        for key in sorted((email_key, ip_key)):
            lock_id = int.from_bytes(hashlib.blake2b(key.encode(), digest_size=8).digest(), "big", signed=True)
            db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
    failed = db.scalar(select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.attempted_at >= cutoff, LoginAttempt.succeeded.is_(False),
        (LoginAttempt.email_key == email_key) | (LoginAttempt.ip_key == ip_key))) or 0
    if failed >= request.app.state.settings.login_max_attempts:
        raise HTTPException(429, "Too many login attempts; try again later")
    set_tenant_context(db, None, user_email=email)
    user = db.scalar(select(User).where(User.email == email))
    password_valid = verify_password(payload.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    valid = user is not None and user.is_active and user.archived_at is None and password_valid
    db.add(LoginAttempt(email_key=email_key, ip_key=ip_key, succeeded=bool(valid)))
    if not valid:
        if user is not None:
            set_tenant_context(db, None, user.id, user.email)
        record_event(db, action="auth.login", target_type="user", target_id=user.id if user else None,
                     actor_user_id=user.id if user else None, outcome="denied",
                     correlation_id=request.headers.get("X-Request-ID"))
        db.commit()
        raise HTTPException(401, "Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    set_tenant_context(db, None, user.id, user.email)
    memberships = db.scalars(select(Membership).where(
        Membership.user_id == user.id, Membership.status == "active")).all()
    if payload.organization_id:
        memberships = [m for m in memberships if m.organization_id == payload.organization_id]
    active_memberships = []
    for membership in memberships:
        set_tenant_context(db, membership.organization_id, user.id, user.email)
        organization = db.get(Organization, membership.organization_id)
        if organization and organization.status == "active" and organization.archived_at is None:
            active_memberships.append(membership)
    memberships = active_memberships
    if not memberships:
        db.commit()
        raise HTTPException(403, "No active organisation membership")
    if len(memberships) > 1 and not payload.organization_id:
        db.commit()
        return {"requires_organization_selection": True,
                "organizations": [{"id": m.organization_id} for m in memberships]}
    raw, expires = _new_session(db, user, memberships[0].organization_id, request.app.state.settings.session_ttl_hours)
    record_event(db, action="auth.login", target_type="user", organization_id=memberships[0].organization_id,
                 actor_user_id=user.id, target_id=user.id, correlation_id=request.headers.get("X-Request-ID"))
    db.commit()
    return {"access_token": raw, "token_type": "bearer", "expires_at": expires,
            "user": UserOut(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active),
            "organization_id": memberships[0].organization_id}
