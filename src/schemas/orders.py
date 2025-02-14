from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

from database.models.orders import OrderStatusEnum


class OrderItemSchema(BaseModel):
    movie_id: int


class OrderItemCreateSchema(OrderItemSchema):
    pass


class OrderItemResponseSchema(OrderItemSchema):
    id: int
    price_at_order: Decimal

    model_config = {"from_attributes": True}


class OrderCreateSchema(BaseModel):
    items: list[OrderItemCreateSchema]


class OrderResponseSchema(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    status: OrderStatusEnum
    order_items: list[OrderItemResponseSchema]
    total_amount: Decimal

    model_config = {"from_attributes": True}


class OrderListResponseSchema(BaseModel):
    orders: list[OrderResponseSchema]
