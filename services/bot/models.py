from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Integer, Text, TIMESTAMP, Boolean, ARRAY, Float, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY


class Base(DeclarativeBase):
    pass


class BotMessage(Base):
    __tablename__ = "bot_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    state: Mapped[str] = mapped_column(Text, default="ACTIVE")
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="en")
    username: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    username_updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    intro_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intro_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intro_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intro_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intro_linkedin: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intro_hobbies_drivers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intro_skills: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intro_birthday: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    field_of_activity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vector_description: Mapped[Optional[list[float]]] = mapped_column(ARRAY(item_type=Float), nullable=True)
    vector_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    finishedonboarding: Mapped[bool] = mapped_column(Boolean, default=False)
    user_telegram_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    matches_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_birthday_greeting_sent: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_1_id: Mapped[int] = mapped_column(BigInteger)
    user_2_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text, default="NEW")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    last_updated: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, default="scheduled")  # 'scheduled', 'sent', 'cancelled'
    recipient_type: Mapped[str] = mapped_column(Text, default="all")  # 'all', 'user', 'group', 'user_group'
    recipient_ids: Mapped[Optional[list[int]]] = mapped_column(PG_ARRAY(BigInteger), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


