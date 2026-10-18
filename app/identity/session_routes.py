"""Server-side session revocation endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, get_principal
from app.identity.models import AuthSession
from app.identity.security import token_digest, utc_now
router = APIRouter()

@router.post("/auth/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_identity_session), principal: Principal = Depends(get_principal)):
    raw = request.headers.get("Authorization", "").partition(" ")[2].strip()
    auth_session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(raw),
                                                       AuthSession.user_id == principal.user_id,
                                                       AuthSession.revoked_at.is_(None)))
    if auth_session:
        auth_session.revoked_at = utc_now()
        record_event(db, action="auth.logout", target_type="session", organization_id=principal.organization_id,
                     actor_user_id=principal.user_id, target_id=auth_session.id)
        db.commit()
    return None

@router.post("/auth/logout-all", status_code=204)
def logout_all(db: Session = Depends(get_identity_session), principal: Principal = Depends(get_principal)):
    db.query(AuthSession).filter(AuthSession.user_id == principal.user_id, AuthSession.revoked_at.is_(None)).update(
        {AuthSession.revoked_at: utc_now()}, synchronize_session=False)
    record_event(db, action="auth.logout_all", target_type="user", organization_id=principal.organization_id,
                 actor_user_id=principal.user_id, target_id=principal.user_id)
    db.commit()
    return None
