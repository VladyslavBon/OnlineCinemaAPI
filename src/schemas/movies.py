from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, Field


class CommentCreateSchema(BaseModel):
    comment: str

    model_config = {"from_attributes": True}


class CommentSchema(BaseModel):
    id: int
    user_id: int
    comment: str
    parent_id: int | None = None
    replies: list[int] | None = None

    model_config = {"from_attributes": True}

    @field_validator("replies", mode="before")
    @classmethod
    def extract_reply_ids(cls, value):
        if isinstance(value, list):
            return [reply.id for reply in value]
        return None


class CommentResponseSchema(BaseModel):
    id: int
    comment: str
    parent_id: int | None = None
    user_id: int

    model_config = {"from_attributes": True}


class GenreSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class StarSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class DirectorSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class CertificationSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class MovieBaseSchema(BaseModel):
    uuid: str | None = None
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    rating: float
    meta_score: float | None = None
    gross: float | None = None
    description: str
    price: float
    likes: int
    dislikes: int

    model_config = {"from_attributes": True}

    @field_validator("year")
    @classmethod
    def validate_year(cls, value):
        current_year = datetime.now().year
        if value > current_year + 1:
            raise ValueError(f"The year in 'year' cannot be greater than {current_year + 1}.")
        return value


class MovieDetailSchema(MovieBaseSchema):
    id: int
    genres: list[GenreSchema]
    stars: list[StarSchema]
    directors: list[DirectorSchema]
    certification: CertificationSchema
    comments: list[CommentSchema]

    model_config = {"from_attributes": True}


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    price: float
    genres: list[GenreSchema]
    stars: list[StarSchema]
    directors: list[DirectorSchema]

    model_config = {"from_attributes": True}


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int

    model_config = {"from_attributes": True}


class MovieCreateSchema(BaseModel):
    name: str
    year: int
    time: int
    imdb: float = Field(..., ge=0, le=10)
    votes: int
    meta_score: float | None = None
    gross: float | None = None
    description: str
    price: float = Field(..., ge=0)
    genres: list[str]
    stars: list[str]
    directors: list[str]
    certification: str

    @field_validator("genres", "stars", "directors", mode="before")
    @classmethod
    def normalize_list_fields(cls, value: list[str]) -> list[str]:
        return [item.title() for item in value]


class MovieUpdateSchema(BaseModel):
    name: str | None = None
    year: int | None = None
    time: int | None = None
    imdb: float | None = Field(None, ge=0, le=10)
    votes: int | None = None
    meta_score: float | None = None
    gross: float | None = None
    description: str | None = None
    price: float | None = Field(None, ge=0)

    model_config = {"from_attributes": True}


class FavoriteSchema(BaseModel):
    id: int
    favorite: bool

    model_config = {"from_attributes": True}
