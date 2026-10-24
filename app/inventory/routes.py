"""Versioned inventory master-data and stock-ledger HTTP endpoints."""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, require_permission
from app.identity.security import utc_now
from app.inventory.models import (InventoryCategory, InventoryMovement, InventoryProduct,
                                  InventoryStockBalance, InventoryUnit)
from app.inventory.schemas import (BalanceOut, CategoryCreate, CategoryOut, MovementCreate,
                                  MovementOut, ProductCreate, ProductOut, ProductPatch,
                                  UnitCreate, UnitOut)
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

