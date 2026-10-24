"""Tenant-scoped warehouse master data and receiving workflow endpoints."""
import hashlib
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, require_permission
from app.identity.security import utc_now
from app.inventory.contracts import (post_warehouse_putaway_transfer,
                                     post_warehouse_receipt_movement,
                                     post_warehouse_pick_reservation, post_warehouse_pick,
                                     release_warehouse_pick_reservation,
                                     post_warehouse_dispatch_movement)
from app.warehouse.models import (Warehouse, WarehouseLocation, WarehouseReceipt,
                                  WarehouseReceiptLine, WarehousePutawayTask,
                                  WarehouseTransfer, WarehouseReplenishmentTask,
                                  WarehouseOutboundOrder, WarehouseOutboundLine,
                                  WarehousePackage, WarehousePackageLine)
from app.warehouse.schemas import (WarehouseCreate, WarehouseLocationCreate,
                                   WarehouseLocationOut, WarehouseLocationPatch,
                                   WarehouseOut, WarehousePatch, WarehouseReceiptCreate,
                                   WarehouseReceiptOut, WarehousePutawayAssign,
                                   WarehousePutawayTaskOut, WarehouseTransferCreate,
                                   WarehouseTransferOut, WarehouseReplenishmentCreate,
                                   WarehouseReplenishmentOut, WarehouseOutboundOrderCreate,
                                   WarehouseOutboundOrderOut, WarehousePackageCreate,
                                   WarehousePackageOut)

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


def _receipt(db: Session, organization_id: str, warehouse_id: str, receipt_id: str,
             *, lock: bool = False) -> WarehouseReceipt:
    query = select(WarehouseReceipt).where(
        WarehouseReceipt.organization_id == organization_id,
        WarehouseReceipt.warehouse_id == warehouse_id,
        WarehouseReceipt.id == receipt_id,
    )
    if lock:
        query = query.with_for_update()
    receipt = db.scalar(query)
    if receipt is None:
        raise HTTPException(404, "Receipt not found")
    return receipt


def _receipt_out(db: Session, receipt: WarehouseReceipt) -> WarehouseReceiptOut:
    lines = db.scalars(select(WarehouseReceiptLine).where(
        WarehouseReceiptLine.organization_id == receipt.organization_id,
        WarehouseReceiptLine.receipt_id == receipt.id,
    ).order_by(WarehouseReceiptLine.id)).all()
    return WarehouseReceiptOut.model_validate({
        "id": receipt.id,
        "organization_id": receipt.organization_id,
        "warehouse_id": receipt.warehouse_id,
        "receiving_location_id": receipt.receiving_location_id,
        "receipt_number": receipt.receipt_number,
        "source_reference": receipt.source_reference,
        "status": receipt.status,
        "note": receipt.note,
        "created_by_user_id": receipt.created_by_user_id,
        "posted_by_user_id": receipt.posted_by_user_id,
        "created_at": receipt.created_at,
        "posted_at": receipt.posted_at,
        "lines": lines,
    })


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/receipts",
             response_model=WarehouseReceiptOut, status_code=201)
def create_receipt(organization_id: str, warehouse_id: str, payload: WarehouseReceiptCreate,
                   request: Request,
                   principal: Principal = Depends(require_permission("warehouse.receiving.write")),
                   db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    warehouse = _warehouse(db, organization_id, warehouse_id)
    if warehouse.status != "active":
        raise HTTPException(409, "Receipts cannot be created in an inactive warehouse")
    location = _location(db, organization_id, warehouse_id, payload.receiving_location_id)
    if location.status != "active" or location.location_type != "receiving":
        raise HTTPException(409, "Receipts must target an active receiving location")

    request_hash = hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()
    existing = db.scalar(select(WarehouseReceipt).where(
        WarehouseReceipt.organization_id == organization_id,
        WarehouseReceipt.idempotency_key == payload.idempotency_key,
    ))
    if existing is not None:
        if existing.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key was already used for a different receipt")
        return _receipt_out(db, existing)

    receipt = WarehouseReceipt(
        organization_id=organization_id,
        warehouse_id=warehouse_id,
        receiving_location_id=location.id,
        receipt_number=f"RCV-{uuid4().hex[:12].upper()}",
        idempotency_key=payload.idempotency_key,
        request_hash=request_hash,
        source_reference=payload.source_reference,
        note=payload.note,
        created_by_user_id=principal.user_id,
    )
    db.add(receipt)
    db.flush()
    for line in payload.lines:
        db.add(WarehouseReceiptLine(
            organization_id=organization_id,
            receipt_id=receipt.id,
            product_id=line.product_id,
            quantity=line.quantity,
            unit_cost=line.unit_cost,
            lot_code=line.lot_code,
            serial_code=line.serial_code,
            expires_at=line.expires_at,
        ))
    db.flush()
    record_event(db, action="warehouse.receipt.create", target_type="warehouse_receipt",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=receipt.id, correlation_id=request.headers.get("X-Request-ID"),
                 details={"warehouse_id": warehouse_id, "line_count": len(payload.lines),
                          "source_reference": payload.source_reference})
    result = _receipt_out(db, receipt)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Receipt number or idempotency key conflicts with an existing receipt") from exc
    return result


@router.get("/organizations/{organization_id}/warehouses/{warehouse_id}/receipts", response_model=dict)
def list_receipts(organization_id: str, warehouse_id: str,
                  status: str | None = Query(default=None, pattern=r"^(draft|posted)$"),
                  limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                  principal: Principal = Depends(require_permission("warehouse.receiving.read")),
                  db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    _warehouse(db, organization_id, warehouse_id)
    query = select(WarehouseReceipt).where(
        WarehouseReceipt.organization_id == organization_id,
        WarehouseReceipt.warehouse_id == warehouse_id,
    )
    if status:
        query = query.where(WarehouseReceipt.status == status)
    receipts = db.scalars(query.order_by(WarehouseReceipt.created_at.desc(), WarehouseReceipt.id.desc())
                          .offset(offset).limit(limit)).all()
    return {"items": [_receipt_out(db, receipt).model_dump() for receipt in receipts],
            "limit": limit, "offset": offset}


@router.get("/organizations/{organization_id}/warehouses/{warehouse_id}/receipts/{receipt_id}",
            response_model=WarehouseReceiptOut)
def get_receipt(organization_id: str, warehouse_id: str, receipt_id: str,
                principal: Principal = Depends(require_permission("warehouse.receiving.read")),
                db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    return _receipt_out(db, _receipt(db, organization_id, warehouse_id, receipt_id))


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/receipts/{receipt_id}/post",
             response_model=WarehouseReceiptOut)
def post_receipt(organization_id: str, warehouse_id: str, receipt_id: str, request: Request,
                 principal: Principal = Depends(require_permission("warehouse.receiving.write")),
                 db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    receipt = _receipt(db, organization_id, warehouse_id, receipt_id, lock=True)
    if receipt.status == "posted":
        return _receipt_out(db, receipt)
    warehouse = _warehouse(db, organization_id, warehouse_id)
    location = _location(db, organization_id, warehouse_id, receipt.receiving_location_id)
    if warehouse.status != "active" or location.status != "active" or location.location_type != "receiving":
        raise HTTPException(409, "Warehouse and receiving location must remain active to post a receipt")
    lines = db.scalars(select(WarehouseReceiptLine).where(
        WarehouseReceiptLine.organization_id == organization_id,
        WarehouseReceiptLine.receipt_id == receipt.id,
    ).order_by(WarehouseReceiptLine.id)).all()
    try:
        for line in lines:
            post_warehouse_receipt_movement(
                db, organization_id, principal.user_id,
                product_id=line.product_id,
                quantity=line.quantity,
                location_id=receipt.receiving_location_id,
                idempotency_key=f"warehouse-receipt:{receipt.id}:{line.id}",
                unit_cost=line.unit_cost,
                lot_code=line.lot_code,
                serial_code=line.serial_code,
                expires_at=line.expires_at,
                note=f"Receipt {receipt.receipt_number}: {receipt.note}"[:500],
                correlation_id=request.headers.get("X-Request-ID"),
            )
            db.add(WarehousePutawayTask(
                organization_id=organization_id,
                warehouse_id=warehouse_id,
                receipt_id=receipt.id,
                receipt_line_id=line.id,
                product_id=line.product_id,
                source_location_id=receipt.receiving_location_id,
                quantity=line.quantity,
                lot_code=line.lot_code,
                serial_code=line.serial_code,
                expires_at=line.expires_at,
            ))
        db.flush()
        receipt.status = "posted"
        receipt.posted_by_user_id = principal.user_id
        receipt.posted_at = utc_now()
        record_event(db, action="warehouse.receipt.post", target_type="warehouse_receipt",
                     organization_id=organization_id, actor_user_id=principal.user_id,
                     target_id=receipt.id, correlation_id=request.headers.get("X-Request-ID"),
                     details={"movement_count": len(lines), "receipt_number": receipt.receipt_number})
        result = _receipt_out(db, receipt)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Receipt conflicts with a previous stock update") from exc
    except HTTPException:
        db.rollback()
        raise
    return result


@router.get("/organizations/{organization_id}/warehouses/{warehouse_id}/putaway-tasks",
            response_model=dict)
def list_putaway_tasks(organization_id: str, warehouse_id: str,
                       status: str | None = Query(default=None, pattern=r"^(pending|assigned|completed)$"),
                       limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                       principal: Principal = Depends(require_permission("warehouse.putaway.read")),
                       db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    _warehouse(db, organization_id, warehouse_id)
    query = select(WarehousePutawayTask).where(
        WarehousePutawayTask.organization_id == organization_id,
        WarehousePutawayTask.warehouse_id == warehouse_id,
    )
    if status:
        query = query.where(WarehousePutawayTask.status == status)
    tasks = db.scalars(query.order_by(WarehousePutawayTask.created_at, WarehousePutawayTask.id)
                       .offset(offset).limit(limit)).all()
    return {"items": [WarehousePutawayTaskOut.model_validate(task).model_dump() for task in tasks],
            "limit": limit, "offset": offset}


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/putaway-tasks/{task_id}/assign",
             response_model=WarehousePutawayTaskOut)
def assign_putaway_task(organization_id: str, warehouse_id: str, task_id: str,
                        payload: WarehousePutawayAssign, request: Request,
                        principal: Principal = Depends(require_permission("warehouse.putaway.write")),
                        db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    task = db.scalar(select(WarehousePutawayTask).where(
        WarehousePutawayTask.organization_id == organization_id,
        WarehousePutawayTask.warehouse_id == warehouse_id,
        WarehousePutawayTask.id == task_id,
    ).with_for_update())
    if task is None:
        raise HTTPException(404, "Putaway task not found")
    if task.status != "pending":
        raise HTTPException(409, "Only pending putaway tasks can be assigned")
    destination = _location(db, organization_id, warehouse_id, payload.destination_location_id)
    if destination.id == task.source_location_id:
        raise HTTPException(409, "Putaway source and destination must differ")
    if destination.status != "active" or destination.location_type not in {"bin", "staging", "quarantine", "unassigned"}:
        raise HTTPException(409, "Destination must be an active storage or handling location")
    task.destination_location_id = destination.id
    task.status = "assigned"
    task.assigned_by_user_id = principal.user_id
    task.assigned_at = utc_now()
    record_event(db, action="warehouse.putaway.assign", target_type="warehouse_putaway_task",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=task.id, correlation_id=request.headers.get("X-Request-ID"),
                 details={"destination_location_id": destination.id})
    result = WarehousePutawayTaskOut.model_validate(task)
    db.commit()
    return result


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/putaway-tasks/{task_id}/complete",
             response_model=WarehousePutawayTaskOut)
def complete_putaway_task(organization_id: str, warehouse_id: str, task_id: str, request: Request,
                          principal: Principal = Depends(require_permission("warehouse.putaway.write")),
                          db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    task = db.scalar(select(WarehousePutawayTask).where(
        WarehousePutawayTask.organization_id == organization_id,
        WarehousePutawayTask.warehouse_id == warehouse_id,
        WarehousePutawayTask.id == task_id,
    ).with_for_update())
    if task is None:
        raise HTTPException(404, "Putaway task not found")
    if task.status == "completed":
        return WarehousePutawayTaskOut.model_validate(task)
    if task.status != "assigned" or task.destination_location_id is None:
        raise HTTPException(409, "Assign a destination before completing putaway")
    source = _location(db, organization_id, warehouse_id, task.source_location_id)
    destination = _location(db, organization_id, warehouse_id, task.destination_location_id)
    if (source.status != "active" or destination.status != "active"
            or destination.location_type not in {"bin", "staging", "quarantine", "unassigned"}):
        raise HTTPException(409, "Putaway source and destination must remain active")
    receipt_line = db.scalar(select(WarehouseReceiptLine).where(
        WarehouseReceiptLine.organization_id == organization_id,
        WarehouseReceiptLine.receipt_id == task.receipt_id,
        WarehouseReceiptLine.id == task.receipt_line_id,
    ))
    if receipt_line is None:
        raise HTTPException(409, "Putaway receipt line is unavailable")
    try:
        post_warehouse_putaway_transfer(
            db, organization_id, principal.user_id,
            product_id=task.product_id,
            quantity=task.quantity,
            source_location_id=task.source_location_id,
            destination_location_id=task.destination_location_id,
            operation_key=f"warehouse-putaway:{task.id}",
            lot_code=task.lot_code,
            serial_code=task.serial_code,
            expires_at=task.expires_at,
            note=f"Putaway for receipt line {receipt_line.id}",
            correlation_id=request.headers.get("X-Request-ID"),
        )
        task.status = "completed"
        task.completed_by_user_id = principal.user_id
        task.completed_at = utc_now()
        record_event(db, action="warehouse.putaway.complete", target_type="warehouse_putaway_task",
                     organization_id=organization_id, actor_user_id=principal.user_id,
                     target_id=task.id, correlation_id=request.headers.get("X-Request-ID"),
                     details={"source_location_id": source.id,
                              "destination_location_id": destination.id,
                              "quantity": str(task.quantity)})
        result = WarehousePutawayTaskOut.model_validate(task)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Putaway conflicts with a previous stock update") from exc
    except HTTPException:
        db.rollback()
        raise
    return result


def _transfer(db: Session, organization_id: str, transfer_id: str,
              *, lock: bool = False) -> WarehouseTransfer:
    query = select(WarehouseTransfer).where(
        WarehouseTransfer.organization_id == organization_id,
        WarehouseTransfer.id == transfer_id,
    )
    if lock:
        query = query.with_for_update()
    transfer = db.scalar(query)
    if transfer is None:
        raise HTTPException(404, "Transfer not found")
    return transfer


@router.post("/organizations/{organization_id}/warehouse-transfers",
             response_model=WarehouseTransferOut, status_code=201)
def create_transfer(organization_id: str, payload: WarehouseTransferCreate, request: Request,
                   principal: Principal = Depends(require_permission("warehouse.transfers.write")),
                   db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    source_warehouse = _warehouse(db, organization_id, payload.source_warehouse_id)
    destination_warehouse = _warehouse(db, organization_id, payload.destination_warehouse_id)
    source = _location(db, organization_id, source_warehouse.id, payload.source_location_id)
    destination = _location(db, organization_id, destination_warehouse.id, payload.destination_location_id)
    for warehouse, location in ((source_warehouse, source), (destination_warehouse, destination)):
        if warehouse.status != "active" or location.status != "active":
            raise HTTPException(409, "Transfer warehouses and locations must be active")
        if location.location_type == "zone":
            raise HTTPException(409, "Transfers require operational locations, not zones")

    request_hash = hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()
    existing = db.scalar(select(WarehouseTransfer).where(
        WarehouseTransfer.organization_id == organization_id,
        WarehouseTransfer.idempotency_key == payload.idempotency_key,
    ))
    if existing is not None:
        if existing.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key was already used for a different transfer")
        return WarehouseTransferOut.model_validate(existing)

    transfer_id = str(uuid4())
    transfer = WarehouseTransfer(
        id=transfer_id,
        organization_id=organization_id,
        transfer_number=f"TR-{uuid4().hex[:12].upper()}",
        idempotency_key=payload.idempotency_key,
        request_hash=request_hash,
        source_warehouse_id=source_warehouse.id,
        source_location_id=source.id,
        destination_warehouse_id=destination_warehouse.id,
        destination_location_id=destination.id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        lot_code=payload.lot_code,
        serial_code=payload.serial_code,
        expires_at=payload.expires_at,
        external_reference=payload.external_reference,
        created_by_user_id=principal.user_id,
    )
    db.add(transfer)
    db.flush()
    record_event(db, action="warehouse.transfer.create", target_type="warehouse_transfer",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=transfer.id, correlation_id=request.headers.get("X-Request-ID"),
                 details={"transfer_number": transfer.transfer_number,
                          "source_location_id": source.id,
                          "destination_location_id": destination.id,
                          "product_id": transfer.product_id})
    result = WarehouseTransferOut.model_validate(transfer)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Transfer number or idempotency key conflicts with an existing transfer") from exc
    return result


@router.get("/organizations/{organization_id}/warehouse-transfers", response_model=dict)
def list_transfers(organization_id: str,
                   status: str | None = Query(default=None, pattern=r"^(draft|in_transit|received)$"),
                   limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                   principal: Principal = Depends(require_permission("warehouse.transfers.read")),
                   db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    query = select(WarehouseTransfer).where(WarehouseTransfer.organization_id == organization_id)
    if status:
        query = query.where(WarehouseTransfer.status == status)
    rows = db.scalars(query.order_by(WarehouseTransfer.created_at.desc(), WarehouseTransfer.id.desc())
                      .offset(offset).limit(limit)).all()
    return {"items": [WarehouseTransferOut.model_validate(row).model_dump() for row in rows],
            "limit": limit, "offset": offset}


@router.get("/organizations/{organization_id}/warehouse-transfers/{transfer_id}",
            response_model=WarehouseTransferOut)
def get_transfer(organization_id: str, transfer_id: str,
                 principal: Principal = Depends(require_permission("warehouse.transfers.read")),
                 db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    return WarehouseTransferOut.model_validate(_transfer(db, organization_id, transfer_id))


@router.post("/organizations/{organization_id}/warehouse-transfers/{transfer_id}/dispatch",
             response_model=WarehouseTransferOut)
def dispatch_transfer(organization_id: str, transfer_id: str, request: Request,
                      principal: Principal = Depends(require_permission("warehouse.transfers.write")),
                      db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    transfer = _transfer(db, organization_id, transfer_id, lock=True)
    if transfer.status in {"in_transit", "received"}:
        return WarehouseTransferOut.model_validate(transfer)
    source_warehouse = _warehouse(db, organization_id, transfer.source_warehouse_id)
    source = _location(db, organization_id, transfer.source_warehouse_id, transfer.source_location_id)
    destination_warehouse = _warehouse(db, organization_id, transfer.destination_warehouse_id)
    destination = _location(db, organization_id, transfer.destination_warehouse_id,
                             transfer.destination_location_id)
    if any(item.status != "active" for item in (source_warehouse, source, destination_warehouse, destination)):
        raise HTTPException(409, "Transfer warehouses and source/destination locations must remain active")

    transit = WarehouseLocation(
        organization_id=organization_id,
        warehouse_id=source_warehouse.id,
        code=f"TR-{transfer.id.replace('-', '')[:16].upper()}",
        name=f"In transit {transfer.transfer_number}",
        location_type="staging",
    )
    db.add(transit)
    try:
        db.flush()
        post_warehouse_putaway_transfer(
            db, organization_id, principal.user_id,
            product_id=transfer.product_id,
            quantity=transfer.quantity,
            source_location_id=source.id,
            destination_location_id=transit.id,
            operation_key=f"warehouse-transfer:{transfer.id}:dispatch",
            lot_code=transfer.lot_code,
            serial_code=transfer.serial_code,
            expires_at=transfer.expires_at,
            note=f"Transfer {transfer.transfer_number} dispatched",
            correlation_id=request.headers.get("X-Request-ID"),
        )
        transfer.in_transit_location_id = transit.id
        transfer.status = "in_transit"
        transfer.dispatched_by_user_id = principal.user_id
        transfer.dispatched_at = utc_now()
        record_event(db, action="warehouse.transfer.dispatch", target_type="warehouse_transfer",
                     organization_id=organization_id, actor_user_id=principal.user_id,
                     target_id=transfer.id, correlation_id=request.headers.get("X-Request-ID"),
                     details={"in_transit_location_id": transit.id,
                              "quantity": str(transfer.quantity)})
        result = WarehouseTransferOut.model_validate(transfer)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Transfer dispatch conflicts with a previous stock update") from exc
    except HTTPException:
        db.rollback()
        raise
    return result


@router.post("/organizations/{organization_id}/warehouse-transfers/{transfer_id}/receive",
             response_model=WarehouseTransferOut)
def receive_transfer(organization_id: str, transfer_id: str, request: Request,
                    principal: Principal = Depends(require_permission("warehouse.transfers.write")),
                    db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    transfer = _transfer(db, organization_id, transfer_id, lock=True)
    if transfer.status == "received":
        return WarehouseTransferOut.model_validate(transfer)
    if transfer.status != "in_transit" or transfer.in_transit_location_id is None:
        raise HTTPException(409, "Only a dispatched transfer can be received")
    destination_warehouse = _warehouse(db, organization_id, transfer.destination_warehouse_id)
    transit = _location(db, organization_id, transfer.source_warehouse_id,
                        transfer.in_transit_location_id)
    destination = _location(db, organization_id, transfer.destination_warehouse_id,
                            transfer.destination_location_id)
    if (destination_warehouse.status != "active" or transit.status != "active"
            or destination.status != "active" or destination.location_type == "zone"):
        raise HTTPException(409, "Transit and destination locations must remain active")
    try:
        post_warehouse_putaway_transfer(
            db, organization_id, principal.user_id,
            product_id=transfer.product_id,
            quantity=transfer.quantity,
            source_location_id=transit.id,
            destination_location_id=destination.id,
            operation_key=f"warehouse-transfer:{transfer.id}:receive",
            lot_code=transfer.lot_code,
            serial_code=transfer.serial_code,
            expires_at=transfer.expires_at,
            note=f"Transfer {transfer.transfer_number} received",
            correlation_id=request.headers.get("X-Request-ID"),
        )
        transfer.status = "received"
        transfer.received_by_user_id = principal.user_id
        transfer.received_at = utc_now()
        record_event(db, action="warehouse.transfer.receive", target_type="warehouse_transfer",
                     organization_id=organization_id, actor_user_id=principal.user_id,
                     target_id=transfer.id, correlation_id=request.headers.get("X-Request-ID"),
                     details={"destination_location_id": destination.id,
                              "quantity": str(transfer.quantity)})
        result = WarehouseTransferOut.model_validate(transfer)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Transfer receipt conflicts with a previous stock update") from exc
    except HTTPException:
        db.rollback()
        raise
    return result


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/replenishment-tasks",
             response_model=WarehouseReplenishmentOut, status_code=201)
def create_replenishment_task(organization_id: str, warehouse_id: str,
                              payload: WarehouseReplenishmentCreate, request: Request,
                              principal: Principal = Depends(require_permission("warehouse.replenishment.write")),
                              db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    warehouse = _warehouse(db, organization_id, warehouse_id)
    if warehouse.status != "active":
        raise HTTPException(409, "Replenishment cannot be created in an inactive warehouse")
    source = _location(db, organization_id, warehouse_id, payload.source_location_id)
    destination = _location(db, organization_id, warehouse_id, payload.destination_location_id)
    if (source.status != "active" or source.location_type not in {"bin", "staging", "unassigned"}
            or destination.status != "active" or destination.location_type != "bin"):
        raise HTTPException(409, "Replenishment requires active reserve and bin locations")

    request_hash = hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()
    existing = db.scalar(select(WarehouseReplenishmentTask).where(
        WarehouseReplenishmentTask.organization_id == organization_id,
        WarehouseReplenishmentTask.idempotency_key == payload.idempotency_key,
    ))
    if existing is not None:
        if existing.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key was already used for a different replenishment")
        return WarehouseReplenishmentOut.model_validate(existing)

    task = WarehouseReplenishmentTask(
        organization_id=organization_id,
        warehouse_id=warehouse_id,
        product_id=payload.product_id,
        source_location_id=source.id,
        destination_location_id=destination.id,
        quantity=payload.quantity,
        lot_code=payload.lot_code,
        serial_code=payload.serial_code,
        expires_at=payload.expires_at,
        idempotency_key=payload.idempotency_key,
        request_hash=request_hash,
        created_by_user_id=principal.user_id,
    )
    db.add(task)
    db.flush()
    record_event(db, action="warehouse.replenishment.create", target_type="warehouse_replenishment_task",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=task.id, correlation_id=request.headers.get("X-Request-ID"),
                 details={"warehouse_id": warehouse_id, "product_id": payload.product_id,
                          "source_location_id": source.id, "destination_location_id": destination.id,
                          "quantity": str(payload.quantity)})
    result = WarehouseReplenishmentOut.model_validate(task)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Replenishment conflicts with an existing idempotency key") from exc
    return result


@router.get("/organizations/{organization_id}/warehouses/{warehouse_id}/replenishment-tasks",
            response_model=dict)
def list_replenishment_tasks(organization_id: str, warehouse_id: str,
                             status: str | None = Query(default=None, pattern=r"^(pending|completed)$"),
                             limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                             principal: Principal = Depends(require_permission("warehouse.replenishment.read")),
                             db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    _warehouse(db, organization_id, warehouse_id)
    query = select(WarehouseReplenishmentTask).where(
        WarehouseReplenishmentTask.organization_id == organization_id,
        WarehouseReplenishmentTask.warehouse_id == warehouse_id,
    )
    if status:
        query = query.where(WarehouseReplenishmentTask.status == status)
    rows = db.scalars(query.order_by(WarehouseReplenishmentTask.created_at,
                                     WarehouseReplenishmentTask.id)
                      .offset(offset).limit(limit)).all()
    return {"items": [WarehouseReplenishmentOut.model_validate(row).model_dump() for row in rows],
            "limit": limit, "offset": offset}


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/replenishment-tasks/{task_id}/complete",
             response_model=WarehouseReplenishmentOut)
def complete_replenishment_task(organization_id: str, warehouse_id: str, task_id: str,
                                request: Request,
                                principal: Principal = Depends(require_permission("warehouse.replenishment.write")),
                                db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    task = db.scalar(select(WarehouseReplenishmentTask).where(
        WarehouseReplenishmentTask.organization_id == organization_id,
        WarehouseReplenishmentTask.warehouse_id == warehouse_id,
        WarehouseReplenishmentTask.id == task_id,
    ).with_for_update())
    if task is None:
        raise HTTPException(404, "Replenishment task not found")
    if task.status == "completed":
        return WarehouseReplenishmentOut.model_validate(task)
    warehouse = _warehouse(db, organization_id, warehouse_id)
    source = _location(db, organization_id, warehouse_id, task.source_location_id)
    destination = _location(db, organization_id, warehouse_id, task.destination_location_id)
    if (warehouse.status != "active" or source.status != "active" or destination.status != "active"
            or source.location_type not in {"bin", "staging", "unassigned"}
            or destination.location_type != "bin"):
        raise HTTPException(409, "Replenishment warehouse and locations must remain active")
    try:
        post_warehouse_putaway_transfer(
            db, organization_id, principal.user_id,
            product_id=task.product_id,
            quantity=task.quantity,
            source_location_id=source.id,
            destination_location_id=destination.id,
            operation_key=f"warehouse-replenishment:{task.id}",
            lot_code=task.lot_code,
            serial_code=task.serial_code,
            expires_at=task.expires_at,
            note=f"Replenishment task {task.id}",
            correlation_id=request.headers.get("X-Request-ID"),
        )
        task.status = "completed"
        task.completed_by_user_id = principal.user_id
        task.completed_at = utc_now()
        record_event(db, action="warehouse.replenishment.complete",
                     target_type="warehouse_replenishment_task",
                     organization_id=organization_id, actor_user_id=principal.user_id,
                     target_id=task.id, correlation_id=request.headers.get("X-Request-ID"),
                     details={"source_location_id": source.id,
                              "destination_location_id": destination.id,
                              "quantity": str(task.quantity)})
        result = WarehouseReplenishmentOut.model_validate(task)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Replenishment conflicts with a previous stock update") from exc
    except HTTPException:
        db.rollback()
        raise
    return result


def _outbound_order(db: Session, organization_id: str, warehouse_id: str,
                    order_id: str, *, lock: bool = False) -> WarehouseOutboundOrder:
    query = select(WarehouseOutboundOrder).where(
        WarehouseOutboundOrder.organization_id == organization_id,
        WarehouseOutboundOrder.warehouse_id == warehouse_id,
        WarehouseOutboundOrder.id == order_id,
    )
    if lock:
        query = query.with_for_update()
    order = db.scalar(query)
    if order is None:
        raise HTTPException(404, "Outbound order not found")
    return order


def _outbound_order_out(db: Session, order: WarehouseOutboundOrder) -> WarehouseOutboundOrderOut:
    lines = db.scalars(select(WarehouseOutboundLine).where(
        WarehouseOutboundLine.organization_id == order.organization_id,
        WarehouseOutboundLine.order_id == order.id,
    ).order_by(WarehouseOutboundLine.id)).all()
    return WarehouseOutboundOrderOut.model_validate({
        "id": order.id, "organization_id": order.organization_id, "warehouse_id": order.warehouse_id,
        "order_number": order.order_number, "external_reference": order.external_reference,
        "shipping_location_id": order.shipping_location_id, "status": order.status,
        "created_by_user_id": order.created_by_user_id, "reserved_by_user_id": order.reserved_by_user_id,
        "picked_by_user_id": order.picked_by_user_id, "packed_by_user_id": order.packed_by_user_id,
        "dispatched_by_user_id": order.dispatched_by_user_id,
        "cancelled_by_user_id": order.cancelled_by_user_id, "created_at": order.created_at,
        "reserved_at": order.reserved_at, "picked_at": order.picked_at, "packed_at": order.packed_at,
        "dispatched_at": order.dispatched_at, "cancelled_at": order.cancelled_at, "lines": lines,
    })


def _package_out(db: Session, package: WarehousePackage) -> WarehousePackageOut:
    lines = db.scalars(select(WarehousePackageLine).where(
        WarehousePackageLine.organization_id == package.organization_id,
        WarehousePackageLine.package_id == package.id,
    ).order_by(WarehousePackageLine.id)).all()
    return WarehousePackageOut.model_validate({
        "id": package.id, "organization_id": package.organization_id, "order_id": package.order_id,
        "package_number": package.package_number, "status": package.status,
        "created_by_user_id": package.created_by_user_id, "sealed_by_user_id": package.sealed_by_user_id,
        "created_at": package.created_at, "sealed_at": package.sealed_at, "lines": lines,
    })


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders",
             response_model=WarehouseOutboundOrderOut, status_code=201)
def create_outbound_order(organization_id: str, warehouse_id: str,
                          payload: WarehouseOutboundOrderCreate, request: Request,
                          principal: Principal = Depends(require_permission("warehouse.outbound.write")),
                          db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    warehouse = _warehouse(db, organization_id, warehouse_id)
    if warehouse.status != "active":
        raise HTTPException(409, "Outbound orders cannot be created in an inactive warehouse")
    for line in payload.lines:
        source = _location(db, organization_id, warehouse_id, line.source_location_id)
        if source.status != "active" or source.location_type != "bin":
            raise HTTPException(409, "Outbound lines must be picked from active bin locations")
    request_hash = hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()
    existing = db.scalar(select(WarehouseOutboundOrder).where(
        WarehouseOutboundOrder.organization_id == organization_id,
        WarehouseOutboundOrder.idempotency_key == payload.idempotency_key,
    ))
    if existing is not None:
        if existing.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key was already used for a different outbound order")
        return _outbound_order_out(db, existing)
    order = WarehouseOutboundOrder(
        organization_id=organization_id, warehouse_id=warehouse_id,
        order_number=f"OUT-{uuid4().hex[:12].upper()}",
        idempotency_key=payload.idempotency_key, request_hash=request_hash,
        external_reference=payload.external_reference, created_by_user_id=principal.user_id,
    )
    db.add(order)
    db.flush()
    for line in payload.lines:
        db.add(WarehouseOutboundLine(
            organization_id=organization_id, warehouse_id=warehouse_id,
            order_id=order.id, product_id=line.product_id,
            source_location_id=line.source_location_id, quantity=line.quantity,
            lot_code=line.lot_code, serial_code=line.serial_code, expires_at=line.expires_at,
        ))
    db.flush()
    record_event(db, action="warehouse.outbound.create", target_type="warehouse_outbound_order",
                 organization_id=organization_id, actor_user_id=principal.user_id, target_id=order.id,
                 correlation_id=request.headers.get("X-Request-ID"),
                 details={"warehouse_id": warehouse_id, "line_count": len(payload.lines),
                          "external_reference": payload.external_reference})
    result = _outbound_order_out(db, order)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Outbound order conflicts with an existing idempotency key") from exc
    return result


@router.get("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders",
            response_model=dict)
def list_outbound_orders(organization_id: str, warehouse_id: str,
                         status: str | None = Query(default=None,
                             pattern=r"^(draft|reserved|picked|packed|dispatched|cancelled)$"),
                         limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                         principal: Principal = Depends(require_permission("warehouse.outbound.read")),
                         db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    _warehouse(db, organization_id, warehouse_id)
    query = select(WarehouseOutboundOrder).where(
        WarehouseOutboundOrder.organization_id == organization_id,
        WarehouseOutboundOrder.warehouse_id == warehouse_id,
    )
    if status:
        query = query.where(WarehouseOutboundOrder.status == status)
    rows = db.scalars(query.order_by(WarehouseOutboundOrder.created_at.desc(),
                                     WarehouseOutboundOrder.id.desc())
                      .offset(offset).limit(limit)).all()
    return {"items": [_outbound_order_out(db, row).model_dump() for row in rows],
            "limit": limit, "offset": offset}


@router.get("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders/{order_id}",
            response_model=WarehouseOutboundOrderOut)
def get_outbound_order(organization_id: str, warehouse_id: str, order_id: str,
                       principal: Principal = Depends(require_permission("warehouse.outbound.read")),
                       db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    return _outbound_order_out(db, _outbound_order(db, organization_id, warehouse_id, order_id))


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders/{order_id}/reserve",
             response_model=WarehouseOutboundOrderOut)
def reserve_outbound_order(organization_id: str, warehouse_id: str, order_id: str, request: Request,
                           principal: Principal = Depends(require_permission("warehouse.outbound.write")),
                           db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    order = _outbound_order(db, organization_id, warehouse_id, order_id, lock=True)
    if order.status == "reserved":
        return _outbound_order_out(db, order)
    if order.status != "draft":
        raise HTTPException(409, "Only draft outbound orders can be reserved")
    warehouse = _warehouse(db, organization_id, warehouse_id)
    if warehouse.status != "active":
        raise HTTPException(409, "Outbound warehouse must remain active")
    lines = db.scalars(select(WarehouseOutboundLine).where(
        WarehouseOutboundLine.organization_id == organization_id,
        WarehouseOutboundLine.order_id == order.id,
    ).order_by(WarehouseOutboundLine.id)).all()
    try:
        for line in lines:
            source = _location(db, organization_id, warehouse_id, line.source_location_id)
            if source.status != "active" or source.location_type != "bin":
                raise HTTPException(409, "Pick locations must remain active bins")
            post_warehouse_pick_reservation(
                db, organization_id, principal.user_id, product_id=line.product_id,
                quantity=line.quantity, location_id=source.id,
                operation_key=f"warehouse-outbound:{order.id}:{line.id}",
                lot_code=line.lot_code, serial_code=line.serial_code, expires_at=line.expires_at,
                note=f"Reservation for outbound {order.order_number}",
                correlation_id=request.headers.get("X-Request-ID"),
            )
        order.status = "reserved"
        order.reserved_by_user_id = principal.user_id
        order.reserved_at = utc_now()
        record_event(db, action="warehouse.outbound.reserve", target_type="warehouse_outbound_order",
                     organization_id=organization_id, actor_user_id=principal.user_id, target_id=order.id,
                     correlation_id=request.headers.get("X-Request-ID"), details={"line_count": len(lines)})
        result = _outbound_order_out(db, order)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Outbound reservation conflicts with a previous stock update") from exc
    except HTTPException:
        db.rollback()
        raise
    return result


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders/{order_id}/pick",
             response_model=WarehouseOutboundOrderOut)
def pick_outbound_order(organization_id: str, warehouse_id: str, order_id: str, request: Request,
                        principal: Principal = Depends(require_permission("warehouse.outbound.write")),
                        db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    order = _outbound_order(db, organization_id, warehouse_id, order_id, lock=True)
    if order.status == "picked":
        return _outbound_order_out(db, order)
    if order.status != "reserved":
        raise HTTPException(409, "Reserve the outbound order before picking")
    warehouse = _warehouse(db, organization_id, warehouse_id)
    if warehouse.status != "active":
        raise HTTPException(409, "Outbound warehouse must remain active")
    transit = WarehouseLocation(
        organization_id=organization_id, warehouse_id=warehouse_id,
        code=f"SHIP-{order.id[:12].upper()}", name=f"Shipping staging {order.order_number}",
        location_type="shipping", status="active",
    )
    db.add(transit)
    db.flush()
    lines = db.scalars(select(WarehouseOutboundLine).where(
        WarehouseOutboundLine.organization_id == organization_id,
        WarehouseOutboundLine.order_id == order.id,
    ).order_by(WarehouseOutboundLine.id)).all()
    try:
        for line in lines:
            source = _location(db, organization_id, warehouse_id, line.source_location_id)
            if source.status != "active" or source.location_type != "bin":
                raise HTTPException(409, "Pick locations must remain active bins")
            post_warehouse_pick(
                db, organization_id, principal.user_id, product_id=line.product_id,
                quantity=line.quantity, source_location_id=source.id,
                shipping_location_id=transit.id,
                operation_key=f"warehouse-outbound:{order.id}:{line.id}:pick",
                lot_code=line.lot_code, serial_code=line.serial_code, expires_at=line.expires_at,
                note=f"Pick for outbound {order.order_number}",
                correlation_id=request.headers.get("X-Request-ID"),
            )
        order.shipping_location_id = transit.id
        order.status = "picked"
        order.picked_by_user_id = principal.user_id
        order.picked_at = utc_now()
        record_event(db, action="warehouse.outbound.pick", target_type="warehouse_outbound_order",
                     organization_id=organization_id, actor_user_id=principal.user_id, target_id=order.id,
                     correlation_id=request.headers.get("X-Request-ID"),
                     details={"shipping_location_id": transit.id, "line_count": len(lines)})
        result = _outbound_order_out(db, order)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Outbound pick conflicts with a previous stock update") from exc
    except HTTPException:
        db.rollback()
        raise
    return result


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders/{order_id}/packages",
             response_model=WarehousePackageOut, status_code=201)
def create_package(organization_id: str, warehouse_id: str, order_id: str,
                   payload: WarehousePackageCreate, request: Request,
                   principal: Principal = Depends(require_permission("warehouse.packing.write")),
                   db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    order = _outbound_order(db, organization_id, warehouse_id, order_id, lock=True)
    if order.status not in {"picked", "packed"}:
        raise HTTPException(409, "Only picked outbound orders can be packed")
    request_hash = hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()
    existing = db.scalar(select(WarehousePackage).where(
        WarehousePackage.organization_id == organization_id,
        WarehousePackage.idempotency_key == payload.idempotency_key,
    ))
    if existing is not None:
        if existing.order_id != order.id or existing.request_hash != request_hash:
            raise HTTPException(409, "Package idempotency key was already used for another request")
        return _package_out(db, existing)
    outbound_lines = {line.id: line for line in db.scalars(select(WarehouseOutboundLine).where(
        WarehouseOutboundLine.organization_id == organization_id,
        WarehouseOutboundLine.order_id == order.id,
    )).all()}
    already_packed = dict(db.execute(select(
        WarehousePackageLine.order_line_id, func.coalesce(func.sum(WarehousePackageLine.quantity), 0),
    ).join(WarehousePackage, WarehousePackage.id == WarehousePackageLine.package_id).where(
        WarehousePackageLine.organization_id == organization_id,
        WarehousePackage.order_id == order.id,
    ).group_by(WarehousePackageLine.order_line_id)).all())
    for line in payload.lines:
        outbound = outbound_lines.get(line.order_line_id)
        if outbound is None:
            raise HTTPException(404, "Outbound order line not found")
        if Decimal(already_packed.get(line.order_line_id, 0)) + line.quantity > outbound.quantity:
            raise HTTPException(409, "Package quantity exceeds the picked outbound quantity")
    package = WarehousePackage(
        organization_id=organization_id, order_id=order.id,
        package_number=f"PKG-{uuid4().hex[:12].upper()}",
        idempotency_key=payload.idempotency_key, request_hash=request_hash,
        created_by_user_id=principal.user_id,
    )
    db.add(package)
    db.flush()
    for line in payload.lines:
        db.add(WarehousePackageLine(organization_id=organization_id, order_id=order.id,
                                    package_id=package.id,
                                    order_line_id=line.order_line_id, quantity=line.quantity))
    db.flush()
    record_event(db, action="warehouse.package.create", target_type="warehouse_package",
                 organization_id=organization_id, actor_user_id=principal.user_id, target_id=package.id,
                 correlation_id=request.headers.get("X-Request-ID"),
                 details={"order_id": order.id, "line_count": len(payload.lines)})
    result = _package_out(db, package)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Package conflicts with an existing idempotency key") from exc
    return result


@router.get("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders/{order_id}/packages",
            response_model=dict)
def list_packages(organization_id: str, warehouse_id: str, order_id: str,
                  principal: Principal = Depends(require_permission("warehouse.packing.read")),
                  db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    order = _outbound_order(db, organization_id, warehouse_id, order_id)
    packages = db.scalars(select(WarehousePackage).where(
        WarehousePackage.organization_id == organization_id,
        WarehousePackage.order_id == order.id,
    ).order_by(WarehousePackage.created_at, WarehousePackage.id)).all()
    return {"items": [_package_out(db, package).model_dump() for package in packages]}


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders/{order_id}/packages/{package_id}/seal",
             response_model=WarehousePackageOut)
def seal_package(organization_id: str, warehouse_id: str, order_id: str, package_id: str,
                 request: Request,
                 principal: Principal = Depends(require_permission("warehouse.packing.write")),
                 db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    order = _outbound_order(db, organization_id, warehouse_id, order_id, lock=True)
    package = db.scalar(select(WarehousePackage).where(
        WarehousePackage.organization_id == organization_id,
        WarehousePackage.order_id == order.id,
        WarehousePackage.id == package_id,
    ).with_for_update())
    if package is None:
        raise HTTPException(404, "Package not found")
    if package.status == "sealed":
        return _package_out(db, package)
    package.status = "sealed"
    package.sealed_by_user_id = principal.user_id
    package.sealed_at = utc_now()
    record_event(db, action="warehouse.package.seal", target_type="warehouse_package",
                 organization_id=organization_id, actor_user_id=principal.user_id, target_id=package.id,
                 correlation_id=request.headers.get("X-Request-ID"), details={"order_id": order.id})
    lines = db.scalars(select(WarehouseOutboundLine).where(
        WarehouseOutboundLine.organization_id == organization_id,
        WarehouseOutboundLine.order_id == order.id,
    )).all()
    packed = dict(db.execute(select(
        WarehousePackageLine.order_line_id, func.coalesce(func.sum(WarehousePackageLine.quantity), 0),
    ).join(WarehousePackage, WarehousePackage.id == WarehousePackageLine.package_id).where(
        WarehousePackageLine.organization_id == organization_id,
        WarehousePackage.order_id == order.id,
        WarehousePackage.status == "sealed",
    ).group_by(WarehousePackageLine.order_line_id)).all())
    unsealed = db.scalar(select(func.count()).select_from(WarehousePackage).where(
        WarehousePackage.organization_id == organization_id,
        WarehousePackage.order_id == order.id,
        WarehousePackage.status == "open",
    ))
    fully_packed = all(Decimal(packed.get(line.id, 0)) == line.quantity for line in lines)
    if fully_packed and not unsealed:
        order.status = "packed"
        order.packed_by_user_id = principal.user_id
        order.packed_at = utc_now()
        record_event(db, action="warehouse.outbound.pack", target_type="warehouse_outbound_order",
                     organization_id=organization_id, actor_user_id=principal.user_id, target_id=order.id,
                     correlation_id=request.headers.get("X-Request-ID"),
                     details={"package_count": db.scalar(select(func.count()).select_from(WarehousePackage).where(
                         WarehousePackage.organization_id == organization_id,
                         WarehousePackage.order_id == order.id))})
    result = _package_out(db, package)
    db.commit()
    return result


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders/{order_id}/dispatch",
             response_model=WarehouseOutboundOrderOut)
def dispatch_outbound_order(organization_id: str, warehouse_id: str, order_id: str,
                            request: Request,
                            principal: Principal = Depends(require_permission("warehouse.outbound.write")),
                            db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    order = _outbound_order(db, organization_id, warehouse_id, order_id, lock=True)
    if order.status == "dispatched":
        return _outbound_order_out(db, order)
    if order.status != "packed" or order.shipping_location_id is None:
        raise HTTPException(409, "Outbound order must be fully packed before dispatch")
    warehouse = _warehouse(db, organization_id, warehouse_id)
    shipping = _location(db, organization_id, warehouse_id, order.shipping_location_id)
    if warehouse.status != "active" or shipping.status != "active" or shipping.location_type != "shipping":
        raise HTTPException(409, "Warehouse and shipping location must remain active to dispatch")
    lines = db.scalars(select(WarehouseOutboundLine).where(
        WarehouseOutboundLine.organization_id == organization_id,
        WarehouseOutboundLine.order_id == order.id,
    ).order_by(WarehouseOutboundLine.id)).all()
    try:
        for line in lines:
            post_warehouse_dispatch_movement(
                db, organization_id, principal.user_id, product_id=line.product_id,
                quantity=line.quantity, location_id=shipping.id,
                operation_key=f"warehouse-outbound:{order.id}:{line.id}:dispatch",
                lot_code=line.lot_code, serial_code=line.serial_code, expires_at=line.expires_at,
                note=f"Dispatch {order.order_number}",
                correlation_id=request.headers.get("X-Request-ID"),
            )
        order.status = "dispatched"
        order.dispatched_by_user_id = principal.user_id
        order.dispatched_at = utc_now()
        record_event(db, action="warehouse.outbound.dispatch", target_type="warehouse_outbound_order",
                     organization_id=organization_id, actor_user_id=principal.user_id, target_id=order.id,
                     correlation_id=request.headers.get("X-Request-ID"),
                     details={"line_count": len(lines), "shipping_location_id": shipping.id})
        result = _outbound_order_out(db, order)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Dispatch conflicts with a previous stock update") from exc
    except HTTPException:
        db.rollback()
        raise
    return result


@router.post("/organizations/{organization_id}/warehouses/{warehouse_id}/outbound-orders/{order_id}/cancel",
             response_model=WarehouseOutboundOrderOut)
def cancel_outbound_order(organization_id: str, warehouse_id: str, order_id: str, request: Request,
                         principal: Principal = Depends(require_permission("warehouse.outbound.write")),
                         db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    order = _outbound_order(db, organization_id, warehouse_id, order_id, lock=True)
    if order.status == "cancelled":
        return _outbound_order_out(db, order)
    if order.status not in {"draft", "reserved"}:
        raise HTTPException(409, "Only draft or reserved outbound orders can be cancelled")
    lines = db.scalars(select(WarehouseOutboundLine).where(
        WarehouseOutboundLine.organization_id == organization_id,
        WarehouseOutboundLine.order_id == order.id,
    ).order_by(WarehouseOutboundLine.id)).all()
    try:
        if order.status == "reserved":
            for line in lines:
                release_warehouse_pick_reservation(
                    db, organization_id, principal.user_id, product_id=line.product_id,
                    quantity=line.quantity, location_id=line.source_location_id,
                    operation_key=f"warehouse-outbound:{order.id}:{line.id}:cancel",
                    lot_code=line.lot_code, serial_code=line.serial_code, expires_at=line.expires_at,
                    note=f"Cancel outbound {order.order_number}",
                    correlation_id=request.headers.get("X-Request-ID"),
                )
        order.status = "cancelled"
        order.cancelled_by_user_id = principal.user_id
        order.cancelled_at = utc_now()
        record_event(db, action="warehouse.outbound.cancel", target_type="warehouse_outbound_order",
                     organization_id=organization_id, actor_user_id=principal.user_id, target_id=order.id,
                     correlation_id=request.headers.get("X-Request-ID"), details={"prior_status": "draft or reserved"})
        result = _outbound_order_out(db, order)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Outbound cancellation conflicts with a previous stock update") from exc
    except HTTPException:
        db.rollback()
        raise
    return result
