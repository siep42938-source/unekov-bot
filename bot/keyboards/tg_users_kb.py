from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def tg_users_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск по username",  callback_data="tgu:search:username"),
        InlineKeyboardButton(text="🆔 Поиск по ID",        callback_data="tgu:search:id"),
    )
    builder.row(
        InlineKeyboardButton(text="📞 Поиск по телефону",  callback_data="tgu:search:phone"),
        InlineKeyboardButton(text="👤 Поиск по имени",     callback_data="tgu:search:name"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика БД",      callback_data="tgu:stats"),
        InlineKeyboardButton(text="📤 Загрузить файл",     callback_data="tgu:upload"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main"))
    return builder.as_markup()


def tg_user_result_kb(tg_id: int | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if tg_id:
        builder.row(
            InlineKeyboardButton(text="🤖 AI Профиль",    callback_data=f"tgu:ai_profile:{tg_id}"),
            InlineKeyboardButton(text="🕸️ Связи",         callback_data=f"tgu:connections:{tg_id}"),
        )
    builder.row(
        InlineKeyboardButton(text="🔍 Новый поиск",       callback_data="tgu:search:username"),
        InlineKeyboardButton(text="◀️ Назад",             callback_data="menu:tg_users"),
    )
    return builder.as_markup()
