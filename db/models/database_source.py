"""
DatabaseSource — подключённые базы данных / источники данных (раздел BD).
"""
from sqlalchemy import Integer, String, Text, Boolean, JSON, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class DatabaseSource(Base, TimestampMixin):
    __tablename__ = "database_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(8), default="🗄️")
    source_type: Mapped[str] = mapped_column(String(32))
    # types: internal_pg / csv_file / json_file / external_api / telegram_export
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    connection_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    access_level: Mapped[str] = mapped_column(String(16), default="free")
    added_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    last_synced_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)


# Предустановленные источники
DEFAULT_SOURCES = [
    {
        "name": "Telegram Users DB",
        "slug": "telegram_users",
        "description": "База данных пользователей Telegram из публичных источников",
        "icon": "✈️",
        "source_type": "internal_pg",
        "access_level": "free",
    },
    {
        "name": "Email Database",
        "slug": "email_db",
        "description": "База email-адресов из разрешённых источников",
        "icon": "📧",
        "source_type": "internal_pg",
        "access_level": "free",
    },
    {
        "name": "Phone Database",
        "slug": "phone_db",
        "description": "База телефонных номеров",
        "icon": "📞",
        "source_type": "internal_pg",
        "access_level": "premium",
    },
    {
        "name": "CSV Files",
        "slug": "csv_files",
        "description": "Загруженные CSV файлы для поиска",
        "icon": "📂",
        "source_type": "csv_file",
        "access_level": "free",
    },
]
