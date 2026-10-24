"""Transactional inventory posting rules shared by the HTTP adapter."""
import hashlib
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.identity.audit import record_event
from app.inventory.models import InventoryMovement, InventoryProduct, InventoryStockBalance, InventoryUnit
from app.inventory.schemas import MovementCreate, MovementReverse
from app.warehouse.contracts import validate_inventory_location

ZERO = Decimal("0")


def _same_request(existing: InventoryMovement, payload: MovementCreate) -> bool:
    digest = hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()
    return existing.request_hash == digest


def _tracked_quantity(db: Session, organization_id: str, product_id: str,
                      tracking_code: str, column: str) -> Decimal:
    field = InventoryMovement.lot_code if column == "lot" else InventoryMovement.serial_code
    value = db.scalar(select(func.coalesce(func.sum(InventoryMovement.quantity_delta), 0)).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.product_id == product_id,
        field == tracking_code,
    ))
    return Decimal(value or 0)


def tracked_on_hand(db: Session, organization_id: str, product_id: str,
                    lot_code: str | None, serial_code: str | None) -> Decimal:
    """Return on-hand for one trace code, or the product total when untracked."""
    if lot_code:
        return _tracked_quantity(db, organization_id, product_id, lot_code, "lot")
    if serial_code:
        return _tracked_quantity(db, organization_id, product_id, serial_code, "serial")
    return ZERO


def _location_totals(db: Session, organization_id: str, product_id: str,
                     location_id: str | None) -> tuple[Decimal, Decimal]:
    row = db.execute(select(
        func.coalesce(func.sum(InventoryMovement.quantity_delta), 0),
        func.coalesce(func.sum(InventoryMovement.reserved_delta), 0),
    ).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.product_id == product_id,
        (InventoryMovement.warehouse_location_id.is_(None) if location_id is None
         else InventoryMovement.warehouse_location_id == location_id),
    )).one()
    return Decimal(row[0] or 0), Decimal(row[1] or 0)


def _tracked_reserved(db: Session, organization_id: str, product_id: str,
                      tracking_code: str, column: str) -> Decimal:
    field = InventoryMovement.lot_code if column == "lot" else InventoryMovement.serial_code
    value = db.scalar(select(func.coalesce(func.sum(InventoryMovement.reserved_delta), 0)).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.product_id == product_id,
        field == tracking_code,
    ))
    return Decimal(value or 0)


def post_movement(db: Session, organization_id: str, actor_user_id: str,
                  payload: MovementCreate, correlation_id: str | None) -> tuple[InventoryMovement, bool]:
    """Apply one immutable movement; return (row, was_created). Caller commits the transaction."""
    prior = db.scalar(select(InventoryMovement).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.idempotency_key == payload.idempotency_key,
    ))
    if prior is not None:
        if not _same_request(prior, payload):
            raise HTTPException(409, "Idempotency key was already used for a different movement")
        return prior, False

    product = db.scalar(select(InventoryProduct).where(
        InventoryProduct.organization_id == organization_id,
        InventoryProduct.id == payload.product_id,
        InventoryProduct.archived_at.is_(None),
    ))
    if product is None:
        raise HTTPException(404, "Product not found")
    if product.kind == "family":
        raise HTTPException(409, "Product family records cannot carry stock; use a stockable SKU variant")
    if payload.movement_type == "count" and db.scalar(select(InventoryMovement.id).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.product_id == product.id,
        InventoryMovement.warehouse_location_id.is_not(None),
    ).limit(1)) is not None:
        raise HTTPException(409, "Location-scoped stock counts are required for products with located stock")
    if payload.warehouse_location_id is not None:
        validate_inventory_location(db, organization_id, payload.warehouse_location_id)
    unit = db.get(InventoryUnit, product.unit_id)
    if unit is None:
        raise HTTPException(409, "Product unit of measure is unavailable")
    quantum = Decimal("1").scaleb(-unit.decimal_places)
    if payload.quantity.quantize(quantum) != payload.quantity:
        raise HTTPException(422, f"This unit allows up to {unit.decimal_places} decimal places")
    if payload.unit_cost is not None and max(-payload.unit_cost.as_tuple().exponent, 0) > 6:
        raise HTTPException(422, "Unit cost allows up to six decimal places")

    # Product creation seeds this row. Locking it serializes stock mutations for this SKU.
    balance = db.scalar(select(InventoryStockBalance).where(
        InventoryStockBalance.organization_id == organization_id,
        InventoryStockBalance.product_id == product.id,
    ).with_for_update())
    if balance is None:
        raise HTTPException(409, "Stock balance is not initialized")

    # Recheck after obtaining the per-product lock so duplicate concurrent requests replay once.
    prior = db.scalar(select(InventoryMovement).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.idempotency_key == payload.idempotency_key,
    ))
    if prior is not None:
        if not _same_request(prior, payload):
            raise HTTPException(409, "Idempotency key was already used for a different movement")
        return prior, False

    tracked_code = payload.lot_code if product.tracking_mode == "lot" else payload.serial_code
    tracked_kind = product.tracking_mode
    if tracked_kind == "lot" and not payload.lot_code:
        raise HTTPException(422, "Lot code is required for this product")
    if tracked_kind == "lot" and payload.serial_code:
        raise HTTPException(422, "Serial code is not valid for a lot-tracked product")
    if tracked_kind == "serial" and not payload.serial_code:
        raise HTTPException(422, "Serial code is required for this product")
    if tracked_kind == "serial" and (payload.lot_code or payload.expires_at):
        raise HTTPException(422, "Lot and expiry fields are not valid for a serial-tracked product")
    if tracked_kind == "none" and (payload.lot_code or payload.serial_code or payload.expires_at):
        raise HTTPException(422, "This product does not use lot or serial tracking")
    if payload.expires_at and not payload.lot_code:
        raise HTTPException(422, "Expiry date requires a lot code")
    if tracked_kind == "serial" and kind_not_count(payload.movement_type) and payload.quantity != Decimal("1"):
        raise HTTPException(422, "Serial-tracked movements must have a quantity of one")
    if tracked_kind == "serial" and payload.movement_type == "count" and payload.quantity not in {ZERO, Decimal("1")}:
        raise HTTPException(422, "A serial count must be zero or one")

    on_hand_delta = ZERO
    reserved_delta = ZERO
    kind = payload.movement_type
    if kind == "receipt":
        on_hand_delta = payload.quantity
    elif kind == "issue":
        on_hand_delta = -payload.quantity
    elif kind == "adjustment":
        on_hand_delta = payload.quantity if payload.direction == "increase" else -payload.quantity
    elif kind == "count":
        if tracked_kind in {"lot", "serial"} and tracked_code:
            current = _tracked_quantity(db, organization_id, product.id, tracked_code, tracked_kind)
            on_hand_delta = payload.quantity - current
        else:
            on_hand_delta = payload.quantity - balance.on_hand
    elif kind == "reserve":
        reserved_delta = payload.quantity
    elif kind == "release":
        reserved_delta = -payload.quantity

    if kind in {"issue", "adjustment", "count"} and on_hand_delta < 0:
        if balance.on_hand + on_hand_delta < balance.reserved:
            raise HTTPException(409, "Movement would make on-hand stock lower than reserved stock")
        if kind == "issue" and balance.on_hand - balance.reserved < payload.quantity:
            raise HTTPException(409, "Insufficient available stock")
        location_on_hand, location_reserved = _location_totals(
            db, organization_id, product.id, payload.warehouse_location_id,
        )
        if location_on_hand + on_hand_delta < location_reserved:
            raise HTTPException(409, "Movement would reduce location stock below its reservation")
        if kind == "issue" and location_on_hand - location_reserved < payload.quantity:
            raise HTTPException(409, "Insufficient available stock at this location")
        if tracked_kind in {"lot", "serial"} and tracked_code:
            tracked_on_hand = _tracked_quantity(db, organization_id, product.id, tracked_code, tracked_kind)
            tracked_reserved = _tracked_reserved(db, organization_id, product.id, tracked_code, tracked_kind)
            if kind == "issue" and tracked_on_hand - tracked_reserved < payload.quantity:
                raise HTTPException(409, "Insufficient available stock in this lot or serial")
            if tracked_on_hand + on_hand_delta < tracked_reserved:
                raise HTTPException(409, "Movement would reduce tracked stock below its reservation")
            if tracked_kind == "serial" and tracked_on_hand < 1:
                raise HTTPException(409, "Serial number is not currently in stock")
    if tracked_kind == "serial" and kind in {"receipt", "adjustment"} and on_hand_delta > 0:
        if _tracked_quantity(db, organization_id, product.id, tracked_code or "", "serial") > 0:
            raise HTTPException(409, "Serial number is already in stock")

    if kind == "reserve":
        if balance.on_hand - balance.reserved < payload.quantity:
            raise HTTPException(409, "Insufficient available stock to reserve")
        if tracked_kind in {"lot", "serial"} and tracked_code:
            tracked_on_hand = _tracked_quantity(db, organization_id, product.id, tracked_code, tracked_kind)
            tracked_reserved = _tracked_reserved(db, organization_id, product.id, tracked_code, tracked_kind)
            if tracked_on_hand - tracked_reserved < payload.quantity:
                raise HTTPException(409, "Insufficient tracked stock to reserve")
        location_on_hand, location_reserved = _location_totals(
            db, organization_id, product.id, payload.warehouse_location_id,
        )
        if location_on_hand - location_reserved < payload.quantity:
            raise HTTPException(409, "Insufficient available stock at this location to reserve")
    if kind == "release" and balance.reserved < payload.quantity:
        raise HTTPException(409, "Release quantity exceeds the reserved stock")
    if kind == "release":
        _location_on_hand, location_reserved = _location_totals(
            db, organization_id, product.id, payload.warehouse_location_id,
        )
        if location_reserved < payload.quantity:
            raise HTTPException(409, "Release quantity exceeds the reserved stock at this location")
    if kind == "release" and tracked_kind in {"lot", "serial"} and tracked_code:
        if _tracked_reserved(db, organization_id, product.id, tracked_code, tracked_kind) < payload.quantity:
            raise HTTPException(409, "Release quantity exceeds the tracked reservation")

    next_on_hand = balance.on_hand + on_hand_delta
    next_reserved = balance.reserved + reserved_delta
    if next_on_hand < 0 or next_reserved < 0 or next_reserved > next_on_hand:
        raise HTTPException(409, "Movement violates the non-negative stock policy")

    average_cost = Decimal(product.average_cost or 0)
    unit_cost = payload.unit_cost if kind == "receipt" else (average_cost if kind in {"issue", "adjustment", "count"} else None)
    if kind == "receipt" and payload.unit_cost is not None:
        if balance.on_hand <= 0:
            average_cost = payload.unit_cost
        else:
            average_cost = ((balance.on_hand * average_cost) + (payload.quantity * payload.unit_cost)) / next_on_hand
        product.average_cost = average_cost
    balance.on_hand = next_on_hand
    balance.reserved = next_reserved
    balance.version += 1

    movement = InventoryMovement(
        organization_id=organization_id,
        product_id=product.id,
        movement_type=kind,
        quantity_delta=on_hand_delta,
        reserved_delta=reserved_delta,
        unit_cost=unit_cost,
        currency_code=product.cost_currency,
        idempotency_key=payload.idempotency_key,
        request_hash=hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest(),
        lot_code=payload.lot_code,
        serial_code=payload.serial_code,
        expires_at=payload.expires_at,
        warehouse_location_id=payload.warehouse_location_id,
        note=payload.note.strip(),
        actor_user_id=actor_user_id,
    )
    db.add(movement)
    db.flush()
    record_event(
        db,
        action=f"inventory.stock.{kind}",
        target_type="inventory_product",
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_id=product.id,
        correlation_id=correlation_id,
        details={"movement_id": movement.id, "quantity_delta": str(on_hand_delta),
                 "reserved_delta": str(reserved_delta), "currency_code": product.cost_currency},
    )
    db.flush()
    return movement, True


def reverse_movement(db: Session, organization_id: str, actor_user_id: str,
                     movement_id: str, payload: MovementReverse,
                     correlation_id: str | None) -> tuple[InventoryMovement, bool]:
    """Append one compensating entry for a prior movement; never edits ledger history."""
    request_hash = hashlib.sha256(
        f"reverse:{movement_id}:{payload.idempotency_key}:{payload.note.strip()}".encode("utf-8")
    ).hexdigest()
    prior_request = db.scalar(select(InventoryMovement).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.idempotency_key == payload.idempotency_key,
    ))
    if prior_request is not None:
        if prior_request.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key was already used for a different movement")
        return prior_request, False

    source = db.scalar(select(InventoryMovement).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.id == movement_id,
    ).with_for_update())
    if source is None:
        raise HTTPException(404, "Movement not found")
    # A concurrent retry may have waited for the source row lock while the
    # first request committed. Re-read its idempotency key before checking the
    # one-reversal constraint so an exact retry returns the original row.
    prior_request = db.scalar(select(InventoryMovement).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.idempotency_key == payload.idempotency_key,
    ))
    if prior_request is not None:
        if prior_request.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key was already used for a different movement")
        return prior_request, False
    if source.movement_type == "reversal" or source.reversal_of_movement_id is not None:
        raise HTTPException(409, "A reversal cannot itself be reversed")
    if source.quantity_delta == 0 and source.reserved_delta == 0:
        raise HTTPException(409, "This movement has no stock effect to reverse")
    already_reversed = db.scalar(select(InventoryMovement.id).where(
        InventoryMovement.organization_id == organization_id,
        InventoryMovement.reversal_of_movement_id == source.id,
    ))
    if already_reversed is not None:
        raise HTTPException(409, "This movement has already been reversed")

    balance = db.scalar(select(InventoryStockBalance).where(
        InventoryStockBalance.organization_id == organization_id,
        InventoryStockBalance.product_id == source.product_id,
    ).with_for_update())
    if balance is None:
        raise HTTPException(409, "Stock balance is not initialized")
    delta = -source.quantity_delta
    reserved_delta = -source.reserved_delta
    location_on_hand, location_reserved = _location_totals(
        db, organization_id, source.product_id, source.warehouse_location_id,
    )
    location_next_on_hand = location_on_hand + delta
    location_next_reserved = location_reserved + reserved_delta
    if (location_next_on_hand < 0 or location_next_reserved < 0
            or location_next_reserved > location_next_on_hand):
        raise HTTPException(409, "Reversal would violate location on-hand or reserved stock")
    next_on_hand = balance.on_hand + delta
    next_reserved = balance.reserved + reserved_delta
    if next_on_hand < 0 or next_reserved < 0 or next_reserved > next_on_hand:
        raise HTTPException(409, "Reversal would violate on-hand or reserved stock")

    product = db.scalar(select(InventoryProduct).where(
        InventoryProduct.organization_id == organization_id,
        InventoryProduct.id == source.product_id,
    ))
    if product is None:
        raise HTTPException(409, "Movement product is unavailable")
    if product.tracking_mode in {"lot", "serial"} and (source.lot_code or source.serial_code):
        field = InventoryMovement.lot_code if product.tracking_mode == "lot" else InventoryMovement.serial_code
        tracking_code = source.lot_code if product.tracking_mode == "lot" else source.serial_code
        tracked_on_hand_now = _tracked_quantity(db, organization_id, product.id, tracking_code or "",
                                                product.tracking_mode)
        tracked_reserved_now = _tracked_reserved(db, organization_id, product.id, tracking_code or "",
                                                product.tracking_mode)
        tracked_next = tracked_on_hand_now + delta
        tracked_reserved_next = tracked_reserved_now + reserved_delta
        if tracked_next < 0 or tracked_reserved_next < 0 or tracked_reserved_next > tracked_next:
            raise HTTPException(409, "Reversal would violate tracked on-hand or reserved stock")
        if product.tracking_mode == "serial" and tracked_next not in {ZERO, Decimal("1")}:
            raise HTTPException(409, "Reversal would create an invalid serial quantity")

    average_cost = Decimal(product.average_cost or 0)
    if delta and source.unit_cost is not None and next_on_hand > 0:
        average_cost = ((balance.on_hand * average_cost) + (delta * source.unit_cost)) / next_on_hand
        if average_cost < 0:
            raise HTTPException(409, "Reversal would produce a negative inventory valuation")
        product.average_cost = average_cost
    balance.on_hand = next_on_hand
    balance.reserved = next_reserved
    balance.version += 1
    movement = InventoryMovement(
        organization_id=organization_id,
        product_id=source.product_id,
        movement_type="reversal",
        quantity_delta=delta,
        reserved_delta=reserved_delta,
        unit_cost=source.unit_cost,
        currency_code=source.currency_code,
        idempotency_key=payload.idempotency_key,
        request_hash=request_hash,
        lot_code=source.lot_code,
        serial_code=source.serial_code,
        expires_at=source.expires_at,
        warehouse_location_id=source.warehouse_location_id,
        note=payload.note.strip(),
        actor_user_id=actor_user_id,
        reversal_of_movement_id=source.id,
    )
    db.add(movement)
    db.flush()
    record_event(
        db,
        action="inventory.stock.reversal",
        target_type="inventory_product",
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_id=source.product_id,
        correlation_id=correlation_id,
        details={"movement_id": movement.id, "reversal_of_movement_id": source.id,
                 "quantity_delta": str(delta), "reserved_delta": str(reserved_delta),
                 "currency_code": source.currency_code},
    )
    db.flush()
    return movement, True


def kind_not_count(movement_type: str) -> bool:
    return movement_type != "count"

