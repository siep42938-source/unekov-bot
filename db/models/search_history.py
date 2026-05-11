from sqlalchemy import BigInteger, Integer, String, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class SearchHistory(Base, TimestampMixin):
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    query: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(16))
    tokens_spent: Mapped[int] = mapped_column(Integer, default=0)
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="completed")  # completed/failed/pending

    user: Mapped["User"] = relationship(back_populates="search_history")
