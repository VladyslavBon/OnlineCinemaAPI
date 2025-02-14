from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from config import get_s3_storage_client
from database import get_db
from database.models.accounts import UserModel
from schemas.profiles import ProfileCreateSchema, ProfileResponseSchema
from services import get_current_user, create_user_profile
from storages import S3StorageInterface


router = APIRouter()


@router.post(
    "/users/profile/",
    response_model=ProfileResponseSchema,
    summary="Create user profile",
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client),
    profile_data: ProfileCreateSchema = Depends(ProfileCreateSchema.from_form),
):
    return create_user_profile(user=user, db=db, s3_client=s3_client, profile_data=profile_data)
