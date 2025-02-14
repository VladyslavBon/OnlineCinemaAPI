from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from database.models.accounts import (
    UserModel,
    ActivationTokenModel,
    PasswordResetTokenModel,
    UserGroupModel,
    UserGroupEnum,
    RefreshTokenModel
)
from schemas.accounts import MessageResponseSchema, PasswordResetRequestSchema
from services.user_service import password_reset_request


class TestUserRegister:
    def test_register_user_success(self, client, db_session, seed_user_groups):
        """
        Test successful user registration.

        Validates that a new user and an activation token are created in the database.
        """
        payload = {
            "email": "testuser@example.com",
            "password": "StrongPassword123!"
        }

        response = client.post("/api/v1/accounts/register/", json=payload)

        assert response.status_code == 201, "Expected status code 201 Created."
        response_data = response.json()
        assert response_data["email"] == payload["email"], "Returned email does not match."
        assert "id" in response_data, "Response does not contain user ID."

        created_user = db_session.query(UserModel).filter_by(email=payload["email"]).first()
        assert created_user is not None, "User was not created in the database."
        assert created_user.email == payload["email"], "Created user's email does not match."

        activation_token = db_session.query(ActivationTokenModel).filter_by(user_id=created_user.id).first()
        assert activation_token is not None, "Activation token was not created in the database."
        assert activation_token.user_id == created_user.id, "Activation token's user_id does not match."
        assert activation_token.token is not None, "Activation token has no token value."

        expires_at = activation_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        assert expires_at > datetime.now(timezone.utc), "Activation token is already expired."

    @pytest.mark.parametrize("invalid_password, expected_error", [
        # ("short", "Password must contain at least 8 characters."),
        ("NoDigitHere!", "Password must contain at least one digit."),
        ("nodigitnorupper@", "Password must contain at least one uppercase letter."),
        ("NOLOWERCASE1@", "Password must contain at least one lower letter."),
        ("NoSpecial123", "Password must contain at least one special character: @, $, !, %, *, ?, #, &."),
    ])
    def test_register_user_password_validation(self, client, seed_user_groups, invalid_password, expected_error):
        """
        Test password strength validation in the user registration endpoint.

        Ensures the endpoint returns the correct error for invalid passwords.
        """
        payload = {
            "email": "testuser@example.com",
            "password": invalid_password
        }

        response = client.post("/api/v1/accounts/register/", json=payload)

        assert response.status_code == 422, "Expected status code 422 for invalid input."

        response_data = response.json()
        assert expected_error in str(response_data), f"Expected error message: {expected_error}"

    def test_register_user_conflict(self, client, db_session, seed_user_groups):
        """
        Test user registration conflict.

        Ensures that trying to register a user with an existing email
        returns a 409 Conflict status and the correct error message.
        """
        payload = {
            "email": "conflictuser@example.com",
            "password": "StrongPassword123!"
        }

        response_first = client.post("/api/v1/accounts/register/", json=payload)
        assert response_first.status_code == 201, "Expected status code 201 for the first registration."

        created_user = db_session.query(UserModel).filter_by(email=payload["email"]).first()
        assert created_user is not None, "User should be created after the first registration."

        response_second = client.post("/api/v1/accounts/register/", json=payload)
        assert response_second.status_code == 409, "Expected status code 409 for a duplicate registration."

        response_data = response_second.json()
        expected_message = f"A user with this email {payload['email']} already exists."
        assert response_data["detail"] == expected_message, f"Expected error message: {expected_message}"

    def test_register_user_internal_server_error(self, client, seed_user_groups):
        """
        Test server error during user registration.

        Ensures that a 500 Internal Server Error is returned when a database operation fails.
        """
        payload = {
            "email": "erroruser@example.com",
            "password": "StrongPassword123!"
        }

        with patch("routes.accounts.Session.commit", side_effect=SQLAlchemyError):
            response = client.post("/api/v1/accounts/register/", json=payload)

            assert response.status_code == 500, "Expected status code 500 for internal server error."

            response_data = response.json()
            expected_message = "An error occurred during user creation."
            assert response_data["detail"] == expected_message, f"Expected error message: {expected_message}"


class TestUserActivation:
    def test_activate_account_success(self, client, db_session, seed_user_groups):
        """
        Test successful activation of a user account.

        Steps:
        - Register a new user.
        - Verify the user is inactive.
        - Activate the user using the activation token.
        - Verify the user is activated and the token is deleted.
        """
        registration_payload = {
            "email": "testuser@example.com",
            "password": "StrongPassword123!"
        }

        registration_response = client.post("/api/v1/accounts/register/", json=registration_payload)
        assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

        user = db_session.query(UserModel).filter_by(email=registration_payload["email"]).first()
        assert user is not None, "User was not created in the database."
        assert not user.is_active, "Newly registered user should not be active."

        assert user.activation_token.token is not None, "Activation token was not created in the database."

        activation_payload = {
            "email": registration_payload["email"],
            "token": user.activation_token.token
        }

        activation_response = client.post("/api/v1/accounts/activate/", json=activation_payload)
        assert activation_response.status_code == 200, "Expected status code 200 for successful activation."
        assert activation_response.json()["message"] == "User account activated successfully."

        user = db_session.query(UserModel).filter_by(email=registration_payload["email"]).first()
        db_session.refresh(user)
        assert user.is_active, "User should be active after successful activation."

        token = db_session.query(ActivationTokenModel).filter_by(user_id=user.id).first()
        assert token is None, "Activation token should be deleted after successful activation."

    def test_activate_user_with_expired_token(self, client, db_session, seed_user_groups):
        """
        Test activation with an expired token.

        Ensures that the endpoint returns a 400 error when the activation token is expired.
        """
        registration_payload = {
            "email": "testuser@example.com",
            "password": "StrongPassword123!"
        }
        registration_response = client.post("/api/v1/accounts/register/", json=registration_payload)
        assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

        user = db_session.query(UserModel).filter_by(email=registration_payload["email"]).first()
        assert user is not None, "User should exist in the database."
        assert not user.is_active, "User should not be active before activation."

        activation_token = db_session.query(ActivationTokenModel).filter_by(user_id=user.id).first()
        assert activation_token is not None, "Activation token should exist for the user."
        activation_token.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
        db_session.commit()

        activation_payload = {
            "email": registration_payload["email"],
            "token": activation_token.token
        }
        activation_response = client.post("/api/v1/accounts/activate/", json=activation_payload)

        assert activation_response.status_code == 400, "Expected status code 400 for expired token."
        assert activation_response.json()["detail"] == "Invalid or expired activation token.", (
            "Expected error message for expired token."
        )

    def test_activate_user_with_deleted_token(self, client, db_session, seed_user_groups):
        """
        Test activation with a deleted token.

        Ensures that the endpoint returns a 400 error when the activation token is deleted.
        """
        registration_payload = {
            "email": "testuser@example.com",
            "password": "StrongPassword123!"
        }
        registration_response = client.post("/api/v1/accounts/register/", json=registration_payload)
        assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

        user = db_session.query(UserModel).filter_by(email=registration_payload["email"]).first()
        assert user is not None, "User should exist in the database."
        assert not user.is_active, "User should not be active before activation."

        activation_token = db_session.query(ActivationTokenModel).filter_by(user_id=user.id).first()
        assert activation_token is not None, "Activation token should exist for the user."
        db_session.delete(activation_token)
        db_session.commit()

        activation_payload = {
            "email": registration_payload["email"],
            "token": activation_token.token
        }
        activation_response = client.post("/api/v1/accounts/activate/", json=activation_payload)

        assert activation_response.status_code == 400, "Expected status code 400 for deleted token."
        assert activation_response.json()["detail"] == "Invalid or expired activation token.", (
            "Expected error message for deleted token."
        )

    def test_activate_already_active_user(self, client, db_session, seed_user_groups):
        """
        Test activation of an already active user.

        Ensures that the endpoint returns a 400 error if the user is already active.
        """
        registration_payload = {
            "email": "testuser@example.com",
            "password": "StrongPassword123!"
        }
        registration_response = client.post("/api/v1/accounts/register/", json=registration_payload)
        assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

        user = db_session.query(UserModel).filter_by(email=registration_payload["email"]).first()
        assert user is not None, "User should exist in the database."

        user.is_active = True
        db_session.commit()

        activation_token = db_session.query(ActivationTokenModel).filter_by(user_id=user.id).first()
        assert activation_token is not None, "Activation token should exist for the user."

        activation_payload = {
            "email": registration_payload["email"],
            "token": activation_token.token
        }
        activation_response = client.post("/api/v1/accounts/activate/", json=activation_payload)

        assert activation_response.status_code == 400, "Expected status code 400 for already active user."
        assert activation_response.json()["detail"] == "User account is already active.", (
            "Expected error message for already active user."
        )


class TestResetPassword:
    def test_request_password_reset_token_success(self, client, db_session, seed_user_groups):
        """
        Test successful password reset token request.

        Ensures that a password reset token is created for an active user.
        """
        registration_payload = {
            "email": "testuser@example.com",
            "password": "StrongPassword123!"
        }
        registration_response = client.post("/api/v1/accounts/register/", json=registration_payload)
        assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

        user = db_session.query(UserModel).filter_by(email=registration_payload["email"]).first()
        assert user is not None, "User should exist in the database."

        user.is_active = True
        db_session.commit()

        reset_payload = {"email": registration_payload["email"]}
        reset_response = client.post("/api/v1/accounts/password-reset/request/", json=reset_payload)

        assert reset_response.status_code == 200, "Expected status code 200 for successful token request."
        assert reset_response.json()[
                   "message"] == "If you are registered, you will receive an email with instructions.", (
            "Expected success message for password reset token request."
        )

        reset_token = db_session.query(PasswordResetTokenModel).filter_by(user_id=user.id).first()
        assert reset_token is not None, "Password reset token should be created for the user."

        expires_at = reset_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        assert expires_at > datetime.now(timezone.utc), "Password reset token should have a future expiration date."


class TestLoginUser:
    def test_login_user_success(self, client, db_session, jwt_manager, seed_user_groups):
        """
        Test successful login.

        Validates that access and refresh tokens are returned, refresh token is stored in the database,
        and both tokens are valid.
        """
        user_payload = {
            "email": "testuser@example.com",
            "password": "StrongPassword123!"
        }
        user_group = db_session.query(UserGroupModel).filter_by(name=UserGroupEnum.USER).first()

        user = UserModel.create(
            email=user_payload["email"],
            raw_password=user_payload["password"],
            group_id=user_group.id
        )
        user.is_active = True
        db_session.add(user)
        db_session.commit()

        login_payload = {
            "email": user_payload["email"],
            "password": user_payload["password"]
        }
        response = client.post("/api/v1/accounts/login/", json=login_payload)

        assert response.status_code == 200, "Expected status code 200 for successful login."
        response_data = response.json()
        assert "access_token" in response_data, "Access token is missing in the response."
        assert "refresh_token" in response_data, "Refresh token is missing in the response."
        assert response_data["access_token"], "Access token is empty."
        assert response_data["refresh_token"], "Refresh token is empty."

        access_token_data = jwt_manager.decode_access_token(response_data["access_token"])
        assert access_token_data["user_id"] == user.id, "Access token does not contain correct user ID."

        refresh_token_data = jwt_manager.decode_refresh_token(response_data["refresh_token"])
        assert refresh_token_data["user_id"] == user.id, "Refresh token does not contain correct user ID."

        refresh_token_record = db_session.query(RefreshTokenModel).filter_by(user_id=user.id).first()
        assert refresh_token_record is not None, "Refresh token was not stored in the database."
        assert refresh_token_record.token == response_data["refresh_token"], "Stored refresh token does not match."

        expires_at = refresh_token_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        assert expires_at > datetime.now(timezone.utc), "Refresh token is already expired."

    def test_login_user_invalid_cases(self, client, db_session, seed_user_groups):
        """
        Test login with invalid cases:
        1. Non-existent user.
        2. Incorrect password for an existing user.
        """
        login_payload = {
            "email": "nonexistent@example.com",
            "password": "SomePassword123!"
        }
        response = client.post("/api/v1/accounts/login/", json=login_payload)

        assert response.status_code == 401, "Expected status code 401 for non-existent user."
        assert response.json()[
                   "detail"] == "Invalid email or password.", "Unexpected error message for non-existent user."

        user_payload = {
            "email": "testuser@example.com",
            "password": "CorrectPassword123!"
        }
        user_group = db_session.query(UserGroupModel).filter_by(name=UserGroupEnum.USER).first()

        user = UserModel.create(
            email=user_payload["email"],
            raw_password=user_payload["password"],
            group_id=user_group.id
        )
        user.is_active = True
        db_session.add(user)
        db_session.commit()

        login_payload_incorrect_password = {
            "email": user_payload["email"],
            "password": "WrongPassword123!"
        }
        response = client.post("/api/v1/accounts/login/", json=login_payload_incorrect_password)

        assert response.status_code == 401, "Expected status code 401 for incorrect password."
        assert response.json()["detail"] == "Invalid email or password.", \
            "Unexpected error message for incorrect password."


class TestRefreshToken:
    # def test_refresh_access_token_success(self, client, db_session, jwt_manager, seed_user_groups):
    #     """
    #     Test successful access token refresh.
    #
    #     Validates that a new access token is returned when a valid refresh token is provided.
    #     """
    #     user_payload = {
    #         "email": "testuser@example.com",
    #         "password": "StrongPassword123!"
    #     }
    #     user_group = db_session.query(UserGroupModel).filter_by(name=UserGroupEnum.USER).first()
    #
    #     user = UserModel.create(
    #         email=user_payload["email"],
    #         raw_password=user_payload["password"],
    #         group_id=user_group.id
    #     )
    #     user.is_active = True
    #     db_session.add(user)
    #     db_session.commit()
    #
    #     login_payload = {
    #         "email": user_payload["email"],
    #         "password": user_payload["password"]
    #     }
    #     login_response = client.post("/api/v1/accounts/login/", json=login_payload)
    #     assert login_response.status_code == 200, "Expected status code 200 for successful login."
    #     login_data = login_response.json()
    #     refresh_token = login_data["refresh_token"]
    #
    #     refresh_payload = {"refresh_token": refresh_token}
    #     refresh_response = client.post("/api/v1/accounts/refresh/", json=refresh_payload)
    #
    #     assert refresh_response.status_code == 200, "Expected status code 200 for successful token refresh."
    #     refresh_data = refresh_response.json()
    #     assert "access_token" in refresh_data, "Access token is missing in the response."
    #     assert refresh_data["access_token"], "Access token is empty."
    #
    #     access_token_data = jwt_manager.decode_access_token(refresh_data["access_token"])
    #     assert access_token_data["user_id"] == user.id, "Access token does not contain correct user ID."

    def test_refresh_access_token_expired_token(self, client, jwt_manager):
        """
        Test refresh token with expired token.

        Validates that a 400 status code and 'Token has expired.' message are returned
        when the refresh token is expired.
        """
        expired_token = jwt_manager.create_refresh_token(
            {"user_id": 1},
            expires_delta=timedelta(days=-1)
        )

        refresh_payload = {"refresh_token": expired_token}
        refresh_response = client.post("/api/v1/accounts/refresh/", json=refresh_payload)

        assert refresh_response.status_code == 400, "Expected status code 400 for expired token."
        assert refresh_response.json()["detail"] == "Token has expired.", "Unexpected error message."

    def test_refresh_access_token_token_not_found(self, client, jwt_manager):
        """
        Test refresh token when token is not found in the database.

        Validates that a 401 status code and 'Refresh token not found.' message
        are returned when the refresh token is not stored in the database.
        """
        refresh_token = jwt_manager.create_refresh_token({"user_id": 1})

        refresh_payload = {"refresh_token": refresh_token}
        refresh_response = client.post("/api/v1/accounts/refresh/", json=refresh_payload)

        assert refresh_response.status_code == 401, "Expected status code 401 for token not found."
        assert refresh_response.json()["detail"] == "Refresh token not found.", "Unexpected error message."

    def test_refresh_access_token_user_not_found(self, client, db_session, jwt_manager, seed_user_groups):
        """
        Test refresh token when user ID inside the token does not exist in the database.

        Validates that a 404 status code and 'User not found.' message
        are returned when the user ID in the token is invalid.
        """
        user_payload = {
            "email": "testuser@example.com",
            "password": "StrongPassword123!"
        }
        user_group = db_session.query(UserGroupModel).filter_by(name=UserGroupEnum.USER).first()

        user = UserModel.create(
            email=user_payload["email"],
            raw_password=user_payload["password"],
            group_id=user_group.id
        )
        user.is_active = True
        db_session.add(user)
        db_session.commit()

        invalid_user_id = 9999
        refresh_token = jwt_manager.create_refresh_token({"user_id": invalid_user_id})

        refresh_token_record = RefreshTokenModel.create(
            user_id=invalid_user_id,
            days_valid=7,
            token=refresh_token
        )
        db_session.add(refresh_token_record)
        db_session.commit()

        refresh_payload = {"refresh_token": refresh_token}
        refresh_response = client.post("/api/v1/accounts/refresh/", json=refresh_payload)

        assert refresh_response.status_code == 404, "Expected status code 404 for non-existent user."
        assert refresh_response.json()["detail"] == "User not found.", "Unexpected error message."
