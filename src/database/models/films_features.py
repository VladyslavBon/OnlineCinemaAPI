from enum import Enum
from typing import Optional

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Boolean, Integer, ForeignKey, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship

from database.models.base import Base


class ReactionEnum(str, Enum):
    LIKE = "Like"
    DISLIKE = "Dislike"


class ReactionModel(Base):
    __tablename__ = "reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    reaction: Mapped[ReactionEnum] = mapped_column(SQLAlchemyEnum(ReactionEnum), nullable=True)

    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="reactions")

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="reactions")


class CommentModel(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    comment: Mapped[str] = mapped_column(Text, nullable=True)

    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("comments.id"), nullable=True)
    parent: Mapped[Optional["CommentModel"]] = relationship("CommentModel", remote_side=[id], backref="replies")

    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="comments")

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="comments")


class FavoriteModel(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    favorite: Mapped[bool] = mapped_column(Boolean, default=False)

    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="favorites")

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="favorites")
