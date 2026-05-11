"""
Unekov.help — AI OSINT Analytical Bot
Entry point: runs Telegram bot in polling mode (dev) or webhook+FastAPI (prod).
"""
import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from db import init_db
from bot.handlers import main_router
from bot.middlewares import AuthMiddleware, RateLimitMiddleware

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ── Storage (Redis если доступен, иначе Memory) ───────────────────────────────
def get_storage():
    try:
        from aiogram.fsm.storage.redis import RedisStorage
        import redis.asyncio as aioredis
        # Проверяем доступность Redis
        storage = RedisStorage.from_url(settings.redis_url)
        logger.info("✅ Storage: Redis")
        return storage
    except Exception:
        logger.warning("⚠️  Redis недоступен, используем MemoryStorage")
        return MemoryStorage()


# ── Bot & Dispatcher ──────────────────────────────────────────────────────────
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
storage = get_storage()
dp = Dispatcher(storage=storage)

# Middlewares
dp.message.middleware(RateLimitMiddleware())
dp.callback_query.middleware(RateLimitMiddleware())
dp.message.middleware(AuthMiddleware())
dp.callback_query.middleware(AuthMiddleware())

# Handlers
dp.include_router(main_router)


# ── Seed default data ─────────────────────────────────────────────────────────
async def seed_default_data():
    """Создаёт дефолтные инструменты и источники БД при первом запуске."""
    from db.database import AsyncSessionLocal
    from db.models import Tool
    from db.models.database_source import DatabaseSource, DEFAULT_SOURCES
    from db.models.tool import DEFAULT_TOOLS
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        for tool_data in DEFAULT_TOOLS:
            exists = (await session.execute(
                select(Tool).where(Tool.slug == tool_data["slug"])
            )).scalar_one_or_none()
            if not exists:
                session.add(Tool(**tool_data))

        for src_data in DEFAULT_SOURCES:
            exists = (await session.execute(
                select(DatabaseSource).where(DatabaseSource.slug == src_data["slug"])
            )).scalar_one_or_none()
            if not exists:
                session.add(DatabaseSource(**src_data))

        await session.commit()
    logger.info("✅ Default data seeded")


# ── Polling mode (dev / local) ────────────────────────────────────────────────
async def run_polling():
    logger.info("🚀 Unekov.help starting in POLLING mode...")
    await init_db()
    await seed_default_data()
    logger.info(f"🤖 Bot: @{(await bot.get_me()).username}")
    logger.info("✅ Ready! Press Ctrl+C to stop.")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


# ── Webhook + FastAPI mode (production) ───────────────────────────────────────
async def run_webhook():
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from contextlib import asynccontextmanager
    import uvicorn

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_db()
        await seed_default_data()
        await bot.set_webhook(
            url=f"{settings.webhook_url}/webhook",
            allowed_updates=dp.resolve_used_update_types(),
        )
        logger.info(f"🚀 Webhook set: {settings.webhook_url}/webhook")
        yield
        await bot.delete_webhook()

    app = FastAPI(title="Unekov.help", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    # API роутеры
    try:
        from api.routers import api_router
        app.include_router(api_router, prefix="/api/v1")
    except Exception as e:
        logger.warning(f"API routers not loaded: {e}")

    @app.post("/webhook")
    async def webhook(request: Request):
        from aiogram.types import Update
        import json
        body = await request.body()
        update = Update.model_validate(json.loads(body))
        await dp.feed_update(bot, update)
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "ok", "bot": "Unekov.help"}

    config = uvicorn.Config(app=app, host=settings.api_host, port=settings.api_port)
    server = uvicorn.Server(config)
    await server.serve()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if settings.webhook_url and settings.is_production:
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())
