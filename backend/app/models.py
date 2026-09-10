from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(StrEnum):
    admin = "admin"
    planner = "planner"
    designer = "designer"
    supply = "supply"
    worker = "worker"
    observer = "observer"


class OrderStatus(StrEnum):
    draft = "draft"
    queued = "queued"


class ItemType(StrEnum):
    kitchen = "kitchen"
    wardrobe = "wardrobe"
    cabinet = "cabinet"
    hallway = "hallway"
    mirror = "mirror"
    appliance = "appliance"
    other = "other"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.observer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_orders: Mapped[list["Order"]] = relationship(back_populates="created_by", foreign_keys="Order.created_by_id")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer: Mapped[str] = mapped_column(String(200), index=True)
    contract_number: Mapped[str] = mapped_column(String(80), default="")
    contract_date: Mapped[date] = mapped_column(Date)
    launch_date: Mapped[date] = mapped_column(Date)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"), default=OrderStatus.queued)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    claimed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id], back_populates="created_orders")
    claimed_by: Mapped[User | None] = relationship(foreign_keys=[claimed_by_id])
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType, name="item_type"))
    comment: Mapped[str] = mapped_column(String(300), default="")
    qty: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    constructor_coeff: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"))
    area_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    linear_m: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")
