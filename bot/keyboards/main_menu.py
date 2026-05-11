from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🤖 AI Поиск",        callback_data="menu:ai_analyze"),
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск данных",     callback_data="menu:search"),
        InlineKeyboardButton(text="✈️ TelegramUsers",    callback_data="menu:tg_users"),
    )
    builder.row(
        InlineKeyboardButton(text="🗄️ Базы данных",      callback_data="menu:databases"),
        InlineKeyboardButton(text="🛠️ Инструменты",      callback_data="menu:tools"),
    )
    builder.row(
        InlineKeyboardButton(text="📜 История",          callback_data="menu:history"),
        InlineKeyboardButton(text="👤 Профиль",          callback_data="menu:profile"),
    )
    builder.row(
        InlineKeyboardButton(text="💎 Подписка",         callback_data="menu:subscription"),
        InlineKeyboardButton(text="🎮 Режим работы",     callback_data="menu:mode"),
    )
    builder.row(
        InlineKeyboardButton(text="🪙 Баланс токенов",   callback_data="menu:balance"),
        InlineKeyboardButton(text="⚙️ Настройки",        callback_data="menu:settings"),
    )
    return builder.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def back_kb(callback: str = "menu:main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=callback))
    return builder.as_markup()
