from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def search_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔎 Новый поиск",         callback_data="search:new"),
    )
    builder.row(
        InlineKeyboardButton(text="👤 По имени/username",   callback_data="search:by_name"),
        InlineKeyboardButton(text="📧 По email",            callback_data="search:by_email"),
    )
    builder.row(
        InlineKeyboardButton(text="📞 По телефону",         callback_data="search:by_phone"),
        InlineKeyboardButton(text="🆔 По Telegram ID",      callback_data="search:by_tgid"),
    )
    builder.row(
        InlineKeyboardButton(text="🌐 Кросс-поиск (все БД)", callback_data="search:cross"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад",               callback_data="menu:main"),
    )
    return builder.as_markup()


def search_result_kb(history_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📄 Экспорт JSON",  callback_data=f"export:json:{history_id}"),
        InlineKeyboardButton(text="📑 Экспорт PDF",   callback_data=f"export:pdf:{history_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 AI Анализ",     callback_data=f"analyze:history:{history_id}"),
        InlineKeyboardButton(text="🔍 Новый поиск",   callback_data="search:new"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Главное меню",  callback_data="menu:main"),
    )
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="menu:main"))
    return builder.as_markup()
