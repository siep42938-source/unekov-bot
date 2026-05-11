import logging
from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from db.database import AsyncSessionLocal
from db.repositories import UserRepository

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Ensure user exists in DB on every update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = None
        if isinstance(event, (Message, CallbackQuery)):
            tg_user = event.from_user

        if tg_user:
            async with AsyncSessionLocal() as session:
                repo = UserRepository(session)
                user, _ = await repo.get_or_create(tg_user)
                if user.is_banned:
                    if isinstance(event, Message):
                        await event.answer("🚫 Ваш аккаунт заблокирован.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("🚫 Заблокирован.", show_alert=True)
                    return
                await session.commit()
                data["db_user"] = user

        return await handler(event, data)
