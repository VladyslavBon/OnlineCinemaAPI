from typing import Annotated
from annotated_types import MinLen
from pydantic import BaseModel, EmailStr, field_validator
from database import account_validators


class UserBaseSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str):
        return account_validators.validate_email(value)


class UserRegistrationRequestSchema(UserBaseSchema):
    password: Annotated[str, MinLen(8)]

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str):
        return account_validators.validate_password_strength(value)


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr

    model_config = {"from_attributes": True}


class UserActivationTokenRequestSchema(UserBaseSchema):
    token: str


class UserReActivationTokenRequestSchema(UserBaseSchema):
    pass


class LoginRequestSchema(UserRegistrationRequestSchema):
    pass


class LoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = {"from_attributes": True}


class MessageResponseSchema(BaseModel):
    message: str

    model_config = {"from_attributes": True}


class PasswordResetRequestSchema(UserBaseSchema):
    pass


class PasswordResetRequestCompleteSchema(UserRegistrationRequestSchema):
    token: str


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str


class RefreshTokenResponseSchema(BaseModel):
    access_token: str

    model_config = {"from_attributes": True}


class PasswordChangeRequestSchema(UserRegistrationRequestSchema):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str):
        return account_validators.validate_password_strength(value)
