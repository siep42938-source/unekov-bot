import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, Document
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.database import AsyncSessionLocal
from db.repositories import UserRepository
from db.models.tool import DEFAULT_TOOLS
from bot.keyboards import tools_menu_kb, tool_action_kb, main_menu_kb, cancel_kb
from bot import ui_texts as T
import os

router = Router()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ToolState(StatesGroup):
    waiting_file = State()
    waiting_tool_query = State()


def _get_tool(slug: str) -> dict | None:
    return next((t for t in DEFAULT_TOOLS if t["slug"] == slug), None)


@router.callback_query(F.data == "menu:tools")
async def cb_tools_menu(call: CallbackQuery):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        plan = user.subscription.plan if user and user.subscription else "free"
        balance = user.token_balance if user else 0

    text = T.TOOLS_MENU.format(plan=plan.upper(), balance=balance)
    await call.message.edit_text(text, reply_markup=tools_menu_kb(plan), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("tool:") & ~F.data.startswith("tool:run:") & ~F.data.startswith("tool:info:"))
async def cb_tool_select(call: CallbackQuery):
    slug = call.data.split("tool:")[1]
    tool = _get_tool(slug)
    if not tool:
        await call.answer("Инструмент не найден", show_alert=True)
        return

    text = (
        f"<b>{tool['icon']} {tool['name']}</b>\n\n"
        f"{tool['description']}\n\n"
        f"💎 Минимальный тариф: <b>{tool['min_plan'].upper()}</b>\n"
        f"🪙 Стоимость: <b>{tool['token_cost']} токенов</b>"
    )
    await call.message.edit_text(text, reply_markup=tool_action_kb(slug), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("tool:run:"))
async def cb_tool_run(call: CallbackQuery, state: FSMContext):
    slug = call.data.replace("tool:run:", "")
    tool = _get_tool(slug)
    if not tool:
        await call.answer("Инструмент не найден", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        plan = user.subscription.plan if user and user.subscription else "free"
        balance = user.token_balance if user else 0

    # Check plan access
    from core.tokens import PLAN_MODE_ACCESS
    plan_order = {"free": 0, "premium": 1, "enterprise": 2}
    if plan_order.get(plan, 0) < plan_order.get(tool["min_plan"], 0):
        await call.answer(
            f"🔒 Требуется тариф {tool['min_plan'].upper()}",
            show_alert=True,
        )
        return

    if balance < tool["token_cost"]:
        await call.answer(
            f"❌ Недостаточно токенов. Нужно {tool['token_cost']}🪙",
            show_alert=True,
        )
        return

    # File scanner — ожидаем файл
    if slug == "file_scanner":
        await state.set_state(ToolState.waiting_file)
        await state.update_data(tool_slug=slug)
        await call.message.edit_text(
            "📂 <b>File Scanner</b>\n\nОтправьте файл (CSV, JSON, TXT) для поиска.\n"
            "После загрузки введите поисковый запрос.",
            reply_markup=cancel_kb(),
            parse_mode="HTML",
        )
    else:
        # Для остальных инструментов — запрашиваем текстовый запрос
        await state.set_state(ToolState.waiting_tool_query)
        await state.update_data(tool_slug=slug)
        await call.message.edit_text(
            f"{tool['icon']} <b>{tool['name']}</b>\n\n✏️ Введите запрос:",
            reply_markup=cancel_kb(),
            parse_mode="HTML",
        )
    await call.answer()


@router.message(ToolState.waiting_file, F.document)
async def process_file_upload(message: Message, state: FSMContext):
    doc: Document = message.document
    allowed_ext = (".csv", ".json", ".txt", ".log")
    fname = doc.file_name or "file"
    if not any(fname.lower().endswith(ext) for ext in allowed_ext):
        await message.answer("❌ Поддерживаются только CSV, JSON, TXT файлы.")
        return

    # Download file
    file = await message.bot.get_file(doc.file_id)
    file_path = os.path.join(UPLOAD_DIR, f"{message.from_user.id}_{fname}")
    await message.bot.download_file(file.file_path, destination=file_path)

    await state.update_data(file_path=file_path, file_name=fname)
    await message.answer(
        f"✅ Файл <b>{fname}</b> загружен.\n\n✏️ Введите поисковый запрос:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )


@router.message(ToolState.waiting_tool_query)
async def process_tool_query(message: Message, state: FSMContext):
    data = await state.get_data()
    slug = data.get("tool_slug", "")
    query = message.text.strip()
    await state.clear()

    if slug == "file_scanner":
        file_path = data.get("file_path")
        if not file_path or not os.path.exists(file_path):
            await message.answer("❌ Файл не найден. Попробуйте снова.", reply_markup=main_menu_kb())
            return

        from core.search.file_scanner import scan_file
        progress = await message.answer("⏳ Сканирование файла...", parse_mode="HTML")
        results = scan_file(file_path, query)

        if not results:
            await progress.edit_text(
                f"❌ Совпадений по запросу <code>{query}</code> не найдено.",
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
            return

        lines = [f"📂 <b>File Scanner</b> — найдено <b>{len(results)}</b> совпадений\n"]
        lines.append(f"🔍 Запрос: <code>{query}</code>\n")
        for i, r in enumerate(results[:10], 1):
            score = r.pop("_score", 0)
            src = r.pop("_source_file", "")
            r.pop("_type", None)
            r.pop("_source", None)
            preview = " | ".join(f"{k}: {v}" for k, v in list(r.items())[:4])
            lines.append(f"<b>{i}.</b> [{score:.0%}] {preview}")

        await progress.edit_text("\n".join(lines), reply_markup=main_menu_kb(), parse_mode="HTML")

    else:
        # Redirect to universal search for other tools
        from core.search.universal_search import UniversalSearch
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(message.from_user.id)
            mode = user.work_mode if user else "standard"
            lang = user.language_code or "ru"

            progress = await message.answer("⏳ Выполняю запрос...", parse_mode="HTML")
            searcher = UniversalSearch(session)
            result = await searcher.search(query, message.from_user.id, mode, lang)
            await session.commit()

        ai = result.get("ai_report", {})
        text = (
            f"🛠️ <b>{_get_tool(slug)['name'] if _get_tool(slug) else slug}</b>\n\n"
            f"🔍 Запрос: <code>{query}</code>\n"
            f"📦 Найдено: <b>{result['total_found']}</b>\n\n"
            f"🤖 <b>AI:</b> {ai.get('summary', 'Нет данных')}\n"
            f"📊 Confidence: <b>{int(ai.get('confidence', 0) * 100)}%</b>"
        )
        await progress.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
