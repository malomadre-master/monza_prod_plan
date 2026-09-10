from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.catalog import LINEAR_PER_M2, ITEM_TYPE_VALUES
from app.models import AttachmentStore, ItemType, OrderStatus, UserRole


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    efficiency: Decimal = Decimal("1.00")

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreateIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=3, max_length=200)
    role: UserRole
    is_active: bool = True
    efficiency: Decimal = Field(default=Decimal("1.00"), ge=Decimal("0.1"), le=Decimal("2.0"))


class UserPatchIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None
    efficiency: Decimal | None = Field(default=None, ge=Decimal("0.1"), le=Decimal("2.0"))


class OrderItemIn(BaseModel):
    item_type: ItemType
    comment: str = ""
    qty: int = Field(default=1, ge=1, le=999)
    priority: int = Field(default=3, ge=1, le=9)
    constructor_coeff: Decimal = Field(default=Decimal("1.0"), ge=Decimal("0.1"), le=Decimal("2.0"))
    area_m2: Decimal = Field(gt=0, le=Decimal("10000"))

    @field_validator("item_type")
    @classmethod
    def known_type(cls, value: ItemType) -> ItemType:
        if value.value not in ITEM_TYPE_VALUES:
            raise ValueError("unknown item type")
        return value


class OrderItemOut(BaseModel):
    id: int
    item_type: ItemType
    comment: str
    qty: int
    priority: int
    constructor_coeff: Decimal
    area_m2: Decimal
    linear_m: Decimal
    procurement_needed: bool | None = None
    construction_done_at: datetime | None = None

    model_config = {"from_attributes": True}


class AttachmentOut(BaseModel):
    id: int
    item_id: int
    store: AttachmentStore
    original_name: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ItemCompleteIn(BaseModel):
    procurement_needed: bool


class OrderIn(BaseModel):
    customer: str = Field(min_length=1, max_length=200)
    contract_number: str = Field(default="", max_length=80)
    contract_date: date
    launch_date: date
    priority: int = Field(default=3, ge=1, le=9)
    status: OrderStatus = OrderStatus.queued
    notes: str = ""
    items: list[OrderItemIn] = Field(min_length=1)


class OrderOut(BaseModel):
    id: int
    customer: str
    contract_number: str
    contract_date: date
    launch_date: date
    priority: int
    status: OrderStatus
    notes: str
    created_by_id: int
    claimed_by_id: int | None
    claimed_by_name: str | None = None
    created_at: datetime
    items: list[OrderItemOut]
    total_area_m2: Decimal
    total_qty: int

    model_config = {"from_attributes": True}


class OrderListOut(BaseModel):
    id: int
    customer: str
    contract_number: str
    contract_date: date
    launch_date: date
    priority: int
    status: OrderStatus
    item_count: int
    total_area_m2: Decimal
    created_by_name: str
    claimed_by_id: int | None = None
    claimed_by_name: str | None = None

    model_config = {"from_attributes": True}


class PlanSlotOut(BaseModel):
    order_id: int
    item_id: int
    customer: str
    center_code: str
    volume: Decimal
    start: date
    finish: date


def linear_from_area(area_m2: Decimal) -> Decimal:
    return (area_m2 * LINEAR_PER_M2).quantize(Decimal("0.01"))
