from datetime import date
from typing import Optional

from fastapi import UploadFile, Form, File, HTTPException
from pydantic import BaseModel, field_validator, HttpUrl

from validation import validate_name, validate_image, validate_gender, validate_birth_date


class ProfileCreateSchema(BaseModel):
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    info: str
    avatar: UploadFile

    @classmethod
    def from_form(
        cls,
        first_name: str = Form(...),
        last_name: str = Form(...),
        gender: str = Form(...),
        date_of_birth: date = Form(...),
        info: str = Form(...),
        avatar: UploadFile = File(...),
    ) -> "ProfileCreateSchema":
        return cls(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar,
        )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name_field(cls, name: str) -> str:
        try:
            validate_name(name)
            return name.lower()
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=[
                    {
                        "type": "value_error",
                        "loc": ["first_name" if "first_name" in name else "last_name"],
                        "msg": str(error),
                        "input": name,
                    }
                ],
            )

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, avatar: Optional[UploadFile]) -> Optional[UploadFile]:
        try:
            validate_image(avatar)
            return avatar
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=[{"type": "value_error", "loc": ["avatar"], "msg": str(error), "input": avatar.filename}],
            )

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, gender: str) -> str:
        try:
            validate_gender(gender)
            return gender
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail=[{"type": "value_error", "loc": ["gender"], "msg": str(error), "input": gender}]
            )

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, date_of_birth: date) -> date:
        try:
            validate_birth_date(date_of_birth)
            return date_of_birth
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=[
                    {"type": "value_error", "loc": ["date_of_birth"], "msg": str(error), "input": str(date_of_birth)}
                ],
            )

    @field_validator("info")
    @classmethod
    def validate_info(cls, info: str) -> str:
        cleaned_info = info.strip()
        if not cleaned_info:
            raise HTTPException(
                status_code=422,
                detail=[
                    {
                        "type": "value_error",
                        "loc": ["info"],
                        "msg": "Info field cannot be empty or contain only spaces.",
                        "input": info,
                    }
                ],
            )
        return cleaned_info


class ProfileResponseSchema(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    info: str
    avatar: HttpUrl
