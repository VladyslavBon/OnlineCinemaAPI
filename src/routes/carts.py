import json

import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from database import get_db
from database.models.accounts import UserModel
from database.models.cart import CartModel
from database.models.payments import PaymentModel, PaymentStatus
from schemas.carts import CartResponseSchema
from database.models.orders import OrderItemModel, OrderModel, OrderStatusEnum
from services import get_current_user

router = APIRouter()


@router.delete(
    "/delete/{cart_item_id}/",
    summary="Remove order from cart",
    description="<h3>Remove a specific order from the user's shopping cart</h3>",
    responses={
        404: {"description": "Order not found in cart."},
        400: {"description": "Order already purchased."},
        401: {"description": "Unauthorized - User is not authenticated."},
    },
    status_code=status.HTTP_200_OK,
)
def remove_movie_from_cart(
    cart_item_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    cart = db.query(CartModel).filter(CartModel.user_id == user.id).first()

    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    existing_item = (
        db.query(OrderModel)
        .filter(
            OrderModel.cart_id == cart.id,
            OrderModel.id == cart_item_id,
            OrderModel.status == OrderStatusEnum.PENDING,
        )
        .first()
    )

    if not existing_item:
        raise HTTPException(status_code=404, detail="Order not found in cart")

    db.delete(existing_item)
    db.commit()

    return {"detail": "Movie deleted successfully."}


@router.delete(
    "/clear/",
    summary="Clear all items from cart",
    description="<h3>Clear all items from the user's shopping cart</h3>",
    responses={
        404: {"description": "Cart not found."},
        401: {"description": "Unauthorized - User is not authenticated."},
    },
    status_code=status.HTTP_200_OK,
)
def clear_cart(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    cart = db.query(CartModel).filter(CartModel.user_id == user.id).first()

    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart_items = (
        db.query(OrderModel)
        .filter(
            OrderModel.cart_id == cart.id,
            OrderModel.status == OrderStatusEnum.PENDING,
        )
        .all()
    )

    if not cart_items:
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        for item in cart_items:
            db.delete(item)

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to clear cart")

    return {"detail": "All items removed from cart"}


@router.get(
    "/",
    response_model=CartResponseSchema,
)
def get_cart(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cart = db.query(CartModel).filter(CartModel.user_id == user.id).first()
    cart_items = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.cart_id == cart.id).all()

    return CartResponseSchema(
        id=cart.id,
        user_id=user.id,
        cart_items=cart_items,
        price=sum(item.total_amount for item in cart_items),
    )


@router.get(
    "/admin/detail/",
    summary="Get all carts",
    description="Admins can view the contents of users' carts for analysis or troubleshooting.",
)
def get_all_carts(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    if user is None or user.group.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view this resource."
        )

    carts = db.query(CartModel).all()
    carts_list = []

    for cart in carts:
        cart_items = db.query(OrderModel).filter(OrderModel.cart_id == cart.id).all()

        carts_list.append(
            CartResponseSchema(
                id=cart.id,
                user_id=user.id,
                cart_items=cart_items,
                price=sum(item.total_amount for item in cart_items),
            )
        )

    return carts_list


@router.post(
    "/pay-all/",
)
def pay_cart(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cart = db.query(CartModel).filter(CartModel.user_id == user.id).first()
    cart_items = (
        db.query(OrderModel)
        .filter(OrderModel.cart_id == cart.id)
        .filter(OrderModel.status == OrderStatusEnum.PENDING)
        .all()
    )

    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No order in cart or all paid")

    total_amount = sum(item.total_amount for item in cart_items)

    try:
        order_ids = [order.id for order in cart_items]
        intent = stripe.PaymentIntent.create(
            amount=int(total_amount * 100), currency="usd", metadata={"order_ids": json.dumps(order_ids)}
        )

        for order in cart_items:
            new_payment = PaymentModel(
                user_id=order.user_id,
                order_id=order.id,
                amount=order.total_amount,
                external_payment_id=intent.id,
                status=PaymentStatus.SUCCESSFUL,
            )
            db.add(new_payment)
        db.commit()

        return {"client_secret": intent.client_secret}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
