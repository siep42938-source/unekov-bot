from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db.models.database_source import DEFAULT_SOURCES


def databases_menu_kb(user_plan: str = "free") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    plan_order = {"free": 0, "premium": 1, "enterprise": 2}
    user_level = plan_order.get(user_plan, 0)

    for src in DEFAULT_SOURCES:
        src_level = plan_order.get(src["access_level"], 0)
        lock = "🔒 " if src_level > user_level else "✅ "
        builder.row(
            InlineKeyboardButton(
                text=f"{src['icon']} {lock}{src['name']}",
                callback_data=f"db:view:{src['slug']}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="📤 Загрузить файл",    callback_data="db:upload"),
        InlineKeyboardButton(text="🔄 Обновить",          callback_data="db:refresh"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main"))
    return builder.as_markup()


def db_detail_kb(slug: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск в этой БД",  callback_data=f"db:search:{slug}"),
        InlineKeyboardButton(text="📊 Статистика",        callback_data=f"db:stats:{slug}"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Базы данных", callback_data="menu:databases"))
    return builder.as_markup()
