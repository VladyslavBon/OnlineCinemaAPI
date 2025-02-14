from typing import Optional, cast

from fastapi import status, HTTPException
from pydantic import HttpUrl
from sqlalchemy.orm import Session

from database.models.accounts import UserModel, GenderEnum, UserProfileModel
from exceptions import S3FileUploadError
from schemas.profiles import ProfileCreateSchema, ProfileResponseSchema
from storages import S3StorageInterface


def create_user_profile(
    user: UserModel, db: Session, s3_client: S3StorageInterface, profile_data: ProfileCreateSchema
) -> ProfileResponseSchema:
    existing_profile = db.query(UserProfileModel).filter_by(user_id=user.id).first()

    if existing_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has a profile.")

    avatar_bytes = profile_data.avatar.file.read()
    avatar_key = f"avatars/{user.id}_{profile_data.avatar.filename}"

    try:
        s3_client.upload_file(file_name=avatar_key, file_data=avatar_bytes)
        avatar_url = s3_client.get_file_url(avatar_key)
    except S3FileUploadError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload avatar. Please try again later."
        )

    new_profile = UserProfileModel(
        user_id=user.id,
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        gender=cast(GenderEnum, profile_data.gender),
        date_of_birth=profile_data.date_of_birth,
        info=profile_data.info,
        avatar=avatar_url,
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return ProfileResponseSchema(
        id=new_profile.id,
        user_id=new_profile.user_id,
        first_name=new_profile.first_name,
        last_name=new_profile.last_name,
        gender=new_profile.gender,
        date_of_birth=new_profile.date_of_birth,
        info=new_profile.info,
        avatar=cast(HttpUrl, avatar_url),
    )
