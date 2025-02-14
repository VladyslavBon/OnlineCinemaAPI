from fastapi import APIRouter, Depends, status, BackgroundTasks, Request
from sqlalchemy.orm import Session

from config import get_jwt_auth_manager, get_mail_service
from mail_service.mail_service import SMTPService
from services import get_current_user
from services import email_notifications
from database import get_db
from database.models.accounts import UserModel
from schemas.accounts import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    UserActivationTokenRequestSchema,
    UserReActivationTokenRequestSchema,
    LoginRequestSchema,
    LoginResponseSchema,
    PasswordResetRequestSchema,
    MessageResponseSchema,
    PasswordResetRequestCompleteSchema,
    RefreshTokenRequestSchema,
    RefreshTokenResponseSchema,
    PasswordChangeRequestSchema,
)
from security.jwt_interface import JWTAuthManagerInterface
from services.user_service import (
    create_user,
    activate_user,
    login_user,
    password_reset_request,
    password_reset_complete,
    refresh_token,
    logout_user,
    change_user_password,
    resend_activation_token,
)
from config.rate_limiter import limiter


router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="Register a new user",
    description="<h3>Register a new user with an email and password.</h3>",
    responses={
        409: {
            "description": "Conflict - User with this email already exists.",
            "content": {
                "application/json": {"example": {"detail": "A user with this email test@example.com already exists."}}
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred during user creation.",
            "content": {"application/json": {"example": {"detail": "An error occurred during user creation."}}},
        },
    },
    status_code=status.HTTP_201_CREATED,
)
def register(
        user_data: UserRegistrationRequestSchema,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        email_sender: SMTPService = Depends(get_mail_service),
):
    user = create_user(user_data=user_data, db=db)
    email_notifications.register_notification(
        user=user,
        bg=background_tasks,
        email_sender=email_sender,
    )

    return user


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    summary="Activate a user account",
    description="<h3>Activate a user account with an activation token</h3>",
    responses={
        400: {
            "description": "Bad Request - Invalid or expired activation token.",
            "content": {"application/json": {"example": {"detail": "Invalid or expired activation token."}}},
        },
        404: {
            "description": "Not found - User with this email not found.",
            "content": {"application/json": {"example": {"detail": "No user with email test@example.com was found."}}},
        },
        500: {
            "description": "Internal Server Error - An error occurred during user activation.",
            "content": {"application/json": {"example": {"detail": "An error occurred during user activation."}}},
        },
    },
    status_code=status.HTTP_200_OK,
)
def activate(
    user_data: UserActivationTokenRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: SMTPService = Depends(get_mail_service),
):
    response = activate_user(user_data=user_data, db=db)
    email_notifications.activation_success_notification(
        user_email=user_data.email,
        bg=background_tasks,
        email_sender=email_sender,
    )

    return response


@router.post(
    "/resend-activation/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
)
def re_activate(
    user_data: UserReActivationTokenRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: SMTPService = Depends(get_mail_service),
):
    user, response = resend_activation_token(user_data=user_data, db=db)

    if user:
        email_notifications.register_notification(
            user=user,
            bg=background_tasks,
            email_sender=email_sender,
        )

    return response


@router.post(
    "/login/",
    response_model=LoginResponseSchema,
    summary="Login user",
    description="<h3>Login user with email and password</h3>",
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password.",
            "content": {"application/json": {"example": {"detail": "Invalid email or password."}}},
        },
        403: {
            "description": "Forbidden - User account is not activated.",
            "content": {"application/json": {"example": {"detail": "User account is not activated."}}},
        },
        500: {
            "description": "Internal Server Error - An error occurred during user login.",
            "content": {"application/json": {"example": {"detail": "An error occurred during login."}}},
        },
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("3/10minutes")
def login(
    request: Request,
    user_data: LoginRequestSchema,
    db: Session = Depends(get_db),
    jwt_auth_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
):
    return login_user(user_data=user_data, db=db, jwt_auth_manager=jwt_auth_manager)


@router.post(
    "/logout/",
    response_model=MessageResponseSchema,
    summary="Logout user",
    description="<h3>Logout user and delete refresh token</h3>",
    responses={
        500: {
            "description": "Internal Server Error - An error occurred during user logout.",
            "content": {"application/json": {"example": {"detail": "An error occurred during logout."}}},
        },
    },
    status_code=status.HTTP_200_OK,
)
def logout(db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    return logout_user(db=db, user=user)


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
    summary="Request reset password",
    description="<h3>Request reset password with email, if the user exists and is active</h3>",
    status_code=status.HTTP_200_OK,
)
def request_password_reset(
    user_data: PasswordResetRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: SMTPService = Depends(get_mail_service),
):
    user, response = password_reset_request(user_data=user_data, db=db)

    if user:
        email_notifications.password_reset_request_notification(
            user=user,
            bg=background_tasks,
            email_sender=email_sender,
        )

    return response


@router.post(
    "/password-reset/complete/",
    response_model=MessageResponseSchema,
    summary="Complete reset password",
    description="<h3>Changing password using the transferred email, token and new password</h3>",
    responses={
        400: {
            "description": "Bad Request - Invalid email or token.",
            "content": {"application/json": {"example": {"detail": "Invalid email or token."}}},
        },
        500: {
            "description": "Internal Server Error - An error occurred during user login.",
            "content": {"application/json": {"example": {"detail": "An error occurred while resetting the password."}}},
        },
    },
    status_code=status.HTTP_200_OK,
)
def request_password_reset_complete(
    user_data: PasswordResetRequestCompleteSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: SMTPService = Depends(get_mail_service),
):
    user, response = password_reset_complete(user_data=user_data, db=db)

    if user:
        email_notifications.password_reset_complete_notification(
            user=user,
            bg=background_tasks,
            email_sender=email_sender,
        )
    return response


@router.post(
    "/change-password/",
    response_model=MessageResponseSchema,
    summary="Changing password",
    description="<h3>Changing password using the transferred email, old and new password</h3>",
    responses={
        400: {
            "description": "Bad Request - Invalid email or password.",
            "content": {"application/json": {"example": {"detail": "Invalid email or password."}}},
        },
        500: {
            "description": "Internal Server Error - An error occurred during user login.",
            "content": {"application/json": {"example": {"detail": "An error occurred while changing the password.."}}},
        },
    },
    status_code=status.HTTP_200_OK,
)
def request_change_password(
    user_data: PasswordChangeRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
    email_sender: SMTPService = Depends(get_mail_service),
):
    response = change_user_password(user_data=user_data, db=db, user=user)
    email_notifications.password_change_complete_notification(
        user=user,
        bg=background_tasks,
        email_sender=email_sender,
    )

    return response


@router.post(
    "/refresh/",
    response_model=RefreshTokenResponseSchema,
    summary="Get a new access token",
    description="<h3>Getting a new access token using a refresh token</h3>",
    responses={
        400: {
            "description": "Bad Request - Token has expired or invalid token.",
            "content": {"application/json": {"example": {"detail": "Token has expired or invalid token."}}},
        },
        401: {
            "description": "Unauthorized - Refresh token not found.",
            "content": {"application/json": {"example": {"detail": "Refresh token not found."}}},
        },
        404: {
            "description": "Not Found - User not found.",
            "content": {"application/json": {"example": {"detail": "User not found."}}},
        },
    },
    status_code=status.HTTP_200_OK,
)
def refresh(
    user_data: RefreshTokenRequestSchema,
    db: Session = Depends(get_db),
    jwt_auth_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
):
    return refresh_token(user_data=user_data, db=db, jwt_auth_manager=jwt_auth_manager)
