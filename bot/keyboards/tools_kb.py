from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db.models.tool import DEFAULT_TOOLS


def tools_menu_kb(user_plan: str = "free") -> InlineKeyboardMarkup:
    """Клавиатура раздела Tools с доступными инструментами."""
    builder = InlineKeyboardBuilder()

    plan_order = {"free": 0, "premium": 1, "enterprise": 2}
    user_level = plan_order.get(user_plan, 0)

    for tool in sorted(DEFAULT_TOOLS, key=lambda t: t["sort_order"]):
        tool_level = plan_order.get(tool["min_plan"], 0)
        lock = "🔒 " if tool_level > user_level else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{tool['icon']} {lock}{tool['name']} [{tool['token_cost']}🪙]",
                callback_data=f"tool:{tool['slug']}",
            )
        )

    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main"))
    return builder.as_markup()


def tool_action_kb(slug: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="▶️ Запустить",    callback_data=f"tool:run:{slug}"),
        InlineKeyboardButton(text="ℹ️ Подробнее",    callback_data=f"tool:info:{slug}"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Инструменты", callback_data="menu:tools"))
    return builder.as_markup()
