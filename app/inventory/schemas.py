"""Transport schemas for inventory master data and stock movements."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _fixed_decimal_text(value: object) -> str:
    """Return one portable six-place representation across PostgreSQL and SQLite."""
    amount = Decimal(str(value))
    return format(amount.quantize(Decimal("0.000001")), "f")


class CategoryCreate(BaseModel):
    code: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=120)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    code: str
    name: str
    archived_at: datetime | None


class UnitCreate(BaseModel):
    code: str = Field(min_length=1, max_length=24, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=80)
    decimal_places: int = Field(default=3, ge=0, le=6)


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    code: str
    name: str
    decimal_places: int
    archived_at: datetime | None


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    kind: Literal["family", "sku"] = "sku"
    family_id: str | None = Field(default=None, max_length=36)
    variant_attributes: dict[str, str] = Field(default_factory=dict)
    category_id: str | None = Field(default=None, max_length=36)
    unit_id: str = Field(min_length=1, max_length=36)
    barcode: str | None = Field(default=None, min_length=1, max_length=120)
    tracking_mode: Literal["none", "lot", "serial"] = "none"
    cost_currency: str = Field(default="MYR", pattern=r"^[A-Za-z]{3}$")

    @field_validator("variant_attributes")
    @classmethod
    def clean_variant_attributes(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned = {key.strip(): item.strip() for key, item in value.items()}
        if any(not key or not item or len(key) > 60 or len(item) > 120 for key, item in cleaned.items()):
            raise ValueError("Variant attribute names and values must be non-empty and within their length limits")
        if len(cleaned) != len(value):
            raise ValueError("Variant attribute names must be unique after trimming")
        return cleaned

    @model_validator(mode="after")
    def validate_family_shape(self):
        if self.kind == "family" and (self.family_id is not None or self.variant_attributes or self.barcode):
            raise ValueError("A product family cannot have a parent, variant attributes, or a barcode")
        if self.family_id is None and self.variant_attributes:
            raise ValueError("Variant attributes require a product family")
        if self.family_id is not None and not self.variant_attributes:
            raise ValueError("A variant must include at least one attribute")
        return self


class ProductPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    category_id: str | None = Field(default=None, max_length=36)
    barcode: str | None = Field(default=None, min_length=1, max_length=120)


class ProductBarcodeCreate(BaseModel):
    barcode: str = Field(min_length=1, max_length=120)


class ProductBarcodeOut(BaseModel):
    id: str
    barcode: str
    is_primary: bool
    created_at: datetime


class ProductOut(BaseModel):
    id: str
    organization_id: str
    sku: str
    name: str
    description: str
    kind: Literal["family", "sku"]
    family_id: str | None
    variant_attributes: dict[str, str]
    category_id: str | None
    unit_id: str
    unit_code: str
    unit_name: str
    barcode: str | None
    barcodes: list[ProductBarcodeOut]
    tracking_mode: str
    cost_currency: str
    average_cost: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("average_cost", mode="before")
    @classmethod
    def fixed_cost_text(cls, value: object) -> str:
        return _fixed_decimal_text(value)


class MovementCreate(BaseModel):
    product_id: str = Field(min_length=1, max_length=36)
    warehouse_location_id: str | None = Field(default=None, min_length=1, max_length=36)
    movement_type: Literal["receipt", "issue", "adjustment", "count", "reserve", "release"]
    quantity: Decimal = Field(max_digits=20, decimal_places=6)
    direction: Literal["increase", "decrease"] | None = None
    unit_cost: Decimal | None = Field(default=None, max_digits=20, decimal_places=6)
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    lot_code: str | None = Field(default=None, max_length=100)
    serial_code: str | None = Field(default=None, max_length=100)
    expires_at: datetime | None = None
    note: str = Field(default="", max_length=500)

    @field_validator("quantity", "unit_cost")
    @classmethod
    def finite_decimal(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and (not value.is_finite() or value < 0):
            raise ValueError("Amount must be a finite, non-negative decimal")
        return value

    @model_validator(mode="after")
    def movement_shape(self):
        if self.movement_type == "count":
            if self.direction is not None:
                raise ValueError("A count supplies the observed on-hand quantity; direction is not used")
        elif self.quantity <= 0:
            raise ValueError("Movement quantity must be greater than zero")
        if self.movement_type == "adjustment" and self.direction is None:
            raise ValueError("Adjustment direction is required")
        if self.movement_type != "adjustment" and self.direction is not None:
            raise ValueError("Direction is only valid for an adjustment")
        if self.movement_type != "receipt" and self.unit_cost is not None:
            raise ValueError("Unit cost may only be supplied for a receipt")
        return self


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)
    id: str
    organization_id: str
    product_id: str
    movement_type: str
    quantity_delta: str
    reserved_delta: str
    unit_cost: str | None
    currency_code: str
    idempotency_key: str
    lot_code: str | None
    serial_code: str | None
    expires_at: datetime | None
    warehouse_location_id: str | None
    note: str
    actor_user_id: str
    reversal_of_movement_id: str | None
    created_at: datetime

    @field_validator("quantity_delta", "reserved_delta", "unit_cost", mode="before")
    @classmethod
    def fixed_amount_text(cls, value: object) -> str | None:
        return None if value is None else _fixed_decimal_text(value)


class MovementReverse(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    note: str = Field(min_length=1, max_length=500)


class BalanceOut(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)
    product_id: str
    sku: str
    product_name: str
    unit_code: str
    on_hand: str
    reserved: str
    available: str
    average_cost: str
    cost_currency: str
    version: int

    @field_validator("on_hand", "reserved", "available", "average_cost", mode="before")
    @classmethod
    def fixed_amount_text(cls, value: object) -> str:
        return _fixed_decimal_text(value)


class InventoryReconciliationItem(BaseModel):
    product_id: str
    sku: str
    product_name: str
    balance_exists: bool
    ledger_on_hand: str
    balance_on_hand: str
    ledger_reserved: str
    balance_reserved: str
    reconciled: bool

    @field_validator("ledger_on_hand", "balance_on_hand", "ledger_reserved", "balance_reserved", mode="before")
    @classmethod
    def fixed_amount_text(cls, value: object) -> str:
        return _fixed_decimal_text(value)


class InventoryReconciliationOut(BaseModel):
    items: list[InventoryReconciliationItem]
    limit: int
    offset: int
    product_count: int
    mismatch_count: int
    reconciled: bool


class InventoryCountLineCreate(BaseModel):
    product_id: str = Field(min_length=1, max_length=36)
    lot_code: str | None = Field(default=None, min_length=1, max_length=100)
    serial_code: str | None = Field(default=None, min_length=1, max_length=100)
    expires_at: datetime | None = None
    counted_quantity: Decimal = Field(max_digits=20, decimal_places=6)
    reason_code: Literal["no_variance", "damage", "loss", "found", "data_correction", "other"] = "no_variance"
    reason_note: str = Field(default="", max_length=300)

    @field_validator("counted_quantity")
    @classmethod
    def count_quantity_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0:
            raise ValueError("Counted quantity must be a finite, non-negative decimal")
        return value

    @field_validator("reason_note")
    @classmethod
    def other_reason_has_note(cls, value: str, info):
        if info.data.get("reason_code") == "other" and not value.strip():
            raise ValueError("A note is required when the reason is 'other'")
        return value.strip()

    @model_validator(mode="after")
    def trace_code_is_unambiguous(self):
        if self.lot_code and self.serial_code:
            raise ValueError("A count line can identify a lot or serial, not both")
        if self.expires_at and not self.lot_code:
            raise ValueError("Expiry date requires a lot code")
        return self


class InventoryCountCreate(BaseModel):
    count_type: Literal["cycle", "full_stocktake"] = "cycle"
    note: str = Field(default="", max_length=500)
    lines: list[InventoryCountLineCreate] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_count_targets(self):
        targets = [(line.product_id, line.lot_code, line.serial_code) for line in self.lines]
        if len(targets) != len(set(targets)):
            raise ValueError("Each product or tracked item can appear only once in a count")
        untracked_products = [target[0] for target in targets if target[1] is None and target[2] is None]
        if len(untracked_products) != len(set(untracked_products)):
            raise ValueError("An untracked product can appear only once in a count")
        return self


class InventoryCountLineOut(BaseModel):
    id: str
    product_id: str
    lot_code: str | None
    serial_code: str | None
    expires_at: datetime | None
    expected_on_hand: str
    counted_quantity: str
    variance: str
    balance_version: int
    reason_code: str
    reason_note: str

    @field_validator("expected_on_hand", "counted_quantity", "variance", mode="before")
    @classmethod
    def fixed_amount_text(cls, value: object) -> str:
        return _fixed_decimal_text(value)


class InventoryCountOut(BaseModel):
    id: str
    organization_id: str
    count_number: str
    count_type: str
    status: str
    note: str
    created_by_user_id: str
    submitted_by_user_id: str | None
    approved_by_user_id: str | None
    created_at: datetime
    submitted_at: datetime | None
    approved_at: datetime | None
    lines: list[InventoryCountLineOut]


class Page(BaseModel):
    items: list
    limit: int
    offset: int


