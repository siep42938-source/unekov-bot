import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy import select, desc
from db.database import AsyncSessionLocal
from db.repositories import UserRepository, SearchRepository
from db.models import TokenTransaction
from bot.keyboards import back_to_main_kb, main_menu_kb
from datetime import datetime, timezone

router = Router()
logger = logging.getLogger(__name__)


def profile_kb(user_id: int, is_admin: bool = False) -> object:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Дневной бонус",  callback_data="profile:daily_bonus"),
        InlineKeyboardButton(text="📜 История",        callback_data="menu:history"),
    )
    builder.row(
        InlineKeyboardButton(text="🪙 Баланс",         callback_data="menu:balance"),
        InlineKeyboardButton(text="💎 Подписка",       callback_data="menu:subscription"),
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⚡ Админ-панель", callback_data="admin:panel"),
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main"))
    return builder.as_markup()


@router.callback_query(F.data == "menu:profile")
async def cb_profile(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        if not user:
            await call.answer("Ошибка. Напишите /start")
            return

        sub = user.subscription
        plan = sub.plan if sub else "free"
        plan_label = sub.plan_label if sub else "⚪ Free"
        monthly = sub.monthly_tokens if sub else 0
        expires = sub.expires_at if sub else None

        if expires:
            exp = expires
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if now > exp:
                expires_str = "❌ Истекла"
            else:
                expires_str = exp.strftime("%d.%m.%Y")
        else:
            expires_str = "∞ Бессрочно" if plan != "free" else "—"

        reg = user.created_at.strftime("%d.%m.%Y") if user.created_at else "—"
        last = user.last_active.strftime("%d.%m.%Y %H:%M") if user.last_active else "—"

        # Последние 3 транзакции
        txs_result = await session.execute(
            select(TokenTransaction)
            .where(TokenTransaction.user_id == user.id)
            .order_by(desc(TokenTransaction.created_at))
            .limit(3)
        )
        txs = txs_result.scalars().all()
        tx_lines = []
        for tx in txs:
            sign = "+" if tx.amount > 0 else ""
            date = tx.created_at.strftime("%d.%m") if tx.created_at else ""
            tx_lines.append(f"  {sign}{tx.amount}🪙 {tx.reason} ({date})")

    text = (
        "╔══════════════════════════════╗\n"
        "║   👤  П Р О Ф И Л Ь          ║\n"
        "╚══════════════════════════════╝\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Имя: <b>{user.first_name}</b>\n"
        f"📛 Username: <b>{'@' + user.username if user.username else '—'}</b>\n"
        f"🎭 Роль: <b>{user.role_label}</b>\n"
        f"📅 Регистрация: <b>{reg}</b>\n"
        f"🕐 Последняя активность: <b>{last}</b>\n\n"
        f"<b>━━━ ПОДПИСКА ━━━</b>\n"
        f"💎 Тариф: <b>{plan_label}</b>\n"
        f"📅 Действует до: <b>{expires_str}</b>\n"
        f"📦 Токенов в месяц: <b>{monthly:,}</b>\n"
        f"🎮 Режим: <b>{user.work_mode.upper()}</b>\n\n"
        f"<b>━━━ СТАТИСТИКА ━━━</b>\n"
        f"📊 Всего запросов: <b>{user.total_requests:,}</b>\n"
        f"🪙 Потрачено токенов: <b>{user.total_tokens_spent:,}</b>\n"
        f"💰 Баланс: <b>{user.token_balance:,}</b> токенов\n"
    )

    if tx_lines:
        text += f"\n<b>━━━ ПОСЛЕДНИЕ ОПЕРАЦИИ ━━━</b>\n" + "\n".join(tx_lines)

    await call.message.edit_text(
        text,
        reply_markup=profile_kb(user.id, user.is_staff),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "profile:daily_bonus")
async def cb_daily_bonus(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        from core.tokens import TokenService
        svc = TokenService(session)
        claimed, balance = await svc.claim_daily_bonus(call.from_user.id)
        await session.commit()

    if claimed:
        await call.answer(f"🎁 +10 токенов! Баланс: {balance}🪙", show_alert=True)
    else:
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(call.from_user.id)
            if user and user.last_daily_bonus:
                from datetime import timedelta
                last = user.last_daily_bonus
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                next_bonus = last + timedelta(days=1)
                now = datetime.now(timezone.utc)
                hours_left = max(0, int((next_bonus - now).total_seconds() / 3600))
                await call.answer(f"⏳ Следующий бонус через {hours_left} ч.", show_alert=True)
            else:
                await call.answer("⏳ Бонус уже получен.", show_alert=True)


@router.callback_query(F.data == "menu:balance")
async def cb_balance(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        if not user:
            await call.answer("Ошибка")
            return

        sub = user.subscription
        plan_label = sub.plan_label if sub else "⚪ Free"
        monthly = sub.monthly_tokens if sub else 0

        result = await session.execute(
            select(TokenTransaction)
            .where(TokenTransaction.user_id == user.id)
            .order_by(desc(TokenTransaction.created_at))
            .limit(8)
        )
        txs = result.scalars().all()

    tx_lines = []
    for tx in txs:
        sign = "+" if tx.amount > 0 else ""
        date = tx.created_at.strftime("%d.%m %H:%M") if tx.created_at else ""
        icon = "🟢" if tx.amount > 0 else "🔴"
        tx_lines.append(f"  {icon} {sign}{tx.amount}🪙 — {tx.reason} ({date})")

    from core.tokens.token_service import MODE_COSTS
    text = (
        "╔══════════════════════════════╗\n"
        "║   🪙  Б А Л А Н С            ║\n"
        "╚══════════════════════════════╝\n\n"
        f"💰 Текущий баланс: <b>{user.token_balance:,} токенов</b>\n"
        f"💎 Тариф: <b>{plan_label}</b>\n"
        f"📦 Токенов в месяц: <b>{monthly:,}</b>\n\n"
        f"<b>━━━ СТОИМОСТЬ РЕЖИМОВ ━━━</b>\n"
        f"⚡ Lite:     <b>{MODE_COSTS['lite']}</b> токенов/запрос\n"
        f"🔵 Standard: <b>{MODE_COSTS['standard']}</b> токенов/запрос\n"
        f"🟣 Deep:     <b>{MODE_COSTS['deep']}</b> токенов/запрос\n"
        f"🔴 Ultra:    <b>{MODE_COSTS['ultra']}</b> токенов/запрос\n\n"
        f"<b>━━━ ПОСЛЕДНИЕ ОПЕРАЦИИ ━━━</b>\n"
        f"{chr(10).join(tx_lines) if tx_lines else '  Нет операций'}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:profile"))
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "menu:history")
async def cb_history(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        search_repo = SearchRepository(session)
        history = await search_repo.get_user_history(call.from_user.id, limit=10)

    if not history:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:profile"))
        await call.message.edit_text(
            "📜 <b>История запросов</b>\n\nЗапросов пока нет.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
        await call.answer()
        return

    lines = ["📜 <b>История запросов</b>\n"]
    for i, h in enumerate(history, 1):
        date = h.created_at.strftime("%d.%m %H:%M") if h.created_at else ""
        conf = f"{int(h.confidence_score * 100)}%" if h.confidence_score else "—"
        status_icon = "✅" if h.status == "completed" else "❌"
        lines.append(
            f"{status_icon} <b>{i}.</b> <code>{h.query[:35]}</code>\n"
            f"   🎮 {h.mode.upper()} | 📦 {h.results_count} | 📊 {conf} | {date}"
        )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:profile"))
    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "menu:subscription")
async def cb_subscription(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        sub = user.subscription if user else None
        plan = sub.plan if sub else "free"
        plan_label = sub.plan_label if sub else "⚪ Free"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:profile"))

    text = (
        "╔══════════════════════════════╗\n"
        "║   💎  П О Д П И С К А        ║\n"
        "╚══════════════════════════════╝\n\n"
        f"Текущий тариф: <b>{plan_label}</b>\n\n"
        "<b>━━━ ТАРИФЫ ━━━</b>\n\n"
        "⚪ <b>Free</b> — 0$/мес\n"
        "  • 100 токенов/мес\n"
        "  • Режимы: Lite, Standard\n\n"
        "🔵 <b>Premium</b> — 9.99$/мес\n"
        "  • 2000 токенов/мес\n"
        "  • Режимы: + Deep Scan\n"
        "  • Все инструменты поиска\n\n"
        "🔴 <b>Enterprise</b> — 49.99$/мес\n"
        "  • 10000 токенов/мес\n"
        "  • Все режимы включая Ultra AI\n\n"
        "⭐ <b>VIP</b> — выдаётся администратором\n"
        "  • 5000 токенов/мес\n"
        "  • Все режимы\n\n"
        "📩 Для покупки/вопросов: @destalone"
    )
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "menu:settings")
async def cb_settings(call: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎮 Режим работы", callback_data="menu:mode"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main"))
    await call.message.edit_text(
        "⚙️ <b>Настройки</b>\n\nВыберите параметр:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await call.answer()
