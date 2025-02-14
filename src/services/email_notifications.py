from database.models.accounts import UserModel
from fastapi import BackgroundTasks

from mail_service.mail_service import SMTPService


def register_notification(
        user: UserModel,
        bg: BackgroundTasks,
        email_sender: SMTPService,
) -> None:
    activation_link = f"http://127.0.0.1/api/v1/accounts/activate/?token={user.activation_token.token}"

    bg.add_task(
        email_sender.send_email,
        to_email=user.email,
        subject="Registration",
        template_name="activation_email.html",
        context={
            "email": user.email,
            "activation_link": activation_link,
        },
    )


def activation_success_notification(
        user_email: str,
        bg: BackgroundTasks,
        email_sender: SMTPService,
) -> None:
    login_link = "http://127.0.0.1/api/v1/accounts/login/"

    bg.add_task(
        email_sender.send_email,
        to_email=user_email,
        subject="Account Activated",
        template_name="activation_email.html",
        context={
            "email": user_email,
            "activation_link": login_link,
        },
    )


def password_reset_request_notification(
        user: UserModel,
        bg: BackgroundTasks,
        email_sender: SMTPService,
) -> None:
    reset_token = (f"http://127.0.0.1/api/v1/accounts/password-reset/request/?token="
                   f"{user.password_reset_token.token}")

    bg.add_task(
        email_sender.send_email,
        to_email=user.email,
        subject="Password Reset Request",
        template_name="password_reset_request_email.html",
        context={
            "email": user.email,
            "reset_link": reset_token,
        },
    )


def password_reset_complete_notification(
        user: UserModel,
        bg: BackgroundTasks,
        email_sender: SMTPService,
) -> None:
    login_link = "http://127.0.0.1/api/v1/accounts/login/"

    bg.add_task(
        email_sender.send_email,
        to_email=user.email,
        subject="Password Successfully Reset",
        template_name="password_reset_complete_email.html",
        context={
            "email": user.email,
            "reset_link": login_link,
        },
    )


def password_change_complete_notification(
        user: UserModel,
        bg: BackgroundTasks,
        email_sender: SMTPService,
) -> None:
    bg.add_task(
        email_sender.send_email,
        to_email=user.email,
        subject="Password Successfully Changed",
        template_name="password_change_complete_email.html",
        context={
            "email": user.email,
        },
    )

def movie_unavailable_notification(
        user: UserModel,
        bg: BackgroundTasks,
        email_sender: SMTPService,
) -> None:
    bg.add_task(
        email_sender.send_email,
        to_email=user.email,
        subject="Movie in your order unavailable",
        template_name="movie_unavailable_email.html",
        context={
            "email": user.email,
        }
    )

def movie_already_in_orders_notification(
        user: UserModel,
        bg: BackgroundTasks,
        email_sender: SMTPService,
) -> None:
    bg.add_task(
        email_sender.send_email,
        to_email=user.email,
        subject="Movie in your order or other",
        template_name="movie_already_in_orders.html",
        context={
            "email": user.email,
        }
    )
