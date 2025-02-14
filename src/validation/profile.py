import re
from datetime import date
from io import BytesIO

from PIL import Image
from fastapi import UploadFile

from database.models.accounts import GenderEnum


def validate_name(name: str):
    if re.search(r"^[A-Za-z]*$", name) is None:
        raise ValueError(f"{name} contains non-english letters")


def validate_image(avatar: UploadFile) -> None:
    supported_image_formats = ["JPG", "JPEG", "PNG"]
    max_file_size = 1 * 1024 * 1024

    contents = avatar.file.read()
    if len(contents) > max_file_size:
        raise ValueError("Image size exceeds 1 MB")

    try:
        image = Image.open(BytesIO(contents))
        avatar.file.seek(0)
        image_format = image.format
        if image_format not in supported_image_formats:
            raise ValueError(f"Unsupported image format: {image_format}. Use one of next: {supported_image_formats}")
    except IOError:
        raise ValueError("Invalid image format")


def validate_gender(gender: str) -> None:
    if gender not in GenderEnum.__members__.values():
        raise ValueError(f"Gender must be one of: {', '.join(gender.value for gender in GenderEnum)}")


def validate_birth_date(birth_date: date) -> None:
    if birth_date.year < 1900:
        raise ValueError("Invalid birth date - year must be greater than 1900.")

    age = (date.today() - birth_date).days // 365
    if age < 18:
        raise ValueError("You must be at least 18 years old to register.")
