"""Organisation lifecycle and tenant-scoped membership administration."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, require_permission
from app.identity.models import AuthSession, Membership, MembershipRole, Organization, Role, RolePermission, User
from app.identity.schemas import MemberCreate, MemberPatch, OrganizationOut, OrganizationPatch, UserOut
from app.identity.security import utc_now
router = APIRouter()

@router.get("/organizations/{organization_id}", response_model=OrganizationOut)
def get_organization(organization_id: str, principal: Principal = Depends(require_permission("organization.read")),
                     db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise HTTPException(404, "Organisation not found")
    return org

@router.patch("/organizations/{organization_id}", response_model=OrganizationOut)
def update_organization(organization_id: str, payload: OrganizationPatch,
    principal: Principal = Depends(require_permission("organization.update")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise HTTPException(404, "Organisation not found")
    if payload.name is not None:
        org.name = payload.name
    if payload.status is not None:
        org.status = payload.status
        if payload.status == "suspended":
            db.query(AuthSession).filter(AuthSession.active_organization_id == org.id, AuthSession.revoked_at.is_(None)).update(
                {AuthSession.revoked_at: utc_now()}, synchronize_session=False)
    record_event(db, action="organization.update", target_type="organization", organization_id=org.id,
                 actor_user_id=principal.user_id, target_id=org.id)
    db.commit()
    db.refresh(org)
    return org

@router.post("/organizations/{organization_id}/archive", status_code=204)
def archive_organization(organization_id: str, principal: Principal = Depends(require_permission("organization.archive")),
                         db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        raise HTTPException(404, "Organisation not found")
    org.status = "archived"
    org.archived_at = utc_now()
    db.query(AuthSession).filter(AuthSession.active_organization_id == org.id, AuthSession.revoked_at.is_(None)).update(
        {AuthSession.revoked_at: utc_now()}, synchronize_session=False)
    record_event(db, action="organization.archive", target_type="organization", organization_id=org.id,
                 actor_user_id=principal.user_id, target_id=org.id)
    db.commit()
    return None

@router.get("/organizations/{organization_id}/members")
def list_members(organization_id: str, limit: int = 50, offset: int = 0,
    principal: Principal = Depends(require_permission("members.read")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    limit, offset = max(1, min(limit, 100)), max(0, offset)
    rows = db.execute(select(Membership, User).join(User, User.id == Membership.user_id).where(
        Membership.organization_id == organization_id, Membership.status != "revoked")
        .order_by(Membership.created_at.desc()).offset(offset).limit(limit)).all()
    return {"items": [{"membership_id": m.id, "status": m.status,
        "user": UserOut(id=u.id, email=u.email, full_name=u.full_name, is_active=u.is_active)} for m, u in rows],
        "limit": limit, "offset": offset}

@router.post("/organizations/{organization_id}/members", status_code=201)
def add_member(organization_id: str, payload: MemberCreate,
    principal: Principal = Depends(require_permission("members.invite")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    user = db.get(User, payload.user_id)
    role = db.scalar(select(Role).where(Role.id == payload.role_id, Role.organization_id == organization_id,
                                         Role.archived_at.is_(None)))
    if not user or not user.is_active or user.archived_at is not None or not role:
        raise HTTPException(404, "User or role not found")
    role_permissions = set(db.scalars(select(RolePermission.permission_key).where(
        RolePermission.organization_id == organization_id, RolePermission.role_id == role.id)).all())
    if not role_permissions.issubset(principal.permissions):
        raise HTTPException(403, "Cannot assign a role with permissions you do not hold")
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization_id,
                                                      Membership.user_id == user.id))
    if membership and membership.status == "active":
        raise HTTPException(409, "User is already an active member")
    if membership:
        membership.status = "active"
    else:
        membership = Membership(organization_id=organization_id, user_id=user.id, status="active")
        db.add(membership)
        db.flush()
    if db.scalar(select(MembershipRole.id).where(MembershipRole.organization_id == organization_id,
             MembershipRole.membership_id == membership.id, MembershipRole.role_id == role.id)) is None:
        db.add(MembershipRole(organization_id=organization_id, membership_id=membership.id, role_id=role.id))
    record_event(db, action="membership.create", target_type="membership", organization_id=organization_id,
                 actor_user_id=principal.user_id, target_id=membership.id)
    db.commit()
    return {"membership_id": membership.id, "user_id": user.id, "status": membership.status}

@router.patch("/organizations/{organization_id}/members/{user_id}")
def update_member(organization_id: str, user_id: str, payload: MemberPatch,
    principal: Principal = Depends(require_permission("members.update")), db: Session = Depends(get_identity_session)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes or (changes.get("status") is None and changes.get("role_id") is None):
        raise HTTPException(422, "Provide a status or role_id change")
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization_id,
        Membership.user_id == user_id))
    if not membership:
        raise HTTPException(404, "Member not found")
    status_value = changes.get("status")
    if status_value is not None:
        if user_id == principal.user_id and status_value != "active":
            raise HTTPException(400, "You cannot suspend your own membership")
        membership.status = status_value
        if status_value != "active":
            db.query(AuthSession).filter(AuthSession.user_id == user_id,
                AuthSession.active_organization_id == organization_id, AuthSession.revoked_at.is_(None)).update(
                    {AuthSession.revoked_at: utc_now()}, synchronize_session=False)
    if changes.get("role_id") is not None:
        role = db.scalar(select(Role).where(Role.id == changes["role_id"],
            Role.organization_id == organization_id, Role.archived_at.is_(None)))
        if not role:
            raise HTTPException(404, "Role not found")
        granted = set(db.scalars(select(RolePermission.permission_key).where(
            RolePermission.organization_id == organization_id, RolePermission.role_id == role.id)).all())
        if not granted.issubset(principal.permissions):
            raise HTTPException(403, "Cannot assign a role with permissions you do not hold")
        db.query(MembershipRole).filter(MembershipRole.organization_id == organization_id,
            MembershipRole.membership_id == membership.id).delete(synchronize_session=False)
        db.add(MembershipRole(organization_id=organization_id, membership_id=membership.id, role_id=role.id))
    record_event(db, action="membership.update", target_type="membership", organization_id=organization_id,
                 actor_user_id=principal.user_id, target_id=membership.id)
    db.commit()
    return {"membership_id": membership.id, "status": membership.status}
