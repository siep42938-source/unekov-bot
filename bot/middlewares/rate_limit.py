import logging
import time
from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)

RATE_LIMIT_SECONDS = 1   # мин. секунд между запросами
SPAM_LIMIT = 15          # макс. запросов в минуту

# In-memory fallback (работает без Redis)
_last_request: dict[int, float] = {}
_request_count: dict[int, list] = {}


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self):
        self._redis = None
        self._use_redis = False
        self._redis_checked = False

    async def _try_get_redis(self):
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            from config import settings
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
            await r.ping()
            self._redis = r
            self._use_redis = True
            logger.info("RateLimit: using Redis")
        except Exception:
            logger.info("RateLimit: using in-memory (Redis unavailable)")
        return self._redis

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id

        if user_id:
            now = time.time()

            # Rate limit: 1 req per N sec
            last = _last_request.get(user_id, 0)
            if now - last < RATE_LIMIT_SECONDS:
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳", show_alert=False)
                return
            _last_request[user_id] = now

            # Spam limit: N req per minute
            counts = _request_count.get(user_id, [])
            counts = [t for t in counts if now - t < 60]
            if len(counts) >= SPAM_LIMIT:
                if isinstance(event, Message):
                    await event.answer("🚫 Слишком много запросов. Подождите минуту.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 Слишком много запросов.", show_alert=True)
                return
            counts.append(now)
            _request_count[user_id] = counts

        return await handler(event, data)
