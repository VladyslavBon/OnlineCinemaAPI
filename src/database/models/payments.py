from datetime import datetime
import enum
from decimal import Decimal
from typing import List
from sqlalchemy import ForeignKey, DateTime, Numeric, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.accounts import UserModel
from database.models.base import Base
from database.models.orders import OrderModel, OrderItemModel


class PaymentStatus(enum.Enum):
    SUCCESSFUL = "successful"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey(OrderModel.id), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.SUCCESSFUL)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    external_payment_id: Mapped[str] = mapped_column(nullable=True)

    user: Mapped["UserModel"] = relationship()
    order: Mapped[OrderModel] = relationship()
    payment_items: Mapped[List["PaymentItemModel"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )


class PaymentItemModel(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"), nullable=False)
    price_at_payment: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    payment: Mapped["PaymentModel"] = relationship(back_populates="payment_items")
    order_item: Mapped["OrderItemModel"] = relationship()
