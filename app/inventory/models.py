"""Tenant-owned inventory catalog and immutable stock ledger records."""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
                        Index, Numeric, String, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base


def new_id() -> str:
    return str(uuid4())


class InventoryCategory(Base):
    __tablename__ = "inventory_categories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_inventory_category_org_id"),
        UniqueConstraint("organization_id", "code", name="uq_inventory_category_org_code"),
        CheckConstraint("length(trim(code)) > 0", name="ck_inventory_category_code_nonempty"),
        CheckConstraint("length(trim(name)) > 0", name="ck_inventory_category_name_nonempty"),
        Index("ix_inventory_category_org_name", "organization_id", "name"),
    )


class InventoryUnit(Base):
    __tablename__ = "inventory_units"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    decimal_places: Mapped[int] = mapped_column(nullable=False, default=3)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_inventory_unit_org_id"),
        UniqueConstraint("organization_id", "code", name="uq_inventory_unit_org_code"),
        CheckConstraint("length(trim(code)) > 0", name="ck_inventory_unit_code_nonempty"),
        CheckConstraint("decimal_places BETWEEN 0 AND 6", name="ck_inventory_unit_decimal_places"),
        Index("ix_inventory_unit_org_name", "organization_id", "name"),
    )


class InventoryProduct(Base):
    __tablename__ = "inventory_products"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("identity_organizations.id", ondelete="RESTRICT"), nullable=False)
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    category_id: Mapped[str | None] = mapped_column(String(36))
    unit_id: Mapped[str] = mapped_column(String(36), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(120))
    tracking_mode: Mapped[str] = mapped_column(String(12), nullable=False, default="none")
    cost_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MYR")
    average_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_inventory_product_org_id"),
        UniqueConstraint("organization_id", "sku", name="uq_inventory_product_org_sku"),
        UniqueConstraint("organization_id", "barcode", name="uq_inventory_product_org_barcode"),
        ForeignKeyConstraint(["organization_id", "category_id"], ["inventory_categories.organization_id", "inventory_categories.id"], ondelete="RESTRICT", name="fk_inventory_product_category_same_org"),
        ForeignKeyConstraint(["organization_id", "unit_id"], ["inventory_units.organization_id", "inventory_units.id"], ondelete="RESTRICT", name="fk_inventory_product_unit_same_org"),
        CheckConstraint("length(trim(sku)) > 0", name="ck_inventory_product_sku_nonempty"),
        CheckConstraint("length(trim(name)) > 0", name="ck_inventory_product_name_nonempty"),
        CheckConstraint("tracking_mode IN ('none','lot','serial')", name="ck_inventory_product_tracking_mode"),
        CheckConstraint("cost_currency = upper(cost_currency)", name="ck_inventory_product_currency_upper"),
        CheckConstraint("length(cost_currency) = 3", name="ck_inventory_product_currency_length"),
        CheckConstraint("average_cost >= 0", name="ck_inventory_product_average_cost_nonnegative"),
        Index("ix_inventory_product_org_name", "organization_id", "name"),
        Index("ix_inventory_product_org_category", "organization_id", "category_id"),
    )


class InventoryStockBalance(Base):
    __tablename__ = "inventory_stock_balances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    on_hand: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    reserved: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    version: Mapped[int] = mapped_column(nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_inventory_balance_org_id"),
        UniqueConstraint("organization_id", "product_id", name="uq_inventory_balance_org_product"),
        ForeignKeyConstraint(["organization_id", "product_id"], ["inventory_products.organization_id", "inventory_products.id"], ondelete="RESTRICT", name="fk_inventory_balance_product_same_org"),
        CheckConstraint("on_hand >= 0", name="ck_inventory_balance_on_hand_nonnegative"),
        CheckConstraint("reserved >= 0 AND reserved <= on_hand", name="ck_inventory_balance_reserved_range"),
        Index("ix_inventory_balance_org_product", "organization_id", "product_id"),
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    reserved_delta: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lot_code: Mapped[str | None] = mapped_column(String(100))
    serial_code: Mapped[str | None] = mapped_column(String(100))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_inventory_movement_org_id"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_inventory_movement_org_idempotency"),
        ForeignKeyConstraint(["organization_id", "product_id"], ["inventory_products.organization_id", "inventory_products.id"], ondelete="RESTRICT", name="fk_inventory_movement_product_same_org"),
        CheckConstraint("movement_type IN ('receipt','issue','adjustment','count','reserve','release')", name="ck_inventory_movement_type"),
        CheckConstraint("quantity_delta != 0 OR reserved_delta != 0 OR movement_type = 'count'", name="ck_inventory_movement_nonzero"),
        CheckConstraint("reserved_delta >= 0 OR movement_type = 'release'", name="ck_inventory_movement_reserve_delta"),
        CheckConstraint("unit_cost IS NULL OR unit_cost >= 0", name="ck_inventory_movement_cost_nonnegative"),
        CheckConstraint("length(currency_code) = 3 AND currency_code = upper(currency_code)", name="ck_inventory_movement_currency"),
        Index("ix_inventory_movement_org_product_created", "organization_id", "product_id", "created_at"),
        Index("ix_inventory_movement_org_lot", "organization_id", "product_id", "lot_code"),
        Index("ix_inventory_movement_org_serial", "organization_id", "product_id", "serial_code"),
    )


class InventoryCount(Base):
    """A submitted count awaiting a separate authorized approval."""
    __tablename__ = "inventory_counts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    count_number: Mapped[str] = mapped_column(String(40), nullable=False)
    count_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    submitted_by_user_id: Mapped[str | None] = mapped_column(String(36))
    approved_by_user_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_inventory_count_org_id"),
        UniqueConstraint("organization_id", "count_number", name="uq_inventory_count_org_number"),
        CheckConstraint("count_type IN ('cycle','full_stocktake')", name="ck_inventory_count_type"),
        CheckConstraint("status IN ('draft','submitted','approved','rejected')", name="ck_inventory_count_status"),
        Index("ix_inventory_count_org_status_created", "organization_id", "status", "created_at"),
    )


class InventoryCountLine(Base):
    """Observed quantity and version snapshot for one product or tracked item."""
    __tablename__ = "inventory_count_lines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    count_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    lot_code: Mapped[str | None] = mapped_column(String(100))
    serial_code: Mapped[str | None] = mapped_column(String(100))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_on_hand: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    counted_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    balance_version: Mapped[int] = mapped_column(nullable=False)
    reason_code: Mapped[str] = mapped_column(String(24), nullable=False)
    reason_note: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_inventory_count_line_org_id"),
        UniqueConstraint("organization_id", "count_id", "product_id", "lot_code", name="uq_inventory_count_line_lot"),
        UniqueConstraint("organization_id", "count_id", "product_id", "serial_code", name="uq_inventory_count_line_serial"),
        ForeignKeyConstraint(["organization_id", "count_id"], ["inventory_counts.organization_id", "inventory_counts.id"], ondelete="RESTRICT", name="fk_inventory_count_line_count_same_org"),
        ForeignKeyConstraint(["organization_id", "product_id"], ["inventory_products.organization_id", "inventory_products.id"], ondelete="RESTRICT", name="fk_inventory_count_line_product_same_org"),
        CheckConstraint("expected_on_hand >= 0 AND counted_quantity >= 0", name="ck_inventory_count_line_quantities_nonnegative"),
        CheckConstraint("lot_code IS NULL OR serial_code IS NULL", name="ck_inventory_count_line_one_trace_code"),
        CheckConstraint("reason_code IN ('no_variance','damage','loss','found','data_correction','other')", name="ck_inventory_count_line_reason"),
        Index("ix_inventory_count_line_org_count", "organization_id", "count_id"),
    )

