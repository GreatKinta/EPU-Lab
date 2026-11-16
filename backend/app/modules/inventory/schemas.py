from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EquipmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)
    product_type: str = Field(min_length=1, max_length=100)
    quantity_total: int = Field(ge=0, le=1000000)
    unit: str = Field(min_length=1, max_length=30)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=10000)


class EquipmentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str | None = Field(
        default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    )
    name: str | None = Field(default=None, min_length=1, max_length=200)
    product_type: str | None = Field(default=None, min_length=1, max_length=100)
    quantity_total: int | None = Field(default=None, ge=0, le=1000000)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=10000)


class EquipmentOut(EquipmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    image_path: str | None
    quantity_reserved: int
    quantity_available: int
    created_at: datetime
    updated_at: datetime


class BulkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[UUID] = Field(min_length=1, max_length=100)
