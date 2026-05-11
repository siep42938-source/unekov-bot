from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.tokens import MODE_COSTS, PLAN_MODE_ACCESS

MODE_INFO = {
    "lite":     ("⚡", "Lite",     "Быстрый, минимум токенов"),
    "standard": ("🔵", "Standard", "Баланс скорости и качества"),
    "deep":     ("🟣", "Deep Scan","Расширенный анализ"),
    "ultra":    ("🔴", "Ultra AI", "Multi-step reasoning, максимум"),
}


def mode_select_kb(current_mode: str, user_plan: str = "free") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    allowed = PLAN_MODE_ACCESS.get(user_plan, ["lite", "standard"])

    for mode, (icon, label, desc) in MODE_INFO.items():
        cost = MODE_COSTS[mode]
        locked = mode not in allowed
        active = "✓ " if mode == current_mode else ""
        lock_icon = "🔒" if locked else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{icon} {active}{label} {lock_icon} — {cost}🪙",
                callback_data=f"mode:set:{mode}" if not locked else f"mode:locked:{mode}",
            )
        )

    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main"))
    return builder.as_markup()
