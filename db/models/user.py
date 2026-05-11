from sqlalchemy import BigInteger, String, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram ID
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language_code: Mapped[str] = mapped_column(String(8), default="en")

    # Статусы
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Роль: user / moderator / admin / owner
    role: Mapped[str] = mapped_column(String(16), default="user")

    # Токены и статистика
    token_balance: Mapped[int] = mapped_column(Integer, default=0)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_spent: Mapped[int] = mapped_column(Integer, default=0)

    # Активность
    last_active: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_daily_bonus: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Режим работы
    work_mode: Mapped[str] = mapped_column(String(16), default="standard")

    # Relationships
    subscription: Mapped["Subscription"] = relationship(back_populates="user", uselist=False)
    search_history: Mapped[list["SearchHistory"]] = relationship(back_populates="user")
    token_transactions: Mapped[list["TokenTransaction"]] = relationship(back_populates="user")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")

    # Роли
    ROLES = {
        "user":      {"label": "👤 User",      "color": "⚪"},
        "vip":       {"label": "⭐ VIP",        "color": "🟡"},
        "moderator": {"label": "🛡️ Moderator",  "color": "🔵"},
        "admin":     {"label": "⚡ Admin",      "color": "🔴"},
        "owner":     {"label": "👑 Owner",      "color": "🟣"},
    }

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.first_name

    @property
    def role_label(self) -> str:
        return self.ROLES.get(self.role, {}).get("label", "👤 User")

    @property
    def role_color(self) -> str:
        return self.ROLES.get(self.role, {}).get("color", "⚪")

    @property
    def is_staff(self) -> bool:
        return self.role in ("moderator", "admin", "owner") or self.is_admin
