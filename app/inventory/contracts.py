"""Application contracts for other domains that need Inventory stock postings."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.inventory.schemas import MovementCreate
from app.inventory.service import post_movement


def post_warehouse_receipt_movement(
    db: Session,
    organization_id: str,
    actor_user_id: str,
    *,
    product_id: str,
    quantity: Decimal,
    location_id: str,
    idempotency_key: str,
    unit_cost: Decimal | None = None,
    lot_code: str | None = None,
    serial_code: str | None = None,
    expires_at: datetime | None = None,
    note: str = "",
    correlation_id: str | None = None,
):
    """Post one receipt through Inventory's stock owner, inside the caller's transaction."""
    payload = MovementCreate(
        product_id=product_id,
        warehouse_location_id=location_id,
        movement_type="receipt",
        quantity=quantity,
        unit_cost=unit_cost,
        idempotency_key=idempotency_key,
        lot_code=lot_code,
        serial_code=serial_code,
        expires_at=expires_at,
        note=note,
    )
    return post_movement(db, organization_id, actor_user_id, payload, correlation_id)


def post_warehouse_putaway_transfer(
    db: Session,
    organization_id: str,
    actor_user_id: str,
    *,
    product_id: str,
    quantity: Decimal,
    source_location_id: str,
    destination_location_id: str,
    operation_key: str,
    lot_code: str | None = None,
    serial_code: str | None = None,
    expires_at: datetime | None = None,
    note: str = "",
    correlation_id: str | None = None,
):
    """Move stock between WMS locations with two ledger legs in one DB transaction."""
    outgoing, _ = post_movement(db, organization_id, actor_user_id, MovementCreate(
        product_id=product_id,
        warehouse_location_id=source_location_id,
        movement_type="issue",
        quantity=quantity,
        idempotency_key=f"{operation_key}:out",
        lot_code=lot_code,
        serial_code=serial_code,
        expires_at=expires_at,
        note=note,
    ), correlation_id)
    incoming, _ = post_movement(db, organization_id, actor_user_id, MovementCreate(
        product_id=product_id,
        warehouse_location_id=destination_location_id,
        movement_type="receipt",
        quantity=quantity,
        unit_cost=outgoing.unit_cost,
        idempotency_key=f"{operation_key}:in",
        lot_code=lot_code,
        serial_code=serial_code,
        expires_at=expires_at,
        note=note,
    ), correlation_id)
    return outgoing, incoming


def post_warehouse_pick_reservation(
    db: Session,
    organization_id: str,
    actor_user_id: str,
    *,
    product_id: str,
    quantity: Decimal,
    location_id: str,
    operation_key: str,
    lot_code: str | None = None,
    serial_code: str | None = None,
    expires_at: datetime | None = None,
    note: str = "",
    correlation_id: str | None = None,
):
    """Reserve one warehouse pick line through Inventory's availability checks."""
    return post_movement(db, organization_id, actor_user_id, MovementCreate(
        product_id=product_id,
        warehouse_location_id=location_id,
        movement_type="reserve",
        quantity=quantity,
        idempotency_key=f"{operation_key}:reserve",
        lot_code=lot_code,
        serial_code=serial_code,
        expires_at=expires_at,
        note=note,
    ), correlation_id)


def release_warehouse_pick_reservation(
    db: Session,
    organization_id: str,
    actor_user_id: str,
    *,
    product_id: str,
    quantity: Decimal,
    location_id: str,
    operation_key: str,
    lot_code: str | None = None,
    serial_code: str | None = None,
    expires_at: datetime | None = None,
    note: str = "",
    correlation_id: str | None = None,
):
    """Release a warehouse pick reservation through Inventory's stock owner."""
    return post_movement(db, organization_id, actor_user_id, MovementCreate(
        product_id=product_id,
        warehouse_location_id=location_id,
        movement_type="release",
        quantity=quantity,
        idempotency_key=f"{operation_key}:release",
        lot_code=lot_code,
        serial_code=serial_code,
        expires_at=expires_at,
        note=note,
    ), correlation_id)


def post_warehouse_pick(
    db: Session,
    organization_id: str,
    actor_user_id: str,
    *,
    product_id: str,
    quantity: Decimal,
    source_location_id: str,
    shipping_location_id: str,
    operation_key: str,
    lot_code: str | None = None,
    serial_code: str | None = None,
    expires_at: datetime | None = None,
    note: str = "",
    correlation_id: str | None = None,
):
    """Release a pick reservation and move stock to shipping staging atomically."""
    post_movement(db, organization_id, actor_user_id, MovementCreate(
        product_id=product_id,
        warehouse_location_id=source_location_id,
        movement_type="release",
        quantity=quantity,
        idempotency_key=f"{operation_key}:release",
        lot_code=lot_code,
        serial_code=serial_code,
        expires_at=expires_at,
        note=note,
    ), correlation_id)
    return post_warehouse_putaway_transfer(
        db, organization_id, actor_user_id,
        product_id=product_id,
        quantity=quantity,
        source_location_id=source_location_id,
        destination_location_id=shipping_location_id,
        operation_key=f"{operation_key}:move",
        lot_code=lot_code,
        serial_code=serial_code,
        expires_at=expires_at,
        note=note,
        correlation_id=correlation_id,
    )


def post_warehouse_dispatch_movement(
    db: Session,
    organization_id: str,
    actor_user_id: str,
    *,
    product_id: str,
    quantity: Decimal,
    location_id: str,
    operation_key: str,
    lot_code: str | None = None,
    serial_code: str | None = None,
    expires_at: datetime | None = None,
    note: str = "",
    correlation_id: str | None = None,
):
    """Issue packed goods at dispatch through Inventory's stock owner."""
    return post_movement(db, organization_id, actor_user_id, MovementCreate(
        product_id=product_id,
        warehouse_location_id=location_id,
        movement_type="issue",
        quantity=quantity,
        idempotency_key=f"{operation_key}:issue",
        lot_code=lot_code,
        serial_code=serial_code,
        expires_at=expires_at,
        note=note,
    ), correlation_id)

