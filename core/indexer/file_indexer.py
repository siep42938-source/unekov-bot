"""
FileIndexer — индексирует все файлы из bif BD/, Telegram Users/,
Telegram_Chats_2022_63kk/ в PostgreSQL для быстрого поиска.

Поддерживаемые форматы:
  CSV, TXT, XLSX, SQL (парсинг INSERT), JSON
"""
import csv
import json
import os
import logging
import asyncio
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Максимум строк на файл при индексации
MAX_ROWS_PER_FILE = 500_000
BATCH_SIZE = 1000


async def index_all_sources(session: AsyncSession, base_path: str = ".."):
    """Индексирует все источники данных."""
    sources = [
        (os.path.join(base_path, "bif BD"), "bif_bd"),
        (os.path.join(base_path, "Telegram Users"), "telegram_users_files"),
        (os.path.join(base_path, "Telegram_Chats_2022_63kk"), "tg_chats_2022"),
    ]
    for folder, source_tag in sources:
        if os.path.exists(folder):
            logger.info(f"Indexing {folder}...")
            await index_folder(session, folder, source_tag)


async def index_folder(session: AsyncSession, folder: str, source_tag: str):
    """Рекурсивно индексирует папку."""
    for root, dirs, files in os.walk(folder):
        for fname in files:
            fpath = os.path.join(root, fname)
            ext = Path(fname).suffix.lower()
            try:
                if ext == ".csv":
                    await index_csv(session, fpath, source_tag)
                elif ext == ".txt":
                    await index_txt(session, fpath, source_tag)
                elif ext in (".xlsx", ".xls"):
                    await index_xlsx(session, fpath, source_tag)
                elif ext == ".sql":
                    await index_sql(session, fpath, source_tag)
                elif ext == ".json":
                    await index_json(session, fpath, source_tag)
                elif ext in (".rar", ".zip", ".7z", ".tar", ".gz"):
                    await index_archive(session, fpath, source_tag)
                elif ext == ".py":
                    await index_txt(session, fpath, source_tag)  # py как текст
            except Exception as e:
                logger.warning(f"Skip {fpath}: {e}")


async def index_csv(session: AsyncSession, fpath: str, source_tag: str):
    """Индексирует CSV файл в таблицу indexed_records."""
    fname = Path(fpath).name
    batch = []
    try:
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            # Определяем разделитель
            sample = f.read(2048)
            f.seek(0)
            delimiter = ";" if sample.count(";") > sample.count(",") else ","
            reader = csv.DictReader(f, delimiter=delimiter)
            fields = reader.fieldnames or []

            for i, row in enumerate(reader):
                if i >= MAX_ROWS_PER_FILE:
                    break
                record = _normalize_row(dict(row), fields, fname, source_tag)
                batch.append(record)
                if len(batch) >= BATCH_SIZE:
                    await _bulk_insert(session, batch)
                    batch = []

        if batch:
            await _bulk_insert(session, batch)
        logger.info(f"Indexed CSV: {fname}")
    except Exception as e:
        logger.error(f"CSV index error {fpath}: {e}")


async def index_txt(session: AsyncSession, fpath: str, source_tag: str):
    """Индексирует TXT файл (построчно или как TG users формат)."""
    fname = Path(fpath).name
    batch = []
    try:
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= MAX_ROWS_PER_FILE:
                    break
                line = line.strip()
                if not line:
                    continue

                # Пробуем распарсить как TG users: id:phone:username:name
                parts = line.split(":")
                if len(parts) >= 3:
                    record = {
                        "raw": line,
                        "tg_id": parts[0].strip() if parts[0].strip().isdigit() else None,
                        "phone": parts[1].strip() if len(parts) > 1 else None,
                        "username": parts[2].strip() if len(parts) > 2 else None,
                        "first_name": parts[3].strip() if len(parts) > 3 else None,
                        "source_file": fname,
                        "source_tag": source_tag,
                    }
                else:
                    record = {
                        "raw": line,
                        "source_file": fname,
                        "source_tag": source_tag,
                    }
                batch.append(record)
                if len(batch) >= BATCH_SIZE:
                    await _bulk_insert(session, batch)
                    batch = []

        if batch:
            await _bulk_insert(session, batch)
        logger.info(f"Indexed TXT: {fname}")
    except Exception as e:
        logger.error(f"TXT index error {fpath}: {e}")


async def index_xlsx(session: AsyncSession, fpath: str, source_tag: str):
    """Индексирует XLSX файл."""
    try:
        import openpyxl
        fname = Path(fpath).name
        wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
        batch = []
        for sheet in wb.worksheets:
            headers = None
            for i, row in enumerate(sheet.iter_rows(values_only=True)):
                if i >= MAX_ROWS_PER_FILE:
                    break
                if i == 0:
                    headers = [str(c).strip() if c else f"col{j}" for j, c in enumerate(row)]
                    continue
                if not any(row):
                    continue
                row_dict = {headers[j]: str(v) if v is not None else "" for j, v in enumerate(row) if j < len(headers)}
                record = _normalize_row(row_dict, headers or [], fname, source_tag)
                batch.append(record)
                if len(batch) >= BATCH_SIZE:
                    await _bulk_insert(session, batch)
                    batch = []
        if batch:
            await _bulk_insert(session, batch)
        wb.close()
        logger.info(f"Indexed XLSX: {fname}")
    except ImportError:
        logger.warning("openpyxl not installed, skipping XLSX")
    except Exception as e:
        logger.error(f"XLSX index error {fpath}: {e}")


async def index_sql(session: AsyncSession, fpath: str, source_tag: str):
    """Парсит SQL дамп и извлекает INSERT данные."""
    import re
    fname = Path(fpath).name
    batch = []
    try:
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            content = f.read(10 * 1024 * 1024)  # max 10MB

        # Ищем INSERT INTO ... VALUES (...)
        pattern = re.compile(r"INSERT INTO\s+`?(\w+)`?\s+.*?VALUES\s*(.+?);", re.DOTALL | re.IGNORECASE)
        for match in pattern.finditer(content):
            table = match.group(1)
            values_str = match.group(2)
            # Парсим строки значений
            rows = re.findall(r"\(([^)]+)\)", values_str)
            for row_str in rows[:MAX_ROWS_PER_FILE]:
                record = {
                    "raw": row_str[:500],
                    "table_name": table,
                    "source_file": fname,
                    "source_tag": source_tag,
                }
                batch.append(record)
                if len(batch) >= BATCH_SIZE:
                    await _bulk_insert(session, batch)
                    batch = []

        if batch:
            await _bulk_insert(session, batch)
        logger.info(f"Indexed SQL: {fname}")
    except Exception as e:
        logger.error(f"SQL index error {fpath}: {e}")


async def index_json(session: AsyncSession, fpath: str, source_tag: str):
    """Индексирует JSON файл."""
    fname = Path(fpath).name
    batch = []
    try:
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return
        for i, item in enumerate(data):
            if i >= MAX_ROWS_PER_FILE:
                break
            if not isinstance(item, dict):
                item = {"value": str(item)}
            record = _normalize_row(item, list(item.keys()), fname, source_tag)
            batch.append(record)
            if len(batch) >= BATCH_SIZE:
                await _bulk_insert(session, batch)
                batch = []
        if batch:
            await _bulk_insert(session, batch)
        logger.info(f"Indexed JSON: {fname}")
    except Exception as e:
        logger.error(f"JSON index error {fpath}: {e}")


def _normalize_row(row: dict, fields: list, fname: str, source_tag: str) -> dict:
    """Нормализует строку для индексации."""
    # Стандартные поля
    normalized = {
        "source_file": fname,
        "source_tag": source_tag,
        "raw": json.dumps(row, ensure_ascii=False)[:1000],
    }
    # Маппинг известных полей
    field_map = {
        "id": ["id", "user_id", "uid", "tg_id"],
        "phone": ["phone", "phone_number", "giver_phone", "телефон", "mobile"],
        "username": ["username", "user_name", "login", "nick"],
        "first_name": ["first_name", "firstname", "name", "имя", "donation_first_name"],
        "last_name": ["last_name", "lastname", "surname", "фамилия", "donation_last_name"],
        "email": ["email", "e_mail", "mail", "donation_email", "почта"],
        "tg_id": ["id", "tg_id", "telegram_id", "user_id"],
    }
    row_lower = {k.lower().strip(): v for k, v in row.items()}
    for target, sources in field_map.items():
        for src in sources:
            if src in row_lower and row_lower[src]:
                normalized[target] = str(row_lower[src])[:256]
                break
    return normalized


async def _bulk_insert(session: AsyncSession, records: list[dict]):
    """Вставляет пачку записей в indexed_records."""
    if not records:
        return
    try:
        await session.execute(
            text("""
                INSERT INTO indexed_records
                    (source_file, source_tag, raw, phone, username, first_name, last_name, email, tg_id)
                VALUES
                    (:source_file, :source_tag, :raw, :phone, :username, :first_name, :last_name, :email, :tg_id)
                ON CONFLICT DO NOTHING
            """),
            [
                {
                    "source_file": r.get("source_file", ""),
                    "source_tag": r.get("source_tag", ""),
                    "raw": r.get("raw", ""),
                    "phone": r.get("phone"),
                    "username": r.get("username"),
                    "first_name": r.get("first_name"),
                    "last_name": r.get("last_name"),
                    "email": r.get("email"),
                    "tg_id": r.get("tg_id"),
                }
                for r in records
            ]
        )
        await session.commit()
    except Exception as e:
        logger.error(f"Bulk insert error: {e}")
        await session.rollback()


async def index_archive(session: AsyncSession, fpath: str, source_tag: str):
    """Распаковывает архив и индексирует содержимое."""
    import tempfile
    from core.indexer.archive_extractor import extract_archive

    fname = Path(fpath).name
    logger.info(f"Extracting archive: {fname}")

    with tempfile.TemporaryDirectory() as tmpdir:
        extracted_files = extract_archive(fpath, tmpdir)
        if not extracted_files:
            logger.warning(f"No indexable files in archive: {fname}")
            return

        for ef in extracted_files:
            ext = Path(ef).suffix.lower()
            archive_source_tag = f"{source_tag}:{fname}"
            try:
                if ext == ".csv":
                    await index_csv(session, ef, archive_source_tag)
                elif ext in (".txt", ".log", ".py"):
                    await index_txt(session, ef, archive_source_tag)
                elif ext == ".json":
                    await index_json(session, ef, archive_source_tag)
                elif ext == ".sql":
                    await index_sql(session, ef, archive_source_tag)
            except Exception as e:
                logger.warning(f"Archive file index error {ef}: {e}")

    logger.info(f"Indexed archive: {fname} ({len(extracted_files)} files)")
