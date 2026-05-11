import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from db.database import AsyncSessionLocal
from db.repositories import UserRepository
from core.tokens import TokenService
from bot.keyboards import main_menu_kb

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user, is_new = await repo.get_or_create(message.from_user)
        await session.commit()

        token_svc = TokenService(session)
        claimed, new_balance = await token_svc.claim_daily_bonus(user.id)
        await session.commit()

        balance = new_balance if claimed else user.token_balance
        sub = user.subscription
        plan_label = sub.plan_label if sub else "⚪ Free"

    role_line = f"🎭 Роль: <b>{user.role_label}</b>\n" if user.role != "user" else ""

    text = (
        "╔══════════════════════════════╗\n"
        "║   🌐  U N E K O V . H E L P  ║\n"
        "║   AI OSINT ANALYTICAL SYSTEM ║\n"
        "╚══════════════════════════════╝\n\n"
        f"Добро пожаловать, <b>{user.display_name}</b>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"{role_line}"
        f"💎 Тариф: <b>{plan_label}</b>\n"
        f"🪙 Баланс: <b>{balance:,} токенов</b>\n"
        f"🎮 Режим: <b>{user.work_mode.upper()}</b>\n"
    )

    if is_new:
        text += f"\n🎉 <b>Добро пожаловать!</b> Начислено <b>{balance}</b>🪙"
    elif claimed:
        text += f"\n🎁 <b>Дневной бонус:</b> +10 токенов!"

    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        if not user:
            await call.answer("Напишите /start")
            return
        sub = user.subscription
        plan_label = sub.plan_label if sub else "⚪ Free"

    role_line = f"🎭 {user.role_label}  |  " if user.role != "user" else ""
    text = (
        "╔══════════════════════════════╗\n"
        "║   🌐  U N E K O V . H E L P  ║\n"
        "╚══════════════════════════════╝\n\n"
        f"<b>[ ГЛАВНОЕ МЕНЮ ]</b>\n\n"
        f"👤 <b>{user.display_name}</b>\n"
        f"{role_line}💎 <b>{plan_label}</b>\n"
        f"🪙 <b>{user.token_balance:,}</b> токенов  |  🎮 <b>{user.work_mode.upper()}</b>\n\n"
        "Выберите раздел:"
    )
    await call.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    await call.answer()


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(message.from_user.id)
        if not user:
            await message.answer("Напишите /start")
            return
        sub = user.subscription
        plan_label = sub.plan_label if sub else "⚪ Free"

    text = (
        "╔══════════════════════════════╗\n"
        "║   🌐  U N E K O V . H E L P  ║\n"
        "╚══════════════════════════════╝\n\n"
        f"👤 <b>{user.display_name}</b>  |  💎 <b>{plan_label}</b>\n"
        f"🪙 <b>{user.token_balance:,}</b>  |  🎮 <b>{user.work_mode.upper()}</b>\n\n"
        "Выберите раздел:"
    )
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
