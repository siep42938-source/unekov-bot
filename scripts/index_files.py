"""
Скрипт для ручной индексации всех файлов.
Запуск: python scripts/index_files.py

Индексирует:
  - ../bif BD/          (CSV, XLSX, TXT, SQL)
  - ../Telegram Users/  (TXT)
  - ../Telegram_Chats_2022_63kk/ (папки с данными)
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db.database import AsyncSessionLocal, engine
from db.models import Base
from core.indexer import index_all_sources
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def create_tables():
    """Создаёт все таблицы включая indexed_records."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # pg_trgm для full-text search
        try:
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_ir_raw_trgm
                ON indexed_records USING gin (raw gin_trgm_ops)
            """))
            await session.commit()
        except Exception as e:
            logger.warning(f"pg_trgm setup: {e}")


async def main():
    logger.info("🚀 Unekov.help File Indexer")
    logger.info("Creating tables...")
    await create_tables()

    logger.info("Starting indexation...")
    async with AsyncSessionLocal() as session:
        await index_all_sources(session, base_path="..")

    # Статистика
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT source_tag, COUNT(*) FROM indexed_records GROUP BY source_tag ORDER BY COUNT(*) DESC")
        )
        rows = result.fetchall()

    logger.info("\n📊 Indexation complete!")
    logger.info("Sources indexed:")
    total = 0
    for tag, cnt in rows:
        logger.info(f"  {tag}: {cnt:,} records")
        total += cnt
    logger.info(f"\nTotal: {total:,} records")


if __name__ == "__main__":
    asyncio.run(main())
