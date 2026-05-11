"""
Tools — инструменты системы, доступные пользователям в разделе Tools.
"""
from sqlalchemy import Integer, String, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class Tool(Base, TimestampMixin):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(8), default="🔧")
    category: Mapped[str] = mapped_column(String(32), default="general")
    # search / analyze / export / utility
    tool_type: Mapped[str] = mapped_column(String(32), default="search")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    min_plan: Mapped[str] = mapped_column(String(16), default="free")   # free/premium/enterprise
    token_cost: Mapped[int] = mapped_column(Integer, default=5)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


# Предустановленные инструменты (seed data)
DEFAULT_TOOLS = [
    {
        "slug": "tg_user_search",
        "name": "Telegram User Search",
        "description": "Поиск пользователей Telegram по username, ID, имени или телефону",
        "icon": "🔍",
        "category": "telegram",
        "tool_type": "search",
        "min_plan": "free",
        "token_cost": 5,
        "sort_order": 1,
    },
    {
        "slug": "tg_group_scan",
        "name": "Group/Channel Scanner",
        "description": "Анализ участников публичных групп и каналов",
        "icon": "📡",
        "category": "telegram",
        "tool_type": "analyze",
        "min_plan": "premium",
        "token_cost": 20,
        "sort_order": 2,
    },
    {
        "slug": "email_lookup",
        "name": "Email Lookup",
        "description": "Поиск по email в подключённых базах данных",
        "icon": "📧",
        "category": "lookup",
        "tool_type": "search",
        "min_plan": "free",
        "token_cost": 5,
        "sort_order": 3,
    },
    {
        "slug": "phone_lookup",
        "name": "Phone Lookup",
        "description": "Поиск по номеру телефона",
        "icon": "📞",
        "category": "lookup",
        "tool_type": "search",
        "min_plan": "free",
        "token_cost": 5,
        "sort_order": 4,
    },
    {
        "slug": "cross_search",
        "name": "Cross-Database Search",
        "description": "Поиск совпадений сразу во всех подключённых базах данных",
        "icon": "🌐",
        "category": "search",
        "tool_type": "search",
        "min_plan": "premium",
        "token_cost": 15,
        "sort_order": 5,
    },
    {
        "slug": "ai_profile_builder",
        "name": "AI Profile Builder",
        "description": "Построение профиля сущности на основе всех найденных данных",
        "icon": "🤖",
        "category": "ai",
        "tool_type": "analyze",
        "min_plan": "premium",
        "token_cost": 30,
        "sort_order": 6,
    },
    {
        "slug": "connection_mapper",
        "name": "Connection Mapper",
        "description": "Карта связей между найденными сущностями",
        "icon": "🕸️",
        "category": "ai",
        "tool_type": "analyze",
        "min_plan": "enterprise",
        "token_cost": 50,
        "sort_order": 7,
    },
    {
        "slug": "export_pdf",
        "name": "Export to PDF",
        "description": "Экспорт результатов поиска в PDF-отчёт",
        "icon": "📄",
        "category": "export",
        "tool_type": "export",
        "min_plan": "premium",
        "token_cost": 10,
        "sort_order": 8,
    },
    {
        "slug": "export_json",
        "name": "Export to JSON",
        "description": "Экспорт данных в JSON формат",
        "icon": "💾",
        "category": "export",
        "tool_type": "export",
        "min_plan": "free",
        "token_cost": 2,
        "sort_order": 9,
    },
    {
        "slug": "file_scanner",
        "name": "File Scanner",
        "description": "Поиск совпадений в загруженных файлах (CSV, JSON, TXT)",
        "icon": "📂",
        "category": "search",
        "tool_type": "search",
        "min_plan": "free",
        "token_cost": 8,
        "sort_order": 10,
    },
]
