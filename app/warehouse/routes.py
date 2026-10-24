"""Tenant-scoped warehouse and location master-data endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, require_permission
from app.identity.security import utc_now
from app.warehouse.models import Warehouse, WarehouseLocation
from app.warehouse.schemas import (WarehouseCreate, WarehouseLocationCreate,
                                   WarehouseLocationOut, WarehouseLocationPatch,
                                   WarehouseOut, WarehousePatch)

router = APIRouter(tags=["Warehouse"])


def _scope(principal: Principal, organization_id: str) -> None:
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")


def _warehouse(db: Session, organization_id: str, warehouse_id: str) -> Warehouse:
    item = db.scalar(select(Warehouse).where(
        Warehouse.organization_id == organization_id,
        Warehouse.id == warehouse_id,
    ))
    if item is None:
        raise HTTPException(404, "Warehouse not found")
    return item


def _location(db: Session, organization_id: str, warehouse_id: str,
              location_id: str) -> WarehouseLocation:
    item = db.scalar(select(WarehouseLocation).where(
        WarehouseLocation.organization_id == organization_id,
        WarehouseLocation.warehouse_id == warehouse_id,
        WarehouseLocation.id == location_id,
    ))
    if item is None:
        raise HTTPException(404, "Location not found")
    return item


@router.post("/organizations/{organization_id}/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(organization_id: str, payload: WarehouseCreate, request: Request,
                     principal: Principal = Depends(require_permission("warehouse.locations.write")),
                     db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    item = Warehouse(organization_id=organization_id, code=payload.code, name=payload.name,
                     description=payload.description)
    db.add(item)
    try:
        db.flush()
        record_event(db, action="warehouse.create", target_type="warehouse",
                     organization_id=organization_id, actor_user_id=principal.user_id,
                     target_id=item.id, correlation_id=request.headers.get("X-Request-ID"),
                     details={"code": item.code})
        result = WarehouseOut.model_validate(item)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Warehouse code already exists") from exc
    return result


@router.get("/organizations/{organization_id}/warehouses", response_model=dict)
def list_warehouses(organization_id: str, limit: int = Query(50, ge=1, le=100),
                    offset: int = Query(0, ge=0),
                    principal: Principal = Depends(require_permission("warehouse.locations.read")),
                    db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    rows = db.scalars(select(Warehouse).where(
        Warehouse.organization_id == organization_id,
    ).order_by(Warehouse.code, Warehouse.id).offset(offset).limit(limit)).all()
    return {"items": [WarehouseOut.model_validate(row).model_dump() for row in rows],
            "limit": limit, "offset": offset}


@router.get("/organizations/{organization_id}/warehouses/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(organization_id: str, warehouse_id: str,
                  principal: Principal = Depends(require_permission("warehouse.locations.read")),
                  db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    return WarehouseOut.model_validate(_warehouse(db, organization_id, warehouse_id))


@router.patch("/organizations/{organization_id}/warehouses/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(organization_id: str, warehouse_id: str, payload: WarehousePatch, request: Request,
                     principal: Principal = Depends(require_permission("warehouse.locations.write")),
                     db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    item = _warehouse(db, organization_id, warehouse_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("status") == "inactive":
        active_locations = db.scalar(select(func.count()).select_from(WarehouseLocation).where(
            WarehouseLocation.organization_id == organization_id,
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.status == "active",
        ))
        if active_locations:
            raise HTTPException(409, "Deactivate active locations before deactivating the warehouse")
    for field, value in values.items():
        setattr(item, field, value)
    item.updated_at = utc_now()
    record_event(db, action="warehouse.update", target_type="warehouse",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=item.id, correlation_id=request.headers.get("X-Request-ID"),
                 details={"changed_fields": sorted(values)})
    result = WarehouseOut.model_validate(item)
    db.commit()
    return result


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/locations",
             response_model=WarehouseLocationOut, status_code=201)
def create_location(organization_id: str, warehouse_id: str, payload: WarehouseLocationCreate,
                    request: Request,
                    principal: Principal = Depends(require_permission("warehouse.locations.write")),
                    db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    warehouse = _warehouse(db, organization_id, warehouse_id)
    if warehouse.status != "active":
        raise HTTPException(409, "Locations cannot be added to an inactive warehouse")
    if payload.parent_location_id is not None:
        parent = db.scalar(select(WarehouseLocation).where(
            WarehouseLocation.organization_id == organization_id,
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.id == payload.parent_location_id,
        ))
        if parent is None:
            raise HTTPException(404, "Parent location not found")
        if parent.status != "active":
            raise HTTPException(409, "Parent location is not active")
    item = WarehouseLocation(
        organization_id=organization_id,
        warehouse_id=warehouse_id,
        parent_location_id=payload.parent_location_id,
        code=payload.code,
        name=payload.name,
        location_type=payload.location_type,
        capacity_limit=payload.capacity_limit,
        capacity_unit=payload.capacity_unit,
    )
    db.add(item)
    try:
        db.flush()
        record_event(db, action="warehouse.location.create", target_type="warehouse_location",
                     organization_id=organization_id, actor_user_id=principal.user_id,
                     target_id=item.id, correlation_id=request.headers.get("X-Request-ID"),
                     details={"warehouse_id": warehouse_id, "code": item.code,
                              "location_type": item.location_type,
                              "parent_location_id": item.parent_location_id})
        result = WarehouseLocationOut.model_validate(item)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Location code or parent relationship conflicts with an existing record") from exc
    return result


@router.get("/organizations/{organization_id}/warehouses/{warehouse_id}/locations", response_model=dict)
def list_locations(organization_id: str, warehouse_id: str,
                   location_type: str | None = Query(default=None, pattern=r"^(zone|bin|receiving|staging|shipping|quarantine|unassigned)$"),
                   parent_location_id: str | None = Query(default=None, min_length=1, max_length=36),
                   limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                   principal: Principal = Depends(require_permission("warehouse.locations.read")),
                   db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    _warehouse(db, organization_id, warehouse_id)
    query = select(WarehouseLocation).where(
        WarehouseLocation.organization_id == organization_id,
        WarehouseLocation.warehouse_id == warehouse_id,
    )
    if location_type:
        query = query.where(WarehouseLocation.location_type == location_type)
    if parent_location_id is not None:
        query = query.where(WarehouseLocation.parent_location_id == parent_location_id)
    rows = db.scalars(query.order_by(WarehouseLocation.code, WarehouseLocation.id)
                      .offset(offset).limit(limit)).all()
    return {"items": [WarehouseLocationOut.model_validate(row).model_dump() for row in rows],
            "limit": limit, "offset": offset}


@router.patch("/organizations/{organization_id}/warehouses/{warehouse_id}/locations/{location_id}",
              response_model=WarehouseLocationOut)
def update_location(organization_id: str, warehouse_id: str, location_id: str,
                    payload: WarehouseLocationPatch, request: Request,
                    principal: Principal = Depends(require_permission("warehouse.locations.write")),
                    db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    item = _location(db, organization_id, warehouse_id, location_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("status") in {"blocked", "inactive"}:
        active_children = db.scalar(select(func.count()).select_from(WarehouseLocation).where(
            WarehouseLocation.organization_id == organization_id,
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.parent_location_id == location_id,
            WarehouseLocation.status == "active",
        ))
        if active_children:
            raise HTTPException(409, "Update active child locations before blocking this location")
    for field, value in values.items():
        setattr(item, field, value)
    item.updated_at = utc_now()
    record_event(db, action="warehouse.location.update", target_type="warehouse_location",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=item.id, correlation_id=request.headers.get("X-Request-ID"),
                 details={"warehouse_id": warehouse_id, "changed_fields": sorted(values)})
    result = WarehouseLocationOut.model_validate(item)
    db.commit()
    return result
