import json
from datetime import datetime
import os

import stripe
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.models import UserModel
from database.models.orders import OrderModel
from database.models.payments import PaymentModel, PaymentStatus
from database import get_db
from schemas.payments import PaymentCreate
from services import get_current_user


load_dotenv()

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

router = APIRouter()


# @router.post("/create-payment/")
# async def create_payment(
#         payment: PaymentCreate,
#         db: Session = Depends(get_db),
#         user: UserModel = Depends(get_current_user)
# ):
#     order = db.query(OrderModel).filter(OrderModel.id == payment.order_id).first()
#     if not order:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
#
#     amount = sum(item.price_at_payment for item in order.order_items)
#
#     if amount != order.total_amount:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Order total does not match calculated amount."
#         )
#
#     try:
#         intent = stripe.PaymentIntent.create(
#             amount=int(amount * 100), currency="usd", metadata={"order_id": payment.order.id}
#         )
#
#         new = PaymentModel(
#             user_id=order.user_id,
#             order_id=order.id,
#             amount=amount,
#             external_payment_id=intent.id,
#             status=PaymentStatus.SUCCESSFUL,
#         )
#         db.add(new)
#         db.commit()
#         db.refresh(new)
#
#         return {"client_secret": intent.client_secret}
#     except stripe.error.StripeError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/stripe-webhook/")
async def stripe_webhook(
        request: Request,
        db: Session = Depends(get_db),
        user: UserModel = Depends(get_current_user)
):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, os.environ["STRIPE_ENDPOINT_SECRET"])
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        try:
            order_id = intent["metadata"]["order_id"]

            payment = db.query(PaymentModel).filter(PaymentModel.order_id == order_id).first()

            if payment:
                payment.status = PaymentStatus.SUCCESSFUL
                db.flush()

            order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
            if order:
                order.status = PaymentStatus.SUCCESSFUL
            db.commit()
        except KeyError:
            order_ids = intent["metadata"]["order_ids"]
            order_ids = json.loads(order_ids)
            for order_id in order_ids:
                payment = db.query(PaymentModel).filter(PaymentModel.order_id == order_id).first()

                if payment:
                    payment.status = PaymentStatus.SUCCESSFUL
                    db.flush()

                order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
                if order:
                    order.status = PaymentStatus.SUCCESSFUL
                db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Payment failed. Please try a different payment method."
        )

    return {"status": "success"}


@router.get("/")
async def get_payments(user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    payments = db.query(PaymentModel).filter(PaymentModel.user_id == user.id).all()
    return payments


@router.get("/mod/payments/")
async def get_moderator_payments(
    user_id: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
    status: PaymentStatus = None,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    filt = db.query(PaymentModel)
    if user_id:
        filt = filt.filter(PaymentModel.user_id == user_id)
    if start_date and end_date:
        filt = filt.filter(PaymentModel.created_at.between(start_date, end_date))
    if status:
        filt = filt.filter(PaymentModel.status == status)
    return filt.all()
