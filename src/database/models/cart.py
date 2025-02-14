import datetime

from sqlalchemy import UniqueConstraint, func, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.accounts import UserModel
from database.models.base import Base
from database.models.movies import MovieModel


class CartModel(Base):
    __tablename__ = "carts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel")
    cart_items: Mapped[list["CartItemModel"]] = relationship(
        "CartItemModel", back_populates="cart", cascade="all, delete-orphan"
    )
    order: Mapped["OrderModel"] = relationship(
        "OrderModel", back_populates="cart", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<id: {self.id}, user_id: {self.user_id}, cart_items: {self.cart_items}>"


class CartItemModel(Base):
    __tablename__ = "cart_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(Integer, ForeignKey("carts.id"), nullable=False)
    cart: Mapped["CartModel"] = relationship("CartModel", back_populates="cart_items")
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    movie: Mapped["MovieModel"] = relationship("MovieModel")
    added_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.current_date())

    __table_args__ = (UniqueConstraint("cart_id", "movie_id", name="unique_cart_movie"),)
