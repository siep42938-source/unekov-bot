"""
Unekov.help — AI OSINT Analytical Bot
Entry point: FastAPI + webhook (production/Render) или polling (dev).
"""
import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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


# ── Storage ───────────────────────────────────────────────────────────────────
def get_storage():
    try:
        from aiogram.fsm.storage.redis import RedisStorage
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

dp.message.middleware(RateLimitMiddleware())
dp.callback_query.middleware(RateLimitMiddleware())
dp.message.middleware(AuthMiddleware())
dp.callback_query.middleware(AuthMiddleware())
dp.include_router(main_router)


# ── Seed default data ─────────────────────────────────────────────────────────
async def seed_default_data():
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


# ── Polling (dev) ─────────────────────────────────────────────────────────────
async def run_polling():
    logger.info("🚀 Starting in POLLING mode...")
    await init_db()
    await seed_default_data()
    logger.info(f"🤖 Bot: @{(await bot.get_me()).username}")
    logger.info("✅ Ready!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


# ── FastAPI app (production / Render) ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_default_data()
    webhook_url = settings.webhook_url
    if webhook_url:
        await bot.set_webhook(
            url=f"{webhook_url}/webhook",
            allowed_updates=dp.resolve_used_update_types(),
        )
        logger.info(f"🚀 Webhook set: {webhook_url}/webhook")
    else:
        # Render: запускаем polling в фоне
        logger.info("🚀 No WEBHOOK_URL — starting polling in background...")
        asyncio.create_task(
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        )
    yield
    await bot.session.close()


app = FastAPI(title="Unekov.help", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/")
async def root():
    return {"status": "ok"}


# ── Entry point (локальный запуск) ────────────────────────────────────────────
if __name__ == "__main__":
    if settings.webhook_url and settings.is_production:
        import uvicorn
        port = int(os.environ.get("PORT", settings.api_port))
        uvicorn.run("main:app", host="0.0.0.0", port=port)
    else:
        asyncio.run(run_polling())
