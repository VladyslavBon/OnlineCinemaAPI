from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class PaymentStatus(str, Enum):
    SUCCESSFUL = "successful"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentCreate(BaseModel):
    order_id: int
    amount: Decimal


class PaymentResponse(BaseModel):
    id: int
    user_id: int
    order_id: int
    created_at: datetime
    status: PaymentStatus
    amount: Decimal
