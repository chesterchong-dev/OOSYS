"""User profile, password and organisation-switching endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, get_principal
from app.identity.models import AuthSession, Membership, Organization, User
from app.identity.security import hash_password, token_digest, utc_now, verify_password
router = APIRouter()

@router.get("/auth/me")
def me(principal: Principal = Depends(get_principal)):
    return {"user_id": principal.user_id, "email": principal.email, "organization_id": principal.organization_id,
            "membership_id": principal.membership_id, "permissions": sorted(principal.permissions)}

@router.patch("/auth/me")
def update_me(payload: dict, principal: Principal = Depends(get_principal), db: Session = Depends(get_identity_session)):
    if set(payload) != {"full_name"} or not isinstance(payload.get("full_name"), str):
        raise HTTPException(422, "full_name is required")
    name = payload["full_name"].strip()
    if not name or len(name) > 160:
        raise HTTPException(422, "Invalid full_name")
    user = db.get(User, principal.user_id)
    user.full_name = name
    record_event(db, action="user.profile_update", target_type="user", organization_id=principal.organization_id,
                 actor_user_id=principal.user_id, target_id=principal.user_id)
    db.commit()
    return {"user_id": user.id, "email": user.email, "full_name": user.full_name}

@router.post("/auth/me/password", status_code=204)
def change_password(payload: dict, principal: Principal = Depends(get_principal), db: Session = Depends(get_identity_session)):
    if set(payload) != {"current_password", "new_password"}:
        raise HTTPException(422, "current_password and new_password are required")
    current, new = payload["current_password"], payload["new_password"]
    if not isinstance(current, str) or not isinstance(new, str) or len(new) < 12 or len(new) > 128:
        raise HTTPException(422, "New password must be between 12 and 128 characters")
    user = db.get(User, principal.user_id)
    if not verify_password(current, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(new)
    db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).update(
        {AuthSession.revoked_at: utc_now()}, synchronize_session=False)
    record_event(db, action="user.password_change", target_type="user", organization_id=principal.organization_id,
                 actor_user_id=user.id, target_id=user.id)
    db.commit()
    return None

@router.post("/auth/me/deactivate", status_code=204)
def deactivate_me(principal: Principal = Depends(get_principal), db: Session = Depends(get_identity_session)):
    user = db.get(User, principal.user_id)
    user.is_active = False
    user.archived_at = utc_now()
    db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).update(
        {AuthSession.revoked_at: utc_now()}, synchronize_session=False)
    record_event(db, action="user.deactivate", target_type="user", organization_id=principal.organization_id,
                 actor_user_id=user.id, target_id=user.id)
    db.commit()
    return None

@router.post("/auth/switch-organization/{organization_id}")
def switch_organization(organization_id: str, request: Request, db: Session = Depends(get_identity_session),
                        principal: Principal = Depends(get_principal)):
    raw = request.headers.get("Authorization", "").partition(" ")[2].strip()
    auth_session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(raw),
        AuthSession.user_id == principal.user_id, AuthSession.revoked_at.is_(None)))
    membership = db.scalar(select(Membership).where(Membership.user_id == principal.user_id,
        Membership.organization_id == organization_id, Membership.status == "active"))
    org = db.get(Organization, organization_id)
    if not auth_session or not membership or not org or org.status != "active" or org.archived_at is not None:
        raise HTTPException(404, "Organisation not found")
    auth_session.active_organization_id = organization_id
    record_event(db, action="auth.organization_switch", target_type="session", organization_id=organization_id,
                 actor_user_id=principal.user_id, target_id=auth_session.id)
    db.commit()
    return {"organization_id": organization_id}
