"""
IndexedRecord — универсальная таблица для всех проиндексированных данных
из bif BD/, Telegram Users/, Telegram_Chats_2022_63kk/ и загруженных файлов.
"""
from sqlalchemy import Integer, String, Text, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class IndexedRecord(Base, TimestampMixin):
    __tablename__ = "indexed_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(String(256), index=True)
    source_tag: Mapped[str] = mapped_column(String(64), index=True)
    # Нормализованные поля для быстрого поиска
    tg_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    # Сырая строка для full-text search
    raw: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        Index("ix_indexed_records_username_lower", "username"),
        Index("ix_indexed_records_phone", "phone"),
        Index("ix_indexed_records_email", "email"),
        Index("ix_indexed_records_tg_id", "tg_id"),
        # Full-text search index (PostgreSQL)
        Index(
            "ix_indexed_records_fts",
            "raw",
            postgresql_using="gin",
            postgresql_ops={"raw": "gin_trgm_ops"},
        ),
    )
