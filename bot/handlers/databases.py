import logging
import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, Document
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from db.database import AsyncSessionLocal
from db.models import UploadedFile
from db.models.database_source import DEFAULT_SOURCES
from db.repositories import UserRepository
from core.search.universal_search import UniversalSearch
from bot.keyboards import databases_menu_kb, db_detail_kb, cancel_kb, main_menu_kb
from bot import ui_texts as T

router = Router()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DBState(StatesGroup):
    waiting_file = State()
    waiting_search_query = State()


@router.callback_query(F.data == "menu:databases")
async def cb_databases_menu(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        plan = user.subscription.plan if user and user.subscription else "free"

    text = T.DATABASES_MENU.format(plan=plan.upper())
    await call.message.edit_text(text, reply_markup=databases_menu_kb(plan), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("db:view:"))
async def cb_db_view(call: CallbackQuery):
    slug = call.data.replace("db:view:", "")
    src = next((s for s in DEFAULT_SOURCES if s["slug"] == slug), None)
    if not src:
        await call.answer("База не найдена", show_alert=True)
        return

    # Get record count for known sources
    count = 0
    async with AsyncSessionLocal() as session:
        if slug == "telegram_users":
            from db.models import TelegramUser
            count = (await session.execute(select(func.count()).select_from(TelegramUser))).scalar() or 0
        elif slug == "csv_files":
            count = (await session.execute(
                select(func.count()).select_from(UploadedFile).where(UploadedFile.is_active == True)
            )).scalar() or 0

    text = (
        f"{src['icon']} <b>{src['name']}</b>\n\n"
        f"{src['description']}\n\n"
        f"📦 Записей: <b>{count:,}</b>\n"
        f"🔧 Тип: <b>{src['source_type']}</b>\n"
        f"💎 Доступ: <b>{src['access_level'].upper()}</b>"
    )
    await call.message.edit_text(text, reply_markup=db_detail_kb(slug), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "db:upload")
async def cb_db_upload(call: CallbackQuery, state: FSMContext):
    await state.set_state(DBState.waiting_file)
    await call.message.edit_text(
        "📤 <b>Загрузка файла</b>\n\n"
        "Отправьте файл в формате:\n"
        "• CSV — таблица с данными\n"
        "• JSON — массив объектов\n"
        "• TXT — текстовые данные\n\n"
        "Максимальный размер: <b>10 МБ</b>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(DBState.waiting_file, F.document)
async def process_db_file_upload(message: Message, state: FSMContext):
    doc: Document = message.document
    fname = doc.file_name or "file"
    allowed = (".csv", ".json", ".txt", ".log")

    if not any(fname.lower().endswith(ext) for ext in allowed):
        await message.answer("❌ Поддерживаются только CSV, JSON, TXT файлы.")
        return

    if doc.file_size and doc.file_size > 10 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой. Максимум 10 МБ.")
        return

    await state.clear()
    progress = await message.answer("⏳ Загружаю и индексирую файл...")

    file = await message.bot.get_file(doc.file_id)
    file_path = os.path.join(UPLOAD_DIR, f"{message.from_user.id}_{fname}")
    await message.bot.download_file(file.file_path, destination=file_path)

    # Count rows
    row_count = 0
    ext = os.path.splitext(fname)[1].lower()
    try:
        if ext == ".csv":
            import csv
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                row_count = sum(1 for _ in csv.DictReader(f))
        elif ext == ".json":
            import json
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            row_count = len(data) if isinstance(data, list) else 1
        elif ext in (".txt", ".log"):
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                row_count = sum(1 for line in f if line.strip())
    except Exception:
        row_count = 0

    # Save to DB
    async with AsyncSessionLocal() as session:
        uf = UploadedFile(
            user_id=message.from_user.id,
            original_name=fname,
            file_path=file_path,
            file_type=ext.lstrip("."),
            file_size=doc.file_size or 0,
            row_count=row_count,
            is_indexed=True,
        )
        session.add(uf)
        await session.commit()

    await progress.edit_text(
        f"✅ <b>Файл загружен!</b>\n\n"
        f"📂 Имя: <b>{fname}</b>\n"
        f"📦 Строк: <b>{row_count:,}</b>\n\n"
        f"Теперь файл доступен для поиска через раздел 🔍 Поиск или 🛠️ File Scanner.",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("db:search:"))
async def cb_db_search(call: CallbackQuery, state: FSMContext):
    slug = call.data.replace("db:search:", "")
    await state.set_state(DBState.waiting_search_query)
    await state.update_data(db_slug=slug)
    await call.message.edit_text(
        f"🔍 Поиск в базе <b>{slug}</b>\n\n✏️ Введите запрос:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(DBState.waiting_search_query)
async def process_db_search(message: Message, state: FSMContext):
    data = await state.get_data()
    slug = data.get("db_slug", "")
    query = message.text.strip()
    await state.clear()

    progress = await message.answer(f"⏳ Поиск в <b>{slug}</b>...", parse_mode="HTML")

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(message.from_user.id)
        mode = user.work_mode if user else "standard"
        lang = user.language_code or "ru"

        searcher = UniversalSearch(session)
        result = await searcher.search(query, message.from_user.id, mode, lang)
        await session.commit()

    ai = result.get("ai_report", {})
    text = (
        f"🗄️ <b>Поиск в {slug}</b>\n\n"
        f"🔍 Запрос: <code>{query}</code>\n"
        f"📦 Найдено: <b>{result['total_found']}</b>\n\n"
        f"🤖 {ai.get('summary', 'Нет данных')}"
    )
    await progress.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
