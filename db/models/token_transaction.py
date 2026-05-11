from sqlalchemy import BigInteger, Integer, String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class TokenTransaction(Base, TimestampMixin):
    __tablename__ = "token_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # positive = credit, negative = debit
    balance_after: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(64))  # search/daily_bonus/purchase/admin
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)

    user: Mapped["User"] = relationship(back_populates="token_transactions")
