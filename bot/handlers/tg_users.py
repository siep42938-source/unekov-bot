import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from db.database import AsyncSessionLocal
from db.models import TelegramUser
from db.repositories import UserRepository
from core.search.universal_search import UniversalSearch
from bot.keyboards import tg_users_menu_kb, tg_user_result_kb, cancel_kb, main_menu_kb
from bot import ui_texts as T

router = Router()
logger = logging.getLogger(__name__)


class TGUserState(StatesGroup):
    waiting_query = State()


@router.callback_query(F.data == "menu:tg_users")
async def cb_tg_users_menu(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(TelegramUser))
        count = result.scalar() or 0

    text = T.TG_USERS_MENU.format(count=f"{count:,}")
    await call.message.edit_text(text, reply_markup=tg_users_menu_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("tgu:search:"))
async def cb_tgu_search(call: CallbackQuery, state: FSMContext):
    search_type = call.data.split("tgu:search:")[1]
    hints = {
        "username": "✏️ Введите @username или username без @:",
        "id":       "✏️ Введите Telegram ID (число):",
        "phone":    "✏️ Введите номер телефона:",
        "name":     "✏️ Введите имя или фамилию:",
    }
    await state.set_state(TGUserState.waiting_query)
    await state.update_data(search_type=search_type)
    await call.message.edit_text(
        hints.get(search_type, "✏️ Введите запрос:"),
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(TGUserState.waiting_query)
async def process_tgu_query(message: Message, state: FSMContext):
    data = await state.get_data()
    search_type = data.get("search_type", "username")
    query = message.text.strip().lstrip("@")
    await state.clear()

    if not query:
        await message.answer("❌ Пустой запрос.", reply_markup=tg_users_menu_kb())
        return

    progress = await message.answer("⏳ <b>Поиск в TelegramUsers DB...</b>", parse_mode="HTML")

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(message.from_user.id)
        mode = user.work_mode if user else "standard"
        lang = user.language_code or "ru"

        # Direct DB search
        try:
            if search_type == "id":
                tg_id = int(query)
                result = await session.execute(
                    select(TelegramUser).where(TelegramUser.tg_id == tg_id).limit(10)
                )
            elif search_type == "phone":
                result = await session.execute(
                    select(TelegramUser).where(
                        TelegramUser.phone.contains(query)
                    ).limit(10)
                )
            elif search_type == "username":
                result = await session.execute(
                    select(TelegramUser).where(
                        func.lower(TelegramUser.username).contains(query.lower())
                    ).limit(10)
                )
            else:  # name
                result = await session.execute(
                    select(TelegramUser).where(
                        func.lower(TelegramUser.first_name).contains(query.lower()) |
                        func.lower(TelegramUser.last_name).contains(query.lower())
                    ).limit(10)
                )

            rows = result.scalars().all()
        except ValueError:
            await progress.edit_text("❌ Неверный формат ID.", reply_markup=tg_users_menu_kb())
            return

    if not rows:
        await progress.edit_text(
            f"❌ По запросу <code>{query}</code> ничего не найдено в TelegramUsers DB.",
            reply_markup=tg_user_result_kb(),
            parse_mode="HTML",
        )
        return

    lines = [f"✈️ <b>TelegramUsers</b> — найдено <b>{len(rows)}</b> записей\n"]
    lines.append(f"🔍 Запрос: <code>{query}</code>\n")

    first_tg_id = None
    for i, u in enumerate(rows, 1):
        if i == 1:
            first_tg_id = u.tg_id
        parts = [f"<b>{i}. {u.display}</b>"]
        if u.tg_id:
            parts.append(f"  🆔 ID: <code>{u.tg_id}</code>")
        if u.phone:
            parts.append(f"  📞 {u.phone}")
        if u.bio:
            parts.append(f"  📝 {u.bio[:80]}...")
        if u.source:
            parts.append(f"  📡 Источник: {u.source}")
        if u.is_premium:
            parts.append("  💎 Premium")
        lines.append("\n".join(parts))
        lines.append("")

    await progress.edit_text(
        "\n".join(lines),
        reply_markup=tg_user_result_kb(first_tg_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "tgu:stats")
async def cb_tgu_stats(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count()).select_from(TelegramUser))).scalar() or 0
        with_username = (await session.execute(
            select(func.count()).select_from(TelegramUser).where(TelegramUser.username.isnot(None))
        )).scalar() or 0
        with_phone = (await session.execute(
            select(func.count()).select_from(TelegramUser).where(TelegramUser.phone.isnot(None))
        )).scalar() or 0
        premium = (await session.execute(
            select(func.count()).select_from(TelegramUser).where(TelegramUser.is_premium == True)
        )).scalar() or 0

    text = (
        "📊 <b>Статистика TelegramUsers DB</b>\n\n"
        f"📦 Всего записей: <b>{total:,}</b>\n"
        f"👤 С username: <b>{with_username:,}</b>\n"
        f"📞 С телефоном: <b>{with_phone:,}</b>\n"
        f"💎 Premium: <b>{premium:,}</b>"
    )
    await call.message.edit_text(text, reply_markup=tg_users_menu_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("tgu:ai_profile:"))
async def cb_tgu_ai_profile(call: CallbackQuery):
    tg_id = int(call.data.split("tgu:ai_profile:")[1])
    await call.answer("⏳ Строю AI профиль...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.tg_id == tg_id)
        )
        rows = result.scalars().all()
        if not rows:
            await call.message.edit_text("❌ Пользователь не найден.", reply_markup=tg_users_menu_kb())
            return

        from core.ai.openai_service import analyze_search_results
        data = [
            {
                "tg_id": r.tg_id, "username": r.username,
                "first_name": r.first_name, "last_name": r.last_name,
                "phone": r.phone, "bio": r.bio, "source": r.source,
            }
            for r in rows
        ]
        ai = await analyze_search_results(
            query=f"Telegram user ID {tg_id}",
            results=data,
            mode="deep",
            language="ru",
        )

    text = (
        f"🤖 <b>AI Профиль</b> — TG ID: <code>{tg_id}</code>\n\n"
        f"{ai.get('summary', 'Нет данных')}\n\n"
        f"📊 Confidence: <b>{int(ai.get('confidence', 0) * 100)}%</b>\n"
        f"⚠️ Risk: <b>{ai.get('risk_level', 'none').upper()}</b>"
    )
    await call.message.edit_text(text, reply_markup=tg_user_result_kb(tg_id), parse_mode="HTML")
