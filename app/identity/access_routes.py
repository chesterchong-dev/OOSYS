"""Tenant-scoped roles, permission catalogue and audit history."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, require_permission
from app.identity.models import MembershipRole, Permission, Role, RolePermission
from app.identity.permissions import PERMISSIONS
from app.identity.schemas import RoleCreate, RoleOut, RolePatch
from app.identity.security import utc_now
router = APIRouter()

@router.get("/organizations/{organization_id}/roles", response_model=list[RoleOut])
def list_roles(organization_id: str, principal: Principal = Depends(require_permission("roles.read")),
               db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    return db.scalars(select(Role).where(Role.organization_id == organization_id, Role.archived_at.is_(None))).all()

@router.post("/organizations/{organization_id}/roles", response_model=RoleOut, status_code=201)
def create_role(organization_id: str, payload: RoleCreate,
    principal: Principal = Depends(require_permission("roles.create")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    requested = set(payload.permissions)
    known = set(db.scalars(select(Permission.key).where(Permission.key.in_(requested))).all()) if requested else set()
    if requested != known or not requested.issubset(principal.permissions):
        raise HTTPException(403, "Roles cannot grant unknown or unheld permissions")
    role = Role(organization_id=organization_id, name=payload.name, description=payload.description)
    db.add(role)
    try:
        db.flush()
        db.add_all([RolePermission(organization_id=organization_id, role_id=role.id, permission_key=key)
                    for key in requested])
        record_event(db, action="role.create", target_type="role", organization_id=organization_id,
                     actor_user_id=principal.user_id, target_id=role.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Role name already exists") from exc
    db.refresh(role)
    return role

@router.patch("/organizations/{organization_id}/roles/{role_id}", response_model=RoleOut)
def update_role(organization_id: str, role_id: str, payload: RolePatch,
    principal: Principal = Depends(require_permission("roles.update")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    role = db.scalar(select(Role).where(Role.id == role_id, Role.organization_id == organization_id,
                                        Role.archived_at.is_(None)))
    if not role or role.is_system:
        raise HTTPException(404, "Role not found")
    changes = payload.model_dump(exclude_unset=True)
    if "permissions" in changes:
        requested = set(changes.pop("permissions") or [])
        known = set(db.scalars(select(Permission.key).where(Permission.key.in_(requested))).all()) if requested else set()
        if requested != known or not requested.issubset(principal.permissions):
            raise HTTPException(403, "Roles cannot grant unknown or unheld permissions")
        db.query(RolePermission).filter(RolePermission.organization_id == organization_id,
                                        RolePermission.role_id == role.id).delete(synchronize_session=False)
        db.add_all([RolePermission(organization_id=organization_id, role_id=role.id, permission_key=key)
                    for key in requested])
    for key, value in changes.items():
        if value is not None:
            setattr(role, key, value)
    record_event(db, action="role.update", target_type="role", organization_id=organization_id,
                 actor_user_id=principal.user_id, target_id=role.id)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Role name already exists") from exc
    db.refresh(role)
    return role

@router.post("/organizations/{organization_id}/roles/{role_id}/archive", status_code=204)
def archive_role(organization_id: str, role_id: str,
    principal: Principal = Depends(require_permission("roles.archive")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    role = db.scalar(select(Role).where(Role.id == role_id, Role.organization_id == organization_id,
                                        Role.archived_at.is_(None)))
    if not role or role.is_system:
        raise HTTPException(404, "Role not found")
    role.archived_at = utc_now()
    db.query(MembershipRole).filter(MembershipRole.organization_id == organization_id,
                                    MembershipRole.role_id == role.id).delete(synchronize_session=False)
    db.query(RolePermission).filter(RolePermission.organization_id == organization_id,
                                    RolePermission.role_id == role.id).delete(synchronize_session=False)
    record_event(db, action="role.archive", target_type="role", organization_id=organization_id,
                 actor_user_id=principal.user_id, target_id=role.id)
    db.commit()
    return None

@router.get("/organizations/{organization_id}/permissions")
def list_permissions(organization_id: str, principal: Principal = Depends(require_permission("roles.read")),
                     db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    return [{"key": key, "description": desc} for key, desc in PERMISSIONS.items()]

@router.get("/organizations/{organization_id}/audit-events")
def list_audit_events(organization_id: str, limit: int = 50, offset: int = 0,
    principal: Principal = Depends(require_permission("audit.read")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    from app.identity.models import AuditEvent
    limit, offset = max(1, min(limit, 100)), max(0, offset)
    rows = db.scalars(select(AuditEvent).where(AuditEvent.organization_id == organization_id)
                      .order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)).all()
    return {"items": [{"id": e.id, "actor_user_id": e.actor_user_id, "action": e.action,
        "target_type": e.target_type, "target_id": e.target_id, "outcome": e.outcome,
        "correlation_id": e.correlation_id, "created_at": e.created_at} for e in rows],
        "limit": limit, "offset": offset}
