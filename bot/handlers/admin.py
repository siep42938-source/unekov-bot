import logging
import asyncio
from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy import select, func, update, desc, text
from db.database import AsyncSessionLocal
from db.models import User, Subscription
from db.repositories import UserRepository
from core.tokens import TokenService
from config import settings

router = Router()
logger = logging.getLogger(__name__)

OWNER_USERNAME = "destalone"
OWNER_IDS = {8362218249}  # @Full_Karat


def is_admin(user_id: int, username: str | None = None) -> bool:
    if user_id in OWNER_IDS:
        return True
    if username and username.lower() == OWNER_USERNAME.lower():
        return True
    return user_id in settings.admin_ids


# ── Inline Admin Panel ────────────────────────────────────────────────────────

def admin_panel_kb() -> object:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="👥 Пользователи",   callback_data="admin:users:0"),
        InlineKeyboardButton(text="📊 Статистика",     callback_data="admin:stats"),
    )
    b.row(
        InlineKeyboardButton(text="🎁 Выдать токены",  callback_data="admin:grant_tokens"),
        InlineKeyboardButton(text="💎 Выдать подписку", callback_data="admin:grant_sub"),
    )
    b.row(
        InlineKeyboardButton(text="🎭 Изменить роль",  callback_data="admin:set_role"),
        InlineKeyboardButton(text="🚫 Бан/Разбан",     callback_data="admin:ban"),
    )
    b.row(
        InlineKeyboardButton(text="🗄️ Индексация БД",  callback_data="admin:index"),
        InlineKeyboardButton(text="◀️ Меню",           callback_data="menu:main"),
    )
    return b.as_markup()


@router.callback_query(F.data == "admin:panel")
async def cb_admin_panel(call: CallbackQuery):
    if not is_admin(call.from_user.id, call.from_user.username):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
        from db.models import IndexedRecord
        indexed = (await session.execute(select(func.count()).select_from(IndexedRecord))).scalar() or 0
    text = (
        "╔══════════════════════════════╗\n"
        "║  ⚡  А Д М И Н  П А Н Е Л Ь  ║\n"
        "╚══════════════════════════════╝\n\n"
        f"👥 Пользователей: <b>{total:,}</b>\n"
        f"📦 Проиндексировано: <b>{indexed:,}</b>\n\n"
        "Выберите действие:"
    )
    await call.message.edit_text(text, reply_markup=admin_panel_kb(), parse_mode="HTML")
    await call.answer()


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id, call.from_user.username):
        await call.answer("⛔", show_alert=True)
        return
    from db.models import IndexedRecord, TelegramUser, SearchHistory
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        users   = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
        indexed = (await session.execute(select(func.count()).select_from(IndexedRecord))).scalar() or 0
        tg_u    = (await session.execute(select(func.count()).select_from(TelegramUser))).scalar() or 0
        searches= (await session.execute(select(func.count()).select_from(SearchHistory))).scalar() or 0
        banned  = (await session.execute(select(func.count()).select_from(User).where(User.is_banned == True))).scalar() or 0
        try:
            src_rows = (await session.execute(
                text("SELECT source_tag, COUNT(*) c FROM indexed_records GROUP BY source_tag ORDER BY c DESC LIMIT 6")
            )).fetchall()
        except Exception:
            src_rows = []

    src_text = "\n".join(f"  • {r[0]}: {r[1]:,}" for r in src_rows) or "  нет данных"
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:panel"))
    await call.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Юзеров: <b>{users:,}</b>  🚫 Забанено: <b>{banned}</b>\n"
        f"🔍 Поисков: <b>{searches:,}</b>\n"
        f"✈️ TG Users: <b>{tg_u:,}</b>\n"
        f"📦 Indexed: <b>{indexed:,}</b>\n\n"
        f"<b>Источники:</b>\n{src_text}",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await call.answer()


# ── Users list ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:users:"))
async def cb_admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id, call.from_user.username):
        await call.answer("⛔", show_alert=True)
        return
    page = int(call.data.split(":")[-1])
    limit, offset = 8, page * 8
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).order_by(desc(User.created_at)).limit(limit).offset(offset)
        )
        users = result.scalars().all()
        total = (await session.execute(select(func.count()).select_from(User))).scalar() or 0

    lines = [f"👥 <b>Пользователи</b> (стр. {page+1})\n"]
    for u in users:
        ban = "🚫" if u.is_banned else ""
        role_icon = {"owner":"👑","admin":"⚡","moderator":"🛡️","vip":"⭐"}.get(u.role, "👤")
        uname = f"@{u.username}" if u.username else f"id{u.id}"
        lines.append(f"{ban}{role_icon} <code>{u.id}</code> {uname} | 🪙{u.token_balance}")

    b = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:users:{page-1}"))
    if offset + limit < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:users:{page+1}"))
    if nav:
        b.row(*nav)
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:panel"))
    await call.message.edit_text("\n".join(lines), reply_markup=b.as_markup(), parse_mode="HTML")
    await call.answer()


# ── Grant tokens ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:grant_tokens")
async def cb_grant_tokens_prompt(call: CallbackQuery):
    if not is_admin(call.from_user.id, call.from_user.username):
        await call.answer("⛔", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:panel"))
    await call.message.edit_text(
        "🎁 <b>Выдать токены</b>\n\n"
        "Используй команду:\n"
        "<code>/grant &lt;user_id&gt; &lt;amount&gt;</code>\n\n"
        "Пример:\n<code>/grant 123456789 500</code>",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await call.answer()


@router.message(Command("grant"))
async def cmd_grant(message: Message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /grant <user_id> <amount>")
        return
    try:
        uid, amount = int(parts[1]), int(parts[2])
    except ValueError:
        await message.answer("❌ Неверный формат")
        return
    async with AsyncSessionLocal() as session:
        svc = TokenService(session)
        bal = await svc.credit(uid, amount, "admin_grant", f"от @{message.from_user.username}")
        await session.commit()
    await message.answer(f"✅ Выдано <b>{amount}</b>🪙 → <code>{uid}</code>\nБаланс: <b>{bal}</b>", parse_mode="HTML")


# ── Grant subscription ────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:grant_sub")
async def cb_grant_sub_prompt(call: CallbackQuery):
    if not is_admin(call.from_user.id, call.from_user.username):
        await call.answer("⛔", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:panel"))
    await call.message.edit_text(
        "💎 <b>Выдать подписку</b>\n\n"
        "Команда:\n"
        "<code>/sub &lt;user_id&gt; &lt;plan&gt; [days]</code>\n\n"
        "Планы: <code>free</code> <code>premium</code> <code>enterprise</code> <code>vip</code>\n\n"
        "Примеры:\n"
        "<code>/sub 123456789 premium 30</code>\n"
        "<code>/sub 123456789 vip</code>  (бессрочно)",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await call.answer()


@router.message(Command("sub"))
async def cmd_sub(message: Message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /sub <user_id> <plan> [days]")
        return
    try:
        uid = int(parts[1])
        plan = parts[2].lower()
        days = int(parts[3]) if len(parts) > 3 else None
    except ValueError:
        await message.answer("❌ Неверный формат")
        return

    if plan not in Subscription.PLANS:
        await message.answer(f"❌ Неверный план. Доступны: {', '.join(Subscription.PLANS.keys())}")
        return

    plan_data = Subscription.PLANS[plan]
    expires_at = None
    if days:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Subscription).where(Subscription.user_id == uid))
        sub = result.scalar_one_or_none()
        if sub:
            sub.plan = plan
            sub.monthly_tokens = plan_data["monthly_tokens"]
            sub.max_mode = plan_data["max_mode"]
            sub.is_active = True
            sub.expires_at = expires_at
            sub.granted_by = message.from_user.id
            sub.grant_reason = f"admin @{message.from_user.username}"
        else:
            sub = Subscription(
                user_id=uid, plan=plan,
                monthly_tokens=plan_data["monthly_tokens"],
                max_mode=plan_data["max_mode"],
                is_active=True, expires_at=expires_at,
                granted_by=message.from_user.id,
                grant_reason=f"admin @{message.from_user.username}",
            )
            session.add(sub)
        await session.commit()

    exp_str = f"{days} дней" if days else "бессрочно"
    await message.answer(
        f"✅ Подписка <b>{plan.upper()}</b> выдана → <code>{uid}</code>\n"
        f"Срок: <b>{exp_str}</b>",
        parse_mode="HTML"
    )


# ── Set role ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:set_role")
async def cb_set_role_prompt(call: CallbackQuery):
    if not is_admin(call.from_user.id, call.from_user.username):
        await call.answer("⛔", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:panel"))
    await call.message.edit_text(
        "🎭 <b>Изменить роль</b>\n\n"
        "Команда:\n<code>/role &lt;user_id&gt; &lt;role&gt;</code>\n\n"
        "Роли: <code>user</code> <code>vip</code> <code>moderator</code> <code>admin</code>",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await call.answer()


@router.message(Command("role"))
async def cmd_role(message: Message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /role <user_id> <role>")
        return
    try:
        uid = int(parts[1])
        role = parts[2].lower()
    except ValueError:
        await message.answer("❌ Неверный формат")
        return
    valid_roles = list(User.ROLES.keys())
    if role not in valid_roles:
        await message.answer(f"❌ Роли: {', '.join(valid_roles)}")
        return
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.id == uid).values(role=role))
        await session.commit()
    await message.answer(f"✅ Роль <b>{role}</b> → <code>{uid}</code>", parse_mode="HTML")


# ── Ban / Unban ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:ban")
async def cb_ban_prompt(call: CallbackQuery):
    if not is_admin(call.from_user.id, call.from_user.username):
        await call.answer("⛔", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:panel"))
    await call.message.edit_text(
        "🚫 <b>Бан / Разбан</b>\n\n"
        "<code>/ban &lt;user_id&gt;</code> — заблокировать\n"
        "<code>/unban &lt;user_id&gt;</code> — разблокировать",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await call.answer()


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /ban <user_id>")
        return
    uid = int(parts[1])
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.id == uid).values(is_banned=True))
        await session.commit()
    await message.answer(f"🚫 Пользователь <code>{uid}</code> заблокирован.", parse_mode="HTML")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /unban <user_id>")
        return
    uid = int(parts[1])
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.id == uid).values(is_banned=False))
        await session.commit()
    await message.answer(f"✅ Пользователь <code>{uid}</code> разблокирован.", parse_mode="HTML")


# ── Index files ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:index")
async def cb_admin_index(call: CallbackQuery):
    if not is_admin(call.from_user.id, call.from_user.username):
        await call.answer("⛔", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="▶️ Запустить", callback_data="admin:index:run"),
        InlineKeyboardButton(text="◀️ Назад",     callback_data="admin:panel"),
    )
    await call.message.edit_text(
        "🗄️ <b>Индексация файлов</b>\n\n"
        "Будут проиндексированы:\n"
        "• <code>bif BD/</code> — CSV, XLSX, TXT, SQL, RAR, ZIP\n"
        "• <code>Telegram Users/</code> — TXT\n"
        "• <code>Telegram_Chats_2022_63kk/</code> — 63kk\n"
        "• <code>tools/</code> — скрипты и архивы\n"
        "• <code>туторы/</code> — мануалы\n\n"
        "⚠️ Может занять несколько минут.",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "admin:index:run")
async def cb_admin_index_run(call: CallbackQuery):
    if not is_admin(call.from_user.id, call.from_user.username):
        await call.answer("⛔", show_alert=True)
        return
    await call.message.edit_text("⏳ <b>Индексация запущена...</b>\n\nЖди уведомления.", parse_mode="HTML")
    await call.answer()

    import asyncio
    asyncio.create_task(_run_indexation(call))


async def _run_indexation(call: CallbackQuery):
    try:
        from core.indexer import index_all_sources
        from db.models import IndexedRecord
        async with AsyncSessionLocal() as session:
            await index_all_sources(session, base_path="..")
        async with AsyncSessionLocal() as session:
            count = (await session.execute(select(func.count()).select_from(IndexedRecord))).scalar() or 0
        await call.message.answer(
            f"✅ <b>Индексация завершена!</b>\n📦 Записей: <b>{count:,}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await call.message.answer(f"❌ Ошибка: {str(e)[:200]}")


# ── /start для admin ──────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id, message.from_user.username):
        await message.answer("⛔ Нет доступа")
        return
    from bot.keyboards import main_menu_kb
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⚡ Открыть панель", callback_data="admin:panel"))
    b.row(InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"))
    await message.answer(
        "⚡ <b>Admin Panel — Unekov.help</b>\n\n"
        "Команды:\n"
        "/grant &lt;id&gt; &lt;amount&gt; — токены\n"
        "/sub &lt;id&gt; &lt;plan&gt; [days] — подписка\n"
        "/role &lt;id&gt; &lt;role&gt; — роль\n"
        "/ban &lt;id&gt; / /unban &lt;id&gt; — бан\n"
        "/admin_stats — статистика",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )


@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    from db.models import IndexedRecord, TelegramUser, SearchHistory
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        users    = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
        indexed  = (await session.execute(select(func.count()).select_from(IndexedRecord))).scalar() or 0
        tg_u     = (await session.execute(select(func.count()).select_from(TelegramUser))).scalar() or 0
        searches = (await session.execute(select(func.count()).select_from(SearchHistory))).scalar() or 0
    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Юзеров: <b>{users:,}</b>\n"
        f"🔍 Поисков: <b>{searches:,}</b>\n"
        f"✈️ TG Users: <b>{tg_u:,}</b>\n"
        f"📦 Indexed: <b>{indexed:,}</b>",
        parse_mode="HTML"
    )
