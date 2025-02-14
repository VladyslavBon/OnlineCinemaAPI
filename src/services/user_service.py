from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    RefreshTokenModel,
    PasswordResetTokenModel,
)
from database.models.cart import CartModel
from exceptions import BaseSecurityError
from schemas.accounts import (
    UserRegistrationRequestSchema,
    UserActivationTokenRequestSchema,
    LoginRequestSchema,
    LoginResponseSchema,
    PasswordResetRequestSchema,
    MessageResponseSchema,
    PasswordResetRequestCompleteSchema,
    RefreshTokenRequestSchema,
    RefreshTokenResponseSchema,
    PasswordChangeRequestSchema,
    UserReActivationTokenRequestSchema,
)
from security.jwt_interface import JWTAuthManagerInterface


def create_user(user_data: UserRegistrationRequestSchema, db: Session) -> UserModel | HTTPException:
    user = db.query(UserModel).filter_by(email=user_data.email).first()

    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"A user with this email {user_data.email} already exists."
        )

    user_group = db.query(UserGroupModel).filter_by(name=UserGroupEnum.USER).first()

    if not user_group:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User group not found.")

    try:
        new_user = UserModel.create(
            email=user_data.email,
            raw_password=user_data.password,
            group_id=user_group.id,
        )
        db.add(new_user)
        db.flush()

        activation_token = ActivationTokenModel(user_id=new_user.id)
        db.add(activation_token)
        db.commit()
        db.refresh(new_user)

        user_cart = CartModel(user_id=new_user.id)
        db.add(user_cart)
        db.commit()

        return new_user
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation.",
        )


def activate_user(user_data: UserActivationTokenRequestSchema, db: Session) -> MessageResponseSchema:
    user = db.query(UserModel).filter_by(email=user_data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user with email {user_data.email} was found.",
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )

    activation_token = db.query(ActivationTokenModel).filter_by(token=user_data.token).first()

    if not activation_token or activation_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation token.")

    try:
        user.is_active = True
        db.delete(activation_token)
        db.commit()

        return MessageResponseSchema(message="User account activated successfully.")
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during account activation.",
        )


def resend_activation_token(
        user_data: UserReActivationTokenRequestSchema,
        db: Session,
) -> tuple[UserModel, MessageResponseSchema]:
    user = db.scalar(select(UserModel).where(UserModel.email == user_data.email))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )

    try:
        db.execute(delete(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id))

        new_activation_token = ActivationTokenModel(user_id=user.id)
        db.add(new_activation_token)
        db.commit()
        db.refresh(user)

        return user, MessageResponseSchema(message="A new activation token has been generated.")
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during the resend activation token.",
        )


def login_user(
    user_data: LoginRequestSchema,
    db: Session,
    jwt_auth_manager: JWTAuthManagerInterface,
) -> LoginResponseSchema:
    user = db.query(UserModel).filter_by(email=user_data.email).first()

    if not user or not user.verify_password(raw_password=user_data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is not activated.")

    try:
        access_token = jwt_auth_manager.create_access_token({"user_id": user.id})
        _refresh_token = jwt_auth_manager.create_refresh_token({"user_id": user.id})
        db_refresh_token = RefreshTokenModel(user_id=user.id, token=_refresh_token)
        db.add(db_refresh_token)
        db.commit()

        return LoginResponseSchema(
            access_token=access_token,
            refresh_token=_refresh_token,
        )

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login.",
        )


def logout_user(db: Session, user: UserModel) -> MessageResponseSchema:
    try:
        db.query(RefreshTokenModel).filter_by(user_id=user.id).delete()
        db.commit()

        return MessageResponseSchema(message="Logout successful.")
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout.",
        )


def password_reset_request(
        user_data: PasswordResetRequestSchema,
        db: Session
) -> tuple[UserModel, MessageResponseSchema]:
    user = db.query(UserModel).filter_by(email=user_data.email).first()

    if not user or not user.is_active:
        return MessageResponseSchema(message="If you are registered, you will receive an email with instructions.")

    try:
        db.query(PasswordResetTokenModel).filter_by(user_id=user.id).delete()

        new_reset_token = PasswordResetTokenModel(user_id=user.id)
        db.add(new_reset_token)
        db.commit()

        return user, MessageResponseSchema(
            message="If you are registered, you will receive an email with instructions."
        )
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during the request to reset the password.",
        )


def password_reset_complete(
    user_data: PasswordResetRequestCompleteSchema,
    db: Session,
) -> tuple[UserModel, MessageResponseSchema]:
    user = db.query(UserModel).filter_by(email=user_data.email).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token.")

    if user.verify_password(raw_password=user_data.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot assign the same password.")

    reset_token = db.query(PasswordResetTokenModel).filter_by(user_id=user.id).first()

    token_expire = reset_token.expires_at.replace(tzinfo=timezone.utc)

    if not reset_token or reset_token.token != user_data.token or token_expire < datetime.now(timezone.utc):
        if reset_token:
            db.delete(reset_token)
            db.commit()

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token.")

    try:
        user.password = user_data.password
        db.delete(reset_token)
        db.commit()

        return user, MessageResponseSchema(message="Password reset successfully.")
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password.",
        )


def change_user_password(
    user_data: PasswordChangeRequestSchema,
    db: Session,
    user: UserModel,
) -> MessageResponseSchema:
    if not user.verify_password(raw_password=user_data.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password.")

    if user.verify_password(raw_password=user_data.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot assign the same password.")

    try:
        user.password = user_data.new_password
        db.query(RefreshTokenModel).filter_by(user_id=user.id).delete()

        db.commit()

        return MessageResponseSchema(message="Password changed successfully")
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while changing the password.",
        )


def refresh_token(
    user_data: RefreshTokenRequestSchema,
    db: Session,
    jwt_auth_manager: JWTAuthManagerInterface,
) -> RefreshTokenResponseSchema:
    try:
        decoded_token = jwt_auth_manager.decode_refresh_token(user_data.refresh_token)
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    refresh_token_exist = db.query(RefreshTokenModel).filter_by(token=user_data.refresh_token).first()

    if not refresh_token_exist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    user = db.query(UserModel).filter_by(id=user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    new_access_token = jwt_auth_manager.create_access_token({"user_id": user_id})
    db.delete(refresh_token_exist)
    db.commit()

    return RefreshTokenResponseSchema(access_token=new_access_token)
