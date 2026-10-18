"""Tenant-scoped organisation hierarchy CRUD."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, require_permission
from app.identity.models import OrganizationUnit
from app.identity.schemas import OrganizationUnitCreate, OrganizationUnitPatch
from app.identity.security import utc_now

router = APIRouter()
PARENTS = {"business_unit": set(), "location": {"business_unit"},
           "department": {"business_unit", "location"}, "team": {"department"}}


def validate_parent(db, org_id, kind, parent_id):
    if not parent_id:
        if kind != "business_unit":
            raise HTTPException(422, "This unit type requires a parent")
        return
    parent = db.scalar(select(OrganizationUnit).where(OrganizationUnit.id == parent_id,
        OrganizationUnit.organization_id == org_id, OrganizationUnit.status == "active",
        OrganizationUnit.archived_at.is_(None)))
    if parent is None or parent.unit_type not in PARENTS[kind]:
        raise HTTPException(422, "Parent is missing, cross-tenant or has an invalid type")


@router.get("/organizations/{organization_id}/units")
def list_units(organization_id: str, unit_type: str | None = None, parent_id: str | None = None,
    limit: int = 50, offset: int = 0, principal: Principal = Depends(require_permission("organization.units.read")),
    db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    q = select(OrganizationUnit).where(OrganizationUnit.organization_id == organization_id,
        OrganizationUnit.archived_at.is_(None))
    if unit_type:
        if unit_type not in PARENTS:
            raise HTTPException(422, "Invalid unit type")
        q = q.where(OrganizationUnit.unit_type == unit_type)
    if parent_id:
        q = q.where(OrganizationUnit.parent_id == parent_id)
    rows = db.scalars(q.order_by(OrganizationUnit.name).offset(max(0, offset)).limit(max(1, min(limit, 100)))).all()
    return {"items": rows, "limit": max(1, min(limit, 100)), "offset": max(0, offset)}


@router.post("/organizations/{organization_id}/units", status_code=201)
def create_unit(organization_id: str, payload: OrganizationUnitCreate,
    principal: Principal = Depends(require_permission("organization.units.create")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    validate_parent(db, organization_id, payload.unit_type, payload.parent_id)
    unit = OrganizationUnit(organization_id=organization_id, unit_type=payload.unit_type,
        name=payload.name.strip(), code=payload.code.strip() if payload.code else None, parent_id=payload.parent_id)
    db.add(unit)
    try:
        db.flush()
        record_event(db, action="organization.unit.create", target_type="organization_unit",
            organization_id=organization_id, actor_user_id=principal.user_id, target_id=unit.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Organisation unit code already exists") from exc
    db.refresh(unit)
    return unit


@router.patch("/organizations/{organization_id}/units/{unit_id}")
def update_unit(organization_id: str, unit_id: str, payload: OrganizationUnitPatch,
    principal: Principal = Depends(require_permission("organization.units.update")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    unit = db.scalar(select(OrganizationUnit).where(OrganizationUnit.id == unit_id,
        OrganizationUnit.organization_id == organization_id, OrganizationUnit.archived_at.is_(None)))
    if unit is None:
        raise HTTPException(404, "Organisation unit not found")
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        validate_parent(db, organization_id, unit.unit_type, changes["parent_id"])
        if changes["parent_id"] == unit.id:
            raise HTTPException(422, "A unit cannot be its own parent")
        if db.scalar(select(OrganizationUnit.id).where(OrganizationUnit.organization_id == organization_id,
            OrganizationUnit.parent_id == unit.id, OrganizationUnit.archived_at.is_(None))):
            raise HTTPException(409, "Move child units before changing this parent")
    for key, value in changes.items():
        setattr(unit, key, value.strip() if key in {"name", "code"} and value else value)
    try:
        record_event(db, action="organization.unit.update", target_type="organization_unit",
            organization_id=organization_id, actor_user_id=principal.user_id, target_id=unit.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Organisation unit code already exists") from exc
    db.refresh(unit)
    return unit


@router.post("/organizations/{organization_id}/units/{unit_id}/archive", status_code=204)
def archive_unit(organization_id: str, unit_id: str,
    principal: Principal = Depends(require_permission("organization.units.archive")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    unit = db.scalar(select(OrganizationUnit).where(OrganizationUnit.id == unit_id,
        OrganizationUnit.organization_id == organization_id, OrganizationUnit.archived_at.is_(None)))
    if unit is None:
        raise HTTPException(404, "Organisation unit not found")
    if db.scalar(select(OrganizationUnit.id).where(OrganizationUnit.organization_id == organization_id,
        OrganizationUnit.parent_id == unit.id, OrganizationUnit.archived_at.is_(None))):
        raise HTTPException(409, "Archive child units before their parent")
    unit.status, unit.archived_at = "archived", utc_now()
    record_event(db, action="organization.unit.archive", target_type="organization_unit",
        organization_id=organization_id, actor_user_id=principal.user_id, target_id=unit.id)
    db.commit()
