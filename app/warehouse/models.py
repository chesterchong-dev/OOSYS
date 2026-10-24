"""Tenant-owned warehouse and physical-location records."""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
                        Index, Numeric, String, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base


def new_id() -> str:
    return str(uuid4())


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False,
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_org_id"),
        UniqueConstraint("organization_id", "code", name="uq_warehouse_org_code"),
        CheckConstraint("length(trim(code)) > 0", name="ck_warehouse_code_nonempty"),
        CheckConstraint("length(trim(name)) > 0", name="ck_warehouse_name_nonempty"),
        CheckConstraint("status IN ('active','inactive')", name="ck_warehouse_status"),
        Index("ix_warehouse_org_name", "organization_id", "name"),
    )


class WarehouseLocation(Base):
    """Zone and physical location hierarchy owned by one tenant warehouse."""
    __tablename__ = "warehouse_locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parent_location_id: Mapped[str | None] = mapped_column(String(36))
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    location_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="active")
    capacity_limit: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    capacity_unit: Mapped[str | None] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )


    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_location_org_id"),
        UniqueConstraint("organization_id", "warehouse_id", "id",
                         name="uq_warehouse_location_org_warehouse_id"),
        UniqueConstraint("organization_id", "warehouse_id", "code",
                         name="uq_warehouse_location_org_warehouse_code"),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id"],
            ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_location_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "parent_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_location_parent_same_warehouse",
        ),
        CheckConstraint("length(trim(code)) > 0", name="ck_warehouse_location_code_nonempty"),
        CheckConstraint("length(trim(name)) > 0", name="ck_warehouse_location_name_nonempty"),
        CheckConstraint(
            "location_type IN ('zone','bin','receiving','staging','shipping','quarantine','unassigned')",
            name="ck_warehouse_location_type",
        ),
        CheckConstraint("status IN ('active','blocked','inactive')", name="ck_warehouse_location_status"),
        CheckConstraint("parent_location_id IS NULL OR parent_location_id != id",
                        name="ck_warehouse_location_not_own_parent"),
        CheckConstraint(
            "(capacity_limit IS NULL AND capacity_unit IS NULL) OR "
            "(capacity_limit > 0 AND capacity_unit IS NOT NULL AND length(trim(capacity_unit)) > 0)",
            name="ck_warehouse_location_capacity_shape",
        ),
        Index("ix_warehouse_location_org_warehouse_parent", "organization_id", "warehouse_id",
              "parent_location_id"),
        Index("ix_warehouse_location_org_status", "organization_id", "status"),
    )


class WarehouseReceipt(Base):
    """Inbound receipt workflow; Inventory owns all resulting stock movements."""
    __tablename__ = "warehouse_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False)
    receiving_location_id: Mapped[str] = mapped_column(String(36), nullable=False)
    receipt_number: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="draft")
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    posted_by_user_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_receipt_org_id"),
        UniqueConstraint("organization_id", "receipt_number", name="uq_warehouse_receipt_org_number"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_receipt_org_key"),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_receipt_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "receiving_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_receipt_location_same_warehouse",
        ),
        CheckConstraint("status IN ('draft','posted')", name="ck_warehouse_receipt_status"),
        CheckConstraint("length(trim(receipt_number)) > 0", name="ck_warehouse_receipt_number_nonempty"),
        Index("ix_warehouse_receipt_org_status_created", "organization_id", "status", "created_at"),
    )


class WarehouseReceiptLine(Base):
    """Expected and accepted inbound quantities for one stockable item/trace."""
    __tablename__ = "warehouse_receipt_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    receipt_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    lot_code: Mapped[str | None] = mapped_column(String(100))
    serial_code: Mapped[str | None] = mapped_column(String(100))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_receipt_line_org_id"),
        ForeignKeyConstraint(
            ["organization_id", "receipt_id"], ["warehouse_receipts.organization_id", "warehouse_receipts.id"],
            ondelete="RESTRICT", name="fk_warehouse_receipt_line_receipt_same_org",
        ),
        CheckConstraint("quantity > 0", name="ck_warehouse_receipt_line_quantity_positive"),
        CheckConstraint("unit_cost IS NULL OR unit_cost >= 0", name="ck_warehouse_receipt_line_cost_nonnegative"),
        CheckConstraint("lot_code IS NULL OR serial_code IS NULL", name="ck_warehouse_receipt_line_trace_unambiguous"),
        CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL", name="ck_warehouse_receipt_line_expiry_requires_lot"),
        Index("ix_warehouse_receipt_line_org_receipt", "organization_id", "receipt_id"),
        Index("ix_warehouse_receipt_line_org_product", "organization_id", "product_id"),
    )

