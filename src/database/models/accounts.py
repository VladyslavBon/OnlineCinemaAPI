import enum
from datetime import datetime, timezone, timedelta, date
from typing import Optional

from sqlalchemy import Integer, String, Boolean, DateTime, func, ForeignKey, Enum, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from database.models.base import Base
from database.validators import accounts as validators
from security.passwords import hash_password, verify_password
from security.token_generator import generate_secure_token


class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"


class BaseTokenModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String(63),
        unique=True,
        nullable=False,
        default=generate_secure_token,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1),
    )


class ActivationTokenModel(BaseTokenModel):
    __tablename__ = "activation_tokens"

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="activation_token",
    )

    def __repr__(self):
        return f"<ActivationTokenModel(id={self.id}, " f"token={self.token}, expires_at={self.expires_at})>"


class PasswordResetTokenModel(BaseTokenModel):
    __tablename__ = "password_reset_tokens"

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="password_reset_token",
    )

    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, " f"token={self.token}, expires_at={self.expires_at})>"


class RefreshTokenModel(BaseTokenModel):
    __tablename__ = "refresh_tokens"

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="refresh_token",
    )
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        default=generate_secure_token,
    )

    @classmethod
    def create(cls, user_id: int, days_valid: int, token: str) -> "RefreshTokenModel":
        expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        return cls(user_id=user_id, expires_at=expires_at, token=token)

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


class UserGroupModel(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum),
        unique=True,
        nullable=False,
    )

    users: Mapped[list["UserModel"]] = relationship("UserModel", back_populates="group")

    def __repr__(self):
        return f"<UserGroupModel(id={self.id}, name={self.name})>"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # reactions, likes and favorites for every user
    reactions: Mapped[list["ReactionModel"]] = relationship("ReactionModel", backref="user_reactions", uselist=False)
    comments: Mapped[list["CommentModel"]] = relationship("CommentModel", backref="user_comments", uselist=False)
    favorites: Mapped[list["FavoriteModel"]] = relationship("FavoriteModel", backref="user_favorites", uselist=False)

    _hashed_password: Mapped[str] = mapped_column(
        "hashed_password",
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False)

    group: Mapped[UserGroupModel] = relationship(
        UserGroupModel,
        back_populates="users",
    )
    profile: Mapped[Optional["UserProfileModel"]] = relationship(
        "UserProfileModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    activation_token: Mapped[Optional[ActivationTokenModel]] = relationship(
        ActivationTokenModel,
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_token: Mapped[Optional[PasswordResetTokenModel]] = relationship(
        PasswordResetTokenModel,
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_token: Mapped[Optional[RefreshTokenModel]] = relationship(
        RefreshTokenModel,
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<UserModel(id={self.id}, email={self.email}, is_active={self.is_active})>"

    def has_group(self, group_name: UserGroupEnum) -> bool:
        return self.group.name == group_name

    @classmethod
    def create(cls, email: str, raw_password: str, group_id: int) -> "UserModel":
        """
        Factory method to create a new UserModel instance.

        This method simplifies the creation of a new user by handling
        password hashing and setting required attributes.
        """
        user = cls(email=email, group_id=group_id)
        user.password = raw_password
        return user

    @property
    def password(self) -> None:
        raise AttributeError("Password is write-only. Use the setter to set the password.")

    @password.setter
    def password(self, raw_password: str) -> None:
        """
        Set the user's password after validating its strength and hashing it.
        """
        validators.validate_password_strength(raw_password)
        self._hashed_password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        """
        Verify the provided password against the stored hashed password.
        """
        return verify_password(raw_password, self._hashed_password)

    @validates("email")
    def validate_email(self, key, value):
        return validators.validate_email(value.lower())


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(127))
    last_name: Mapped[Optional[str]] = mapped_column(String(127))
    avatar: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional[GenderEnum]] = mapped_column(Enum(GenderEnum))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    info: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped[UserModel] = relationship(UserModel, back_populates="profile")

    def __repr__(self):
        return (
            f"<UserProfileModel(id={self.id}, first_name={self.first_name}, last_name={self.last_name}, "
            f"gender={self.gender}, date_of_birth={self.date_of_birth})>"
        )
