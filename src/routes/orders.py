from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from config.dependencies import get_mail_service
from database.models.accounts import UserModel, UserGroupEnum
from database.models.cart import CartModel
from database.models.movies import MovieModel
from database.models.orders import OrderModel, OrderStatusEnum, OrderItemModel
from mail_service.mail_service import SMTPService
from database import get_db
from schemas.orders import OrderResponseSchema, OrderListResponseSchema, OrderCreateSchema
from services import email_notifications, get_current_user


router = APIRouter()


@router.post("/", response_model=OrderResponseSchema)
def create_order(
    order_data: OrderCreateSchema,
    background_tasks: BackgroundTasks,
    user: UserModel = Depends(get_current_user),
    email_sender: SMTPService = Depends(get_mail_service),
    db: Session = Depends(get_db),
):
    valid_items = []
    movies_ids = set()

    orders = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.user_id == user.id).all()
    for order in orders:
        for item in order.order_items:
            movies_ids.add(item.movie_id)

    total_price = Decimal(0)

    for order_item in order_data.items:
        movie = db.query(MovieModel).filter(MovieModel.id == order_item.movie_id).first()

        if not movie:
            email_notifications.movie_unavailable_notification(
                user=user,
                bg=background_tasks,
                email_sender=email_sender,
            )


        if movie.id in movies_ids:
            email_notifications.movie_already_in_orders_notification(
                user=user,
                bg=background_tasks,
                email_sender=email_sender,
            )

        else:
            item = OrderItemModel(movie_id=order_item.movie_id, price_at_order=Decimal(movie.price))
            valid_items.append(item)
            total_price += Decimal(movie.price)
            movies_ids.add(order_item.movie_id)

    if not valid_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid movies found")

    new_order = OrderModel(
        user_id=user.id,
        total_amount=total_price,
        status=OrderStatusEnum.PENDING,
    )

    db.add(new_order)
    db.flush()

    for order_item in valid_items:
        order_item.order_id = new_order.id
        db.add(order_item)

    db.commit()
    db.refresh(new_order)
    items = db.query(OrderItemModel).filter_by(order_id=new_order.id).all()

    return OrderResponseSchema(
        id=new_order.id,
        user_id=new_order.user_id,
        created_at=new_order.created_at,
        status=new_order.status,
        total_amount=new_order.total_amount,
        order_items=items,
    )


@router.get("/", response_model=OrderListResponseSchema)
def get_orders(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orders = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.user_id == user.id).all()
    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orders not found.")

    return OrderListResponseSchema(
        orders=orders,
    )


@router.get("/all/", response_model=OrderListResponseSchema)
def get_all_users_orders(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status_filter: Optional[OrderStatusEnum] = None,
):
    if user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this resource."
        )

    query = db.query(OrderModel).join(OrderItemModel)

    if user_id:
        query = query.filter(OrderModel.user_id == user_id)

    if start_date:
        query = query.filter(OrderModel.created_at >= start_date)

    if end_date:
        query = query.filter(OrderModel.created_at <= end_date)

    if status_filter:
        query = query.filter(OrderModel.status == status_filter)

    orders = query.all()

    return OrderListResponseSchema(
        orders=orders,
    )


@router.get("/{order_id}/", response_model=OrderResponseSchema)
def get_order(
    order_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.id == order_id).first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    if order.user_id != user.id and user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this resource."
        )

    return order


@router.post(
    "/{order_id}/to-cart",
)
def order_to_cart(
    order_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    if order.user_id != user.id and user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this resource."
        )

    if order.cart_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order already in cart."
        )

    cart = db.query(CartModel).filter(CartModel.user_id == user.id).first()

    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found.")

    orders_in_cart = db.query(OrderModel).join(OrderItemModel).filter(OrderModel.cart_id == cart.id)
    if order in orders_in_cart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order already in cart."
        )

    order.cart_id = cart.id

    db.commit()

    return {"detail": "Orders added to cart"}
