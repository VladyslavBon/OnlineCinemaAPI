from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from schemas.orders import OrderResponseSchema


class CartItemBaseSchema(BaseModel):
    movie_id: int


class CartItemCreateSchema(CartItemBaseSchema):
    added_at: date


class CartResponseSchema(BaseModel):
    id: int
    user_id: int
    cart_items: list[OrderResponseSchema]
    price: Decimal

    model_config = {"from_attributes": True}
