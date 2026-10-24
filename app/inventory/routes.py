"""Versioned inventory master-data and stock-ledger HTTP endpoints."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, require_permission
from app.identity.security import utc_now
from app.inventory.models import (InventoryCategory, InventoryCount, InventoryCountLine,
                                  InventoryMovement, InventoryProduct, InventoryStockBalance,
                                  InventoryUnit)
from app.inventory.schemas import (BalanceOut, CategoryCreate, CategoryOut, MovementCreate,
                                  InventoryCountCreate, InventoryCountLineOut, InventoryCountOut,
                                  MovementOut, ProductCreate, ProductOut, ProductPatch, UnitCreate,
                                  UnitOut)
from app.inventory.service import post_movement

router = APIRouter(tags=["Inventory"])


def _scope(principal: Principal, organization_id: str) -> None:
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")


def _product_out(db: Session, product: InventoryProduct) -> ProductOut:
    unit = db.get(InventoryUnit, product.unit_id)
    return ProductOut(
        id=product.id, organization_id=product.organization_id, sku=product.sku,
        name=product.name, description=product.description, category_id=product.category_id,
        unit_id=product.unit_id, unit_code=unit.code if unit else "", unit_name=unit.name if unit else "",
        barcode=product.barcode, tracking_mode=product.tracking_mode,
        cost_currency=product.cost_currency, average_cost=str(product.average_cost),
        archived_at=product.archived_at, created_at=product.created_at, updated_at=product.updated_at,
    )


@router.get("/organizations/{organization_id}/inventory/categories", response_model=dict)
def list_categories(organization_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                    principal: Principal = Depends(require_permission("inventory.products.read")),
                    db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    query = select(InventoryCategory).where(
        InventoryCategory.organization_id == organization_id,
        InventoryCategory.archived_at.is_(None),
    ).order_by(InventoryCategory.name, InventoryCategory.id)
    items = db.scalars(query.offset(offset).limit(limit)).all()
    return {"items": [CategoryOut.model_validate(item).model_dump() for item in items], "limit": limit, "offset": offset}


@router.post("/organizations/{organization_id}/inventory/categories", response_model=CategoryOut, status_code=201)
def create_category(organization_id: str, payload: CategoryCreate, request: Request,
                    principal: Principal = Depends(require_permission("inventory.products.write")),
                    db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    category = InventoryCategory(organization_id=organization_id, code=payload.code.strip().upper(), name=payload.name.strip())
    db.add(category)
    try:
        db.flush()
        record_event(db, action="inventory.category.create", target_type="inventory_category",
                     organization_id=organization_id, actor_user_id=principal.user_id, target_id=category.id,
                     correlation_id=request.headers.get("X-Request-ID"))
        result = CategoryOut.model_validate(category)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Category code already exists") from exc
    return result


@router.get("/organizations/{organization_id}/inventory/units", response_model=dict)
def list_units(organization_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
               principal: Principal = Depends(require_permission("inventory.products.read")),
               db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    items = db.scalars(select(InventoryUnit).where(
        InventoryUnit.organization_id == organization_id, InventoryUnit.archived_at.is_(None)
    ).order_by(InventoryUnit.name, InventoryUnit.id).offset(offset).limit(limit)).all()
    return {"items": [UnitOut.model_validate(item).model_dump() for item in items], "limit": limit, "offset": offset}


@router.post("/organizations/{organization_id}/inventory/units", response_model=UnitOut, status_code=201)
def create_unit(organization_id: str, payload: UnitCreate, request: Request,
                principal: Principal = Depends(require_permission("inventory.products.write")),
                db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    unit = InventoryUnit(organization_id=organization_id, code=payload.code.strip().upper(),
                         name=payload.name.strip(), decimal_places=payload.decimal_places)
    db.add(unit)
    try:
        db.flush()
        record_event(db, action="inventory.unit.create", target_type="inventory_unit",
                     organization_id=organization_id, actor_user_id=principal.user_id, target_id=unit.id,
                     correlation_id=request.headers.get("X-Request-ID"))
        result = UnitOut.model_validate(unit)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Unit code already exists") from exc
    return result


@router.get("/organizations/{organization_id}/inventory/products", response_model=dict)
def list_products(organization_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                  search: str | None = Query(None, max_length=120), include_archived: bool = False,
                  principal: Principal = Depends(require_permission("inventory.products.read")),
                  db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    query = select(InventoryProduct).where(InventoryProduct.organization_id == organization_id)
    if not include_archived:
        query = query.where(InventoryProduct.archived_at.is_(None))
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(InventoryProduct.sku.ilike(term), InventoryProduct.name.ilike(term),
                                InventoryProduct.barcode.ilike(term)))
    items = db.scalars(query.order_by(InventoryProduct.name, InventoryProduct.id).offset(offset).limit(limit)).all()
    return {"items": [_product_out(db, item).model_dump() for item in items], "limit": limit, "offset": offset}


@router.post("/organizations/{organization_id}/inventory/products", response_model=ProductOut, status_code=201)
def create_product(organization_id: str, payload: ProductCreate, request: Request,
                   principal: Principal = Depends(require_permission("inventory.products.write")),
                   db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    unit = db.scalar(select(InventoryUnit).where(InventoryUnit.organization_id == organization_id,
                                                 InventoryUnit.id == payload.unit_id,
                                                 InventoryUnit.archived_at.is_(None)))
    if unit is None:
        raise HTTPException(422, "A valid active unit of measure is required")
    if payload.category_id:
        category = db.scalar(select(InventoryCategory).where(
            InventoryCategory.organization_id == organization_id, InventoryCategory.id == payload.category_id,
            InventoryCategory.archived_at.is_(None)))
        if category is None:
            raise HTTPException(422, "Category is not available in this organisation")
    product = InventoryProduct(
        organization_id=organization_id, sku=payload.sku.strip().upper(), name=payload.name.strip(),
        description=payload.description.strip(), category_id=payload.category_id, unit_id=unit.id,
        barcode=payload.barcode.strip() if payload.barcode else None,
        tracking_mode=payload.tracking_mode, cost_currency=payload.cost_currency.upper(),
    )
    db.add(product)
    try:
        db.flush()
        db.add(InventoryStockBalance(organization_id=organization_id, product_id=product.id))
        record_event(db, action="inventory.product.create", target_type="inventory_product",
                     organization_id=organization_id, actor_user_id=principal.user_id, target_id=product.id,
                     correlation_id=request.headers.get("X-Request-ID"))
        result = _product_out(db, product)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "SKU or barcode already exists") from exc
    return result


@router.patch("/organizations/{organization_id}/inventory/products/{product_id}", response_model=ProductOut)
def update_product(organization_id: str, product_id: str, payload: ProductPatch, request: Request,
                   principal: Principal = Depends(require_permission("inventory.products.write")),
                   db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    product = db.scalar(select(InventoryProduct).where(
        InventoryProduct.organization_id == organization_id, InventoryProduct.id == product_id,
        InventoryProduct.archived_at.is_(None)))
    if product is None:
        raise HTTPException(404, "Product not found")
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes and changes["category_id"]:
        category = db.scalar(select(InventoryCategory).where(
            InventoryCategory.organization_id == organization_id,
            InventoryCategory.id == changes["category_id"], InventoryCategory.archived_at.is_(None)))
        if category is None:
            raise HTTPException(422, "Category is not available in this organisation")
    for key, value in changes.items():
        setattr(product, key, value.strip() if isinstance(value, str) else value)
    record_event(db, action="inventory.product.update", target_type="inventory_product",
                 organization_id=organization_id, actor_user_id=principal.user_id, target_id=product.id,
                 correlation_id=request.headers.get("X-Request-ID"))
    result = _product_out(db, product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Barcode already belongs to another product") from exc
    return result


@router.post("/organizations/{organization_id}/inventory/products/{product_id}/archive", status_code=204)
def archive_product(organization_id: str, product_id: str, request: Request,
                    principal: Principal = Depends(require_permission("inventory.products.write")),
                    db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    product = db.scalar(select(InventoryProduct).where(
        InventoryProduct.organization_id == organization_id, InventoryProduct.id == product_id,
        InventoryProduct.archived_at.is_(None)))
    if product is None:
        raise HTTPException(404, "Product not found")
    balance = db.scalar(select(InventoryStockBalance).where(
        InventoryStockBalance.organization_id == organization_id,
        InventoryStockBalance.product_id == product.id))
    if balance and (balance.on_hand != 0 or balance.reserved != 0):
        raise HTTPException(409, "A product with stock or reservations cannot be archived")
    product.archived_at = utc_now()
    record_event(db, action="inventory.product.archive", target_type="inventory_product",
                 organization_id=organization_id, actor_user_id=principal.user_id, target_id=product.id,
                 correlation_id=request.headers.get("X-Request-ID"))
    db.commit()
    return None


@router.post("/organizations/{organization_id}/inventory/movements", response_model=MovementOut)
def create_movement(organization_id: str, payload: MovementCreate, request: Request,
                    principal: Principal = Depends(require_permission("inventory.stock.write")),
                    db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    if payload.movement_type == "count":
        raise HTTPException(409, "Stock counts must be submitted and approved through the inventory count workflow")
    try:
        movement, _created = post_movement(db, organization_id, principal.user_id, payload,
                                           request.headers.get("X-Request-ID"))
        result = MovementOut.model_validate(movement)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Movement conflicts with a previous stock update") from exc
    return result


@router.get("/organizations/{organization_id}/inventory/movements", response_model=dict)
def list_movements(organization_id: str, product_id: str | None = None,
                   limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                   principal: Principal = Depends(require_permission("inventory.stock.read")),
                   db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    query = select(InventoryMovement).where(InventoryMovement.organization_id == organization_id)
    if product_id:
        query = query.where(InventoryMovement.product_id == product_id)
    items = db.scalars(query.order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc())
                       .offset(offset).limit(limit)).all()
    return {"items": [MovementOut.model_validate(item).model_dump() for item in items], "limit": limit, "offset": offset}


@router.get("/organizations/{organization_id}/inventory/balances", response_model=dict)
def list_balances(organization_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                  principal: Principal = Depends(require_permission("inventory.stock.read")),
                  db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    rows = db.execute(select(InventoryStockBalance, InventoryProduct, InventoryUnit)
        .join(InventoryProduct, (InventoryProduct.organization_id == InventoryStockBalance.organization_id)
              & (InventoryProduct.id == InventoryStockBalance.product_id))
        .join(InventoryUnit, (InventoryUnit.organization_id == InventoryProduct.organization_id)
              & (InventoryUnit.id == InventoryProduct.unit_id))
        .where(InventoryStockBalance.organization_id == organization_id,
               InventoryProduct.archived_at.is_(None))
        .order_by(InventoryProduct.name, InventoryProduct.id).offset(offset).limit(limit)).all()
    items = [BalanceOut(
        product_id=p.id, sku=p.sku, product_name=p.name, unit_code=u.code,
        on_hand=str(b.on_hand), reserved=str(b.reserved), available=str(b.on_hand - b.reserved),
        average_cost=str(p.average_cost), cost_currency=p.cost_currency, version=b.version,
    ).model_dump() for b, p, u in rows]
    return {"items": items, "limit": limit, "offset": offset}


def _count_out(db: Session, count: InventoryCount) -> InventoryCountOut:
    lines = db.scalars(select(InventoryCountLine).where(
        InventoryCountLine.organization_id == count.organization_id,
        InventoryCountLine.count_id == count.id,
    ).order_by(InventoryCountLine.product_id)).all()
    return InventoryCountOut(
        id=count.id, organization_id=count.organization_id, count_number=count.count_number,
        count_type=count.count_type, status=count.status, note=count.note,
        created_by_user_id=count.created_by_user_id,
        submitted_by_user_id=count.submitted_by_user_id,
        approved_by_user_id=count.approved_by_user_id,
        created_at=count.created_at, submitted_at=count.submitted_at,
        approved_at=count.approved_at,
        lines=[InventoryCountLineOut(
            id=line.id, product_id=line.product_id, expected_on_hand=line.expected_on_hand,
            counted_quantity=line.counted_quantity,
            variance=line.counted_quantity - line.expected_on_hand,
            balance_version=line.balance_version, reason_code=line.reason_code,
            reason_note=line.reason_note,
        ) for line in lines],
    )


@router.get("/organizations/{organization_id}/inventory/counts", response_model=dict)
def list_counts(organization_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                principal: Principal = Depends(require_permission("inventory.counts.read")),
                db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    counts = db.scalars(select(InventoryCount).where(
        InventoryCount.organization_id == organization_id,
    ).order_by(InventoryCount.created_at.desc(), InventoryCount.id.desc())
        .offset(offset).limit(limit)).all()
    return {"items": [_count_out(db, count).model_dump() for count in counts],
            "limit": limit, "offset": offset}


@router.post("/organizations/{organization_id}/inventory/counts", response_model=InventoryCountOut, status_code=201)
def create_count(organization_id: str, payload: InventoryCountCreate, request: Request,
                 principal: Principal = Depends(require_permission("inventory.counts.write")),
                 db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    products = db.scalars(select(InventoryProduct).where(
        InventoryProduct.organization_id == organization_id,
        InventoryProduct.id.in_([line.product_id for line in payload.lines]),
        InventoryProduct.archived_at.is_(None),
    )).all()
    product_by_id = {product.id: product for product in products}
    if len(product_by_id) != len(payload.lines):
        raise HTTPException(422, "Every counted product must be active in this organisation")
    if any(product.tracking_mode != "none" for product in products):
        raise HTTPException(422, "Lot- and serial-tracked products need a trace-specific count")

    if payload.count_type == "full_stocktake":
        all_products = db.scalars(select(InventoryProduct).where(
            InventoryProduct.organization_id == organization_id,
            InventoryProduct.archived_at.is_(None),
        )).all()
        if any(product.tracking_mode != "none" for product in all_products):
            raise HTTPException(422, "A full stocktake must include trace-specific counts for tracked products")
        if {product.id for product in all_products} != set(product_by_id):
            raise HTTPException(422, "A full stocktake must include every active product")

    product_ids = sorted(product_by_id)
    balances = db.scalars(select(InventoryStockBalance).where(
        InventoryStockBalance.organization_id == organization_id,
        InventoryStockBalance.product_id.in_(product_ids),
    ).order_by(InventoryStockBalance.product_id)).all()
    balance_by_product = {balance.product_id: balance for balance in balances}
    if len(balance_by_product) != len(product_by_id):
        raise HTTPException(409, "A product stock balance is not initialized")
    units = {unit.id: unit for unit in db.scalars(select(InventoryUnit).where(
        InventoryUnit.organization_id == organization_id,
        InventoryUnit.id.in_([product.unit_id for product in products]),
    )).all()}

    count_id = str(uuid4())
    count = InventoryCount(
        id=count_id, organization_id=organization_id,
        count_number=f"IC-{uuid4().hex[:12].upper()}", count_type=payload.count_type,
        status="draft", note=payload.note.strip(), created_by_user_id=principal.user_id,
    )
    db.add(count)
    for submitted_line in payload.lines:
        product = product_by_id[submitted_line.product_id]
        unit = units.get(product.unit_id)
        if unit is None:
            raise HTTPException(409, "A product unit of measure is unavailable")
        quantum = Decimal("1").scaleb(-unit.decimal_places)
        if submitted_line.counted_quantity.quantize(quantum) != submitted_line.counted_quantity:
            raise HTTPException(422, f"This unit allows up to {unit.decimal_places} decimal places")
        balance = balance_by_product[product.id]
        has_variance = submitted_line.counted_quantity != balance.on_hand
        if has_variance == (submitted_line.reason_code == "no_variance"):
            raise HTTPException(422, "Provide a variance reason only when the counted quantity differs")
        db.add(InventoryCountLine(
            organization_id=organization_id, count_id=count.id, product_id=product.id,
            expected_on_hand=balance.on_hand, counted_quantity=submitted_line.counted_quantity,
            balance_version=balance.version, reason_code=submitted_line.reason_code,
            reason_note=submitted_line.reason_note,
        ))
    db.flush()
    record_event(db, action="inventory.count.create", target_type="inventory_count",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=count.id, correlation_id=request.headers.get("X-Request-ID"),
                 details={"count_number": count.count_number, "count_type": count.count_type,
                          "line_count": len(payload.lines)})
    db.commit()
    return _count_out(db, count)


@router.post("/organizations/{organization_id}/inventory/counts/{count_id}/submit", response_model=InventoryCountOut)
def submit_count(organization_id: str, count_id: str, request: Request,
                 principal: Principal = Depends(require_permission("inventory.counts.write")),
                 db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    count = db.scalar(select(InventoryCount).where(
        InventoryCount.organization_id == organization_id, InventoryCount.id == count_id,
    ).with_for_update())
    if count is None:
        raise HTTPException(404, "Count not found")
    if count.status != "draft":
        raise HTTPException(409, "Only a draft count can be submitted")
    count.status = "submitted"
    count.submitted_by_user_id = principal.user_id
    count.submitted_at = utc_now()
    record_event(db, action="inventory.count.submit", target_type="inventory_count",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=count.id, correlation_id=request.headers.get("X-Request-ID"))
    db.flush()
    result = _count_out(db, count)
    db.commit()
    return result


@router.post("/organizations/{organization_id}/inventory/counts/{count_id}/approve", response_model=InventoryCountOut)
def approve_count(organization_id: str, count_id: str, request: Request,
                  principal: Principal = Depends(require_permission("inventory.counts.approve")),
                  db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    count = db.scalar(select(InventoryCount).where(
        InventoryCount.organization_id == organization_id, InventoryCount.id == count_id,
    ).with_for_update())
    if count is None:
        raise HTTPException(404, "Count not found")
    if count.status != "submitted":
        raise HTTPException(409, "Only a submitted count can be approved")
    if count.created_by_user_id == principal.user_id:
        raise HTTPException(403, "The count creator cannot approve their own count")
    lines = db.scalars(select(InventoryCountLine).where(
        InventoryCountLine.organization_id == organization_id,
        InventoryCountLine.count_id == count.id,
    ).order_by(InventoryCountLine.product_id)).all()
    balances = db.scalars(select(InventoryStockBalance).where(
        InventoryStockBalance.organization_id == organization_id,
        InventoryStockBalance.product_id.in_([line.product_id for line in lines]),
    ).order_by(InventoryStockBalance.product_id).with_for_update()).all()
    balance_by_product = {balance.product_id: balance for balance in balances}
    for line in lines:
        balance = balance_by_product.get(line.product_id)
        if balance is None or balance.version != line.balance_version:
            raise HTTPException(409, "Stock changed after this count was recorded; create a new count")
    for line in lines:
        reason = line.reason_code if line.reason_code != "no_variance" else "no variance"
        note = f"Count {count.count_number}: {reason} {line.reason_note}".strip()
        movement = MovementCreate(
            product_id=line.product_id, movement_type="count",
            quantity=line.counted_quantity,
            idempotency_key=f"count:{count.id}:{line.id}", note=note[:500],
        )
        post_movement(db, organization_id, principal.user_id, movement,
                      request.headers.get("X-Request-ID"))
    count.status = "approved"
    count.approved_by_user_id = principal.user_id
    count.approved_at = utc_now()
    record_event(db, action="inventory.count.approve", target_type="inventory_count",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=count.id, correlation_id=request.headers.get("X-Request-ID"),
                 details={"count_number": count.count_number, "line_count": len(lines)})
    db.flush()
    result = _count_out(db, count)
    db.commit()
    return result


@router.post("/organizations/{organization_id}/inventory/counts/{count_id}/reject", response_model=InventoryCountOut)
def reject_count(organization_id: str, count_id: str, request: Request,
                 principal: Principal = Depends(require_permission("inventory.counts.approve")),
                 db: Session = Depends(get_identity_session)):
    _scope(principal, organization_id)
    count = db.scalar(select(InventoryCount).where(
        InventoryCount.organization_id == organization_id, InventoryCount.id == count_id,
    ).with_for_update())
    if count is None:
        raise HTTPException(404, "Count not found")
    if count.status != "submitted":
        raise HTTPException(409, "Only a submitted count can be rejected")
    if count.created_by_user_id == principal.user_id:
        raise HTTPException(403, "The count creator cannot reject their own count")
    count.status = "rejected"
    record_event(db, action="inventory.count.reject", target_type="inventory_count",
                 organization_id=organization_id, actor_user_id=principal.user_id,
                 target_id=count.id, correlation_id=request.headers.get("X-Request-ID"))
    db.flush()
    result = _count_out(db, count)
    db.commit()
    return result
