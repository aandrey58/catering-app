from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    note: Mapped[str] = mapped_column(String(512), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class DaySelection(Base):
    __tablename__ = "day_selections"
    __table_args__ = (UniqueConstraint("login", "day", name="uq_login_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(128), index=True)
    day: Mapped[str] = mapped_column(String(8))
    breakfast: Mapped[str] = mapped_column(String(512), default="")
    soup: Mapped[str] = mapped_column(String(512), default="")
    hot: Mapped[str] = mapped_column(String(512), default="")
    side: Mapped[str] = mapped_column(String(512), default="")
    salad: Mapped[str] = mapped_column(String(512), default="")
    dessert: Mapped[str] = mapped_column(String(512), default="")


class FeedbackRow(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    rating: Mapped[int] = mapped_column(Integer)
    feedback_text: Mapped[str] = mapped_column(Text, default="")
