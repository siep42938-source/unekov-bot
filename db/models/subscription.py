from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .base import Base, TimestampMixin


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True)
    plan: Mapped[str] = mapped_column(String(16), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    monthly_tokens: Mapped[int] = mapped_column(Integer, default=100)
    tokens_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    max_mode: Mapped[str] = mapped_column(String(16), default="standard")
    # Кто выдал подписку
    granted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    grant_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscription")

    PLANS = {
        "free":       {"monthly_tokens": 100,   "max_mode": "standard", "price": 0,     "label": "⚪ Free"},
        "premium":    {"monthly_tokens": 2000,  "max_mode": "deep",     "price": 9.99,  "label": "🔵 Premium"},
        "enterprise": {"monthly_tokens": 10000, "max_mode": "ultra",    "price": 49.99, "label": "🔴 Enterprise"},
        "vip":        {"monthly_tokens": 5000,  "max_mode": "ultra",    "price": 0,     "label": "⭐ VIP (выдано)"},
    }

    @property
    def plan_label(self) -> str:
        return self.PLANS.get(self.plan, {}).get("label", "⚪ Free")

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        from datetime import timezone
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp
