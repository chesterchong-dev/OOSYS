"""Published validation contract for Inventory references to warehouse locations."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.warehouse.models import Warehouse, WarehouseLocation


def validate_inventory_location(db: Session, organization_id: str, location_id: str) -> None:
    """Require an active operational location in an active warehouse.

    Inventory stores only the stable location ID. WMS remains responsible for
    the location hierarchy and its lifecycle rules.
    """
    row = db.execute(
        select(WarehouseLocation.id, WarehouseLocation.location_type).join(
            Warehouse,
            (Warehouse.organization_id == WarehouseLocation.organization_id)
            & (Warehouse.id == WarehouseLocation.warehouse_id),
        ).where(
            WarehouseLocation.organization_id == organization_id,
            WarehouseLocation.id == location_id,
            WarehouseLocation.status == "active",
            Warehouse.status == "active",
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "Active warehouse location not found")
    if row.location_type == "zone":
        raise HTTPException(409, "Stock must be assigned to an operational location, not a zone")


