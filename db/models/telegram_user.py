"""
TelegramUsers — раздел для хранения и поиска данных о Telegram-пользователях
из подключённых источников (публичные группы, каналы, разрешённые базы).
"""
from sqlalchemy import BigInteger, String, Integer, Boolean, Text, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class TelegramUser(Base, TimestampMixin):
    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)   # откуда данные
    source_group: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seen_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_tg_users_username_lower", "username"),
        Index("ix_tg_users_tg_id", "tg_id"),
    )

    @property
    def display(self) -> str:
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        name = " ".join(parts) or "Unknown"
        if self.username:
            return f"{name} (@{self.username})"
        return name
