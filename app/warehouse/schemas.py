"""Validated warehouse and location API contracts."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WarehouseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Warehouse code must not be empty")
        return normalized

    @field_validator("name")
    @classmethod
    def trim_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Warehouse name must not be empty")
        return trimmed

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str) -> str:
        return value.strip()


class WarehousePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    status: Literal["active", "inactive"] | None = None

    @field_validator("name")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        trimmed = value.strip() if value is not None else None
        if value is not None and not trimmed:
            raise ValueError("Warehouse name must not be empty")
        return trimmed

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def at_least_one_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one warehouse field must be provided")
        if any(value is None for value in self.model_dump(exclude_unset=True).values()):
            raise ValueError("Warehouse fields cannot be cleared")
        return self


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    code: str
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class WarehouseLocationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    location_type: Literal["zone", "bin", "receiving", "staging", "shipping", "quarantine", "unassigned"]
    parent_location_id: str | None = Field(default=None, min_length=1, max_length=36)
    capacity_limit: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=6)
    capacity_unit: str | None = Field(default=None, min_length=1, max_length=24)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Location code must not be empty")
        return normalized

    @field_validator("name")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        trimmed = value.strip() if value is not None else None
        if value is not None and not trimmed:
            raise ValueError("Location name must not be empty")
        return trimmed

    @field_validator("capacity_unit")
    @classmethod
    def trim_capacity_unit(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def capacity_shape(self):
        if (self.capacity_limit is None) != (self.capacity_unit is None):
            raise ValueError("Capacity limit and capacity unit must be supplied together")
        if self.capacity_unit == "":
            raise ValueError("Capacity unit must not be empty")
        return self


class WarehouseLocationPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    status: Literal["active", "blocked", "inactive"] | None = None
    capacity_limit: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=6)
    capacity_unit: str | None = Field(default=None, min_length=1, max_length=24)

    @field_validator("name")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        trimmed = value.strip() if value is not None else None
        if value is not None and not trimmed:
            raise ValueError("Location name must not be empty")
        return trimmed

    @field_validator("capacity_unit")
    @classmethod
    def trim_capacity_unit(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def patch_shape(self):
        values = self.model_dump(exclude_unset=True)
        if not values:
            raise ValueError("At least one location field must be provided")
        if "name" in values and values["name"] is None:
            raise ValueError("Location name cannot be cleared")
        if "status" in values and values["status"] is None:
            raise ValueError("Location status cannot be cleared")
        if "capacity_limit" in values and "capacity_unit" not in values:
            raise ValueError("Capacity limit and capacity unit must be updated together")
        if "capacity_unit" in values and "capacity_limit" not in values:
            raise ValueError("Capacity limit and capacity unit must be updated together")
        if values.get("capacity_limit") is None and values.get("capacity_unit") is not None:
            raise ValueError("Capacity limit and capacity unit must be supplied together")
        if values.get("capacity_unit") == "":
            raise ValueError("Capacity unit must not be empty")
        return self


class WarehouseLocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)
    id: str
    organization_id: str
    warehouse_id: str
    parent_location_id: str | None
    code: str
    name: str
    location_type: str
    status: str
    capacity_limit: str | None
    capacity_unit: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("capacity_limit", mode="before")
    @classmethod
    def fixed_capacity_text(cls, value: object) -> str | None:
        if value is None:
            return None
        return format(Decimal(value).quantize(Decimal("0.000001")), "f")


class WarehouseReceiptLineCreate(BaseModel):
    product_id: str = Field(min_length=1, max_length=36)
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=6)
    lot_code: str | None = Field(default=None, min_length=1, max_length=100)
    serial_code: str | None = Field(default=None, min_length=1, max_length=100)
    expires_at: datetime | None = None

    @field_validator("quantity", "unit_cost")
    @classmethod
    def finite_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("Amount must be finite")
        return value

    @field_validator("lot_code", "serial_code")
    @classmethod
    def trim_trace_code(cls, value: str | None) -> str | None:
        trimmed = value.strip() if value is not None else None
        if value is not None and not trimmed:
            raise ValueError("Trace code must not be empty")
        return trimmed

    @model_validator(mode="after")
    def trace_shape(self):
        if self.lot_code and self.serial_code:
            raise ValueError("A receipt line can track a lot or a serial, not both")
        if self.expires_at and not self.lot_code:
            raise ValueError("Expiry date requires a lot code")
        return self


class WarehouseReceiptCreate(BaseModel):
    receiving_location_id: str = Field(min_length=1, max_length=36)
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    source_reference: str | None = Field(default=None, max_length=160)
    note: str = Field(default="", max_length=500)
    lines: list[WarehouseReceiptLineCreate] = Field(min_length=1, max_length=200)

    @field_validator("source_reference", "note")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def unique_receipt_targets(self):
        targets = [(line.product_id, line.lot_code, line.serial_code) for line in self.lines]
        if len(targets) != len(set(targets)):
            raise ValueError("Each product or tracked item can appear only once per receipt")
        return self


class WarehouseReceiptLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)
    id: str
    product_id: str
    quantity: str
    unit_cost: str | None
    lot_code: str | None
    serial_code: str | None
    expires_at: datetime | None

    @field_validator("quantity", "unit_cost", mode="before")
    @classmethod
    def fixed_amount(cls, value: object) -> str | None:
        return None if value is None else format(Decimal(value).quantize(Decimal("0.000001")), "f")


class WarehouseReceiptOut(BaseModel):
    id: str
    organization_id: str
    warehouse_id: str
    receiving_location_id: str
    receipt_number: str
    source_reference: str | None
    status: str
    note: str
    created_by_user_id: str
    posted_by_user_id: str | None
    created_at: datetime
    posted_at: datetime | None
    lines: list[WarehouseReceiptLineOut]

