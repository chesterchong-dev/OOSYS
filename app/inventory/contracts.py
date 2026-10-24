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


