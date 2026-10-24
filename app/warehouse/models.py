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


class WarehousePutawayTask(Base):
    """Move one fully received line from the receiving bay to an assigned location."""
    __tablename__ = "warehouse_putaway_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False)
    receipt_id: Mapped[str] = mapped_column(String(36), nullable=False)
    receipt_line_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_location_id: Mapped[str] = mapped_column(String(36), nullable=False)
    destination_location_id: Mapped[str | None] = mapped_column(String(36))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    lot_code: Mapped[str | None] = mapped_column(String(100))
    serial_code: Mapped[str | None] = mapped_column(String(100))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")
    assigned_by_user_id: Mapped[str | None] = mapped_column(String(36))
    completed_by_user_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_putaway_task_org_id"),
        UniqueConstraint("organization_id", "receipt_line_id", name="uq_warehouse_putaway_task_line"),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_task_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "receipt_id"], ["warehouse_receipts.organization_id", "warehouse_receipts.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_task_receipt_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "receipt_line_id"],
            ["warehouse_receipt_lines.organization_id", "warehouse_receipt_lines.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_task_line_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "source_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_source_same_warehouse",
        ),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "destination_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_putaway_destination_same_warehouse",
        ),
        CheckConstraint("quantity > 0", name="ck_warehouse_putaway_quantity_positive"),
        CheckConstraint("status IN ('pending','assigned','completed')", name="ck_warehouse_putaway_status"),
        CheckConstraint("lot_code IS NULL OR serial_code IS NULL", name="ck_warehouse_putaway_trace_unambiguous"),
        CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL", name="ck_warehouse_putaway_expiry_requires_lot"),
        CheckConstraint(
            "(status = 'pending' AND destination_location_id IS NULL) OR "
            "(status IN ('assigned','completed') AND destination_location_id IS NOT NULL)",
            name="ck_warehouse_putaway_assignment_shape",
        ),
        CheckConstraint("destination_location_id IS NULL OR destination_location_id != source_location_id",
                        name="ck_warehouse_putaway_distinct_locations"),
        Index("ix_warehouse_putaway_org_status_created", "organization_id", "status", "created_at"),
    )


class WarehouseTransfer(Base):
    """Two-step stock transfer with a visible in-transit staging location."""
    __tablename__ = "warehouse_transfers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    transfer_number: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_location_id: Mapped[str] = mapped_column(String(36), nullable=False)
    destination_warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False)
    destination_location_id: Mapped[str] = mapped_column(String(36), nullable=False)
    in_transit_location_id: Mapped[str | None] = mapped_column(String(36))
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    lot_code: Mapped[str | None] = mapped_column(String(100))
    serial_code: Mapped[str | None] = mapped_column(String(100))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_reference: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="draft")
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dispatched_by_user_id: Mapped[str | None] = mapped_column(String(36))
    received_by_user_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_transfer_org_id"),
        UniqueConstraint("organization_id", "transfer_number", name="uq_warehouse_transfer_org_number"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_transfer_org_key"),
        ForeignKeyConstraint(
            ["organization_id", "source_warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_source_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_warehouse_id", "source_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_source_location_same_warehouse",
        ),
        ForeignKeyConstraint(
            ["organization_id", "destination_warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_destination_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "destination_warehouse_id", "destination_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_destination_location_same_warehouse",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_warehouse_id", "in_transit_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_transfer_transit_location_same_warehouse",
        ),
        CheckConstraint("quantity > 0", name="ck_warehouse_transfer_quantity_positive"),
        CheckConstraint("status IN ('draft','in_transit','received')", name="ck_warehouse_transfer_status"),
        CheckConstraint("source_location_id != destination_location_id", name="ck_warehouse_transfer_distinct_locations"),
        CheckConstraint("lot_code IS NULL OR serial_code IS NULL", name="ck_warehouse_transfer_trace_unambiguous"),
        CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL", name="ck_warehouse_transfer_expiry_requires_lot"),
        CheckConstraint(
            "(status = 'draft' AND in_transit_location_id IS NULL) OR "
            "(status IN ('in_transit','received') AND in_transit_location_id IS NOT NULL)",
            name="ck_warehouse_transfer_transit_shape",
        ),
        Index("ix_warehouse_transfer_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_warehouse_transfer_org_product", "organization_id", "product_id", "created_at"),
    )


class WarehouseReplenishmentTask(Base):
    """Move stock from a reserve location to an operational pick location."""
    __tablename__ = "warehouse_replenishment_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_location_id: Mapped[str] = mapped_column(String(36), nullable=False)
    destination_location_id: Mapped[str] = mapped_column(String(36), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    lot_code: Mapped[str | None] = mapped_column(String(100))
    serial_code: Mapped[str | None] = mapped_column(String(100))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    completed_by_user_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_replenishment_org_id"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_replenishment_org_key"),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_replenishment_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "source_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_replenishment_source_same_warehouse",
        ),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "destination_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_replenishment_destination_same_warehouse",
        ),
        CheckConstraint("quantity > 0", name="ck_warehouse_replenishment_quantity_positive"),
        CheckConstraint("status IN ('pending','completed')", name="ck_warehouse_replenishment_status"),
        CheckConstraint("source_location_id != destination_location_id",
                        name="ck_warehouse_replenishment_distinct_locations"),
        CheckConstraint("lot_code IS NULL OR serial_code IS NULL",
                        name="ck_warehouse_replenishment_trace_unambiguous"),
        CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL",
                        name="ck_warehouse_replenishment_expiry_requires_lot"),
        Index("ix_warehouse_replenishment_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_warehouse_replenishment_org_product", "organization_id", "product_id", "created_at"),
    )


class WarehouseOutboundOrder(Base):
    """Outbound fulfillment lifecycle from stock reservation through dispatch."""
    __tablename__ = "warehouse_outbound_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False)
    order_number: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(160))
    shipping_location_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reserved_by_user_id: Mapped[str | None] = mapped_column(String(36))
    picked_by_user_id: Mapped[str | None] = mapped_column(String(36))
    packed_by_user_id: Mapped[str | None] = mapped_column(String(36))
    dispatched_by_user_id: Mapped[str | None] = mapped_column(String(36))
    cancelled_by_user_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    picked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    packed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_outbound_order_org_id"),
        UniqueConstraint("organization_id", "warehouse_id", "id",
                         name="uq_warehouse_outbound_order_org_warehouse_id"),
        UniqueConstraint("organization_id", "order_number", name="uq_warehouse_outbound_order_org_number"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_outbound_order_org_key"),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id"], ["warehouses.organization_id", "warehouses.id"],
            ondelete="RESTRICT", name="fk_warehouse_outbound_order_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "shipping_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_outbound_order_shipping_same_warehouse",
        ),
        CheckConstraint("status IN ('draft','reserved','picked','packed','dispatched','cancelled')",
                        name="ck_warehouse_outbound_order_status"),
        CheckConstraint(
            "(status IN ('draft','reserved','cancelled') AND shipping_location_id IS NULL) OR "
            "(status IN ('picked','packed','dispatched') AND shipping_location_id IS NOT NULL)",
            name="ck_warehouse_outbound_order_shipping_shape",
        ),
        Index("ix_warehouse_outbound_order_org_status_created", "organization_id", "status", "created_at"),
    )


class WarehouseOutboundLine(Base):
    """One reserved stock line to pick from a specific warehouse location."""
    __tablename__ = "warehouse_outbound_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False)
    order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_location_id: Mapped[str] = mapped_column(String(36), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    lot_code: Mapped[str | None] = mapped_column(String(100))
    serial_code: Mapped[str | None] = mapped_column(String(100))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_outbound_line_org_id"),
        UniqueConstraint("organization_id", "order_id", "id", name="uq_warehouse_outbound_line_order_id"),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "order_id"],
            ["warehouse_outbound_orders.organization_id", "warehouse_outbound_orders.warehouse_id",
             "warehouse_outbound_orders.id"],
            ondelete="RESTRICT", name="fk_warehouse_outbound_line_order_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id", "source_location_id"],
            ["warehouse_locations.organization_id", "warehouse_locations.warehouse_id",
             "warehouse_locations.id"],
            ondelete="RESTRICT", name="fk_warehouse_outbound_line_location_same_org",
        ),
        CheckConstraint("quantity > 0", name="ck_warehouse_outbound_line_quantity_positive"),
        CheckConstraint("lot_code IS NULL OR serial_code IS NULL",
                        name="ck_warehouse_outbound_line_trace_unambiguous"),
        CheckConstraint("expires_at IS NULL OR lot_code IS NOT NULL",
                        name="ck_warehouse_outbound_line_expiry_requires_lot"),
        Index("ix_warehouse_outbound_line_org_order", "organization_id", "order_id"),
    )


class WarehousePackage(Base):
    """Package/container prepared for one outbound order."""
    __tablename__ = "warehouse_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    package_number: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="open")
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sealed_by_user_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_package_org_id"),
        UniqueConstraint("organization_id", "order_id", "id", name="uq_warehouse_package_order_id"),
        UniqueConstraint("organization_id", "package_number", name="uq_warehouse_package_org_number"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_warehouse_package_org_key"),
        ForeignKeyConstraint(
            ["organization_id", "order_id"],
            ["warehouse_outbound_orders.organization_id", "warehouse_outbound_orders.id"],
            ondelete="RESTRICT", name="fk_warehouse_package_order_same_org",
        ),
        CheckConstraint("status IN ('open','sealed')", name="ck_warehouse_package_status"),
        Index("ix_warehouse_package_org_order", "organization_id", "order_id"),
    )


class WarehousePackageLine(Base):
    """Quantity of an already-picked outbound line packed in a handling unit."""
    __tablename__ = "warehouse_package_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    package_id: Mapped[str] = mapped_column(String(36), nullable=False)
    order_line_id: Mapped[str] = mapped_column(String(36), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_warehouse_package_line_org_id"),
        UniqueConstraint("organization_id", "package_id", "order_line_id",
                         name="uq_warehouse_package_line_item"),
        ForeignKeyConstraint(
            ["organization_id", "order_id", "package_id"],
            ["warehouse_packages.organization_id", "warehouse_packages.order_id",
             "warehouse_packages.id"],
            ondelete="RESTRICT", name="fk_warehouse_package_line_package_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "order_id", "order_line_id"],
            ["warehouse_outbound_lines.organization_id", "warehouse_outbound_lines.order_id",
             "warehouse_outbound_lines.id"],
            ondelete="RESTRICT", name="fk_warehouse_package_line_order_line_same_org",
        ),
        CheckConstraint("quantity > 0", name="ck_warehouse_package_line_quantity_positive"),
        Index("ix_warehouse_package_line_org_order_line", "organization_id", "order_line_id"),
    )
