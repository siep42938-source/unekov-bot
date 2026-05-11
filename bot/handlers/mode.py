from aiogram import Router, F
from aiogram.types import CallbackQuery
from db.database import AsyncSessionLocal
from db.repositories import UserRepository
from core.tokens import PLAN_MODE_ACCESS
from bot.keyboards import mode_select_kb, main_menu_kb
from bot import ui_texts as T

router = Router()

MODE_NAMES = {
    "lite":     "⚡ Lite",
    "standard": "🔵 Standard",
    "deep":     "🟣 Deep Scan",
    "ultra":    "🔴 Ultra AI",
}


@router.callback_query(F.data == "menu:mode")
async def cb_mode_menu(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        mode = user.work_mode if user else "standard"
        plan = user.subscription.plan if user and user.subscription else "free"

    text = T.MODE_MENU.format(current_mode=MODE_NAMES.get(mode, mode.upper()))
    await call.message.edit_text(text, reply_markup=mode_select_kb(mode, plan), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("mode:set:"))
async def cb_mode_set(call: CallbackQuery):
    mode = call.data.replace("mode:set:", "")
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        plan = user.subscription.plan if user and user.subscription else "free"
        allowed = PLAN_MODE_ACCESS.get(plan, ["lite", "standard"])

        if mode not in allowed:
            await call.answer(f"🔒 Режим недоступен на тарифе {plan.upper()}", show_alert=True)
            return

        await repo.update_mode(call.from_user.id, mode)
        await session.commit()

    await call.answer(f"✅ Режим: {MODE_NAMES.get(mode, mode)}", show_alert=False)
    # Refresh menu
    text = T.MODE_MENU.format(current_mode=MODE_NAMES.get(mode, mode.upper()))
    await call.message.edit_text(text, reply_markup=mode_select_kb(mode, plan), parse_mode="HTML")


@router.callback_query(F.data.startswith("mode:locked:"))
async def cb_mode_locked(call: CallbackQuery):
    mode = call.data.replace("mode:locked:", "")
    plan_needed = {
        "deep":  "Premium",
        "ultra": "Enterprise",
    }
    needed = plan_needed.get(mode, "Premium")
    await call.answer(f"🔒 Режим {mode.upper()} доступен с тарифа {needed}", show_alert=True)
