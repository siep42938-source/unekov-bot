"""
AI Search handler — главная кнопка поиска.
Пользователь пишет запрос → бот ищет во ВСЕХ файлах и базах → AI анализирует → отчёт.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from db.database import AsyncSessionLocal
from db.repositories import UserRepository, SearchRepository
from core.tokens import TokenService, MODE_COSTS
from core.search.universal_search import UniversalSearch
from bot.keyboards import main_menu_kb, cancel_kb
from bot import ui_texts as T

router = Router()
logger = logging.getLogger(__name__)


class AISearchState(StatesGroup):
    waiting_query = State()


def ai_search_result_kb(history_id: int) -> object:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📄 JSON",        callback_data=f"export:json:{history_id}"),
        InlineKeyboardButton(text="📑 PDF",         callback_data=f"export:pdf:{history_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Новый поиск", callback_data="ai_search:new"),
        InlineKeyboardButton(text="◀️ Меню",        callback_data="menu:main"),
    )
    return builder.as_markup()


@router.callback_query(F.data == "menu:ai_analyze")
@router.callback_query(F.data == "ai_search:new")
async def cb_ai_search_start(call: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        mode = user.work_mode if user else "standard"
        cost = MODE_COSTS.get(mode, 10)

    await state.set_state(AISearchState.waiting_query)
    text = (
        "╔══════════════════════════════╗\n"
        "║  🤖  A I  П О И С К          ║\n"
        "╚══════════════════════════════╝\n\n"
        f"🎮 Режим: <b>{mode.upper()}</b> | 🪙 Стоимость: <b>{cost}</b>\n\n"
        "Введите запрос — бот найдёт совпадения\n"
        "во <b>всех</b> подключённых базах данных:\n\n"
        "• Telegram Users (520k+)\n"
        "• EyeOfGod база (774k)\n"
        "• Госуслуги ЕСИА\n"
        "• Convoy Donations\n"
        "• Telegram Chats 2022 (63kk)\n"
        "• Ваши загруженные файлы\n\n"
        "✏️ <b>Введите имя, username, телефон, email или ID:</b>"
    )
    await call.message.edit_text(text, reply_markup=cancel_kb(), parse_mode="HTML")
    await call.answer()


@router.message(AISearchState.waiting_query)
async def process_ai_search(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query or len(query) < 2:
        await message.answer("❌ Запрос слишком короткий. Минимум 2 символа.", reply_markup=cancel_kb())
        return

    await state.clear()
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        if not user:
            await message.answer("Напишите /start")
            return

        mode = user.work_mode
        cost = MODE_COSTS.get(mode, 10)
        lang = user.language_code or "ru"

        # Проверка баланса
        token_svc = TokenService(session)
        if not await token_svc.can_afford(user_id, mode):
            await message.answer(
                T.NOT_ENOUGH_TOKENS.format(balance=user.token_balance, cost=cost),
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
            return

        # Прогресс
        progress = await message.answer(
            f"⏳ <b>NEXUS SCANNING...</b>\n\n"
            f"🔍 Запрос: <code>{query}</code>\n"
            f"🎮 Режим: <b>{mode.upper()}</b>\n\n"
            f"<code>▓▓▓░░░░░░░ 30%</code>\n"
            f"<i>Поиск в базах данных...</i>",
            parse_mode="HTML",
        )

        # Создаём запись в истории
        search_repo = SearchRepository(session)
        history = await search_repo.create(user_id, query, mode)
        await session.commit()

        try:
            # Обновляем прогресс
            await progress.edit_text(
                f"🤖 <b>AI АНАЛИЗ...</b>\n\n"
                f"🔍 Запрос: <code>{query}</code>\n\n"
                f"<code>▓▓▓▓▓▓▓░░░ 70%</code>\n"
                f"<i>Обработка результатов...</i>",
                parse_mode="HTML",
            )

            # Поиск
            searcher = UniversalSearch(session)
            result = await searcher.search(query, user_id, mode, lang)

            # Списываем токены
            ok, new_balance = await token_svc.deduct(user_id, mode, f"AI Search: {query[:50]}")
            await repo.increment_requests(user_id)

            # Сохраняем результат
            ai = result.get("ai_report", {})
            confidence = ai.get("confidence", 0.0)
            await search_repo.update_result(
                record_id=history.id,
                tokens_spent=cost,
                results_count=result["total_found"],
                confidence_score=confidence,
                result_summary=ai.get("summary", ""),
                result_data=result,
            )
            await session.commit()

            # Форматируем ответ
            total = result["total_found"]

            if total == 0:
                await progress.edit_text(
                    f"╔══════════════════════════════╗\n"
                    f"║   ❌  НЕТ РЕЗУЛЬТАТОВ        ║\n"
                    f"╚══════════════════════════════╝\n\n"
                    f"🔍 Запрос: <code>{query}</code>\n\n"
                    f"По данному запросу совпадений не найдено\n"
                    f"ни в одной из подключённых баз данных.\n\n"
                    f"💡 Попробуйте другой формат запроса.",
                    reply_markup=ai_search_result_kb(history.id),
                    parse_mode="HTML",
                )
                return

            # Источники
            sources = result.get("sources_searched", {})
            sources_text = "\n".join(
                f"  • {src}: <b>{cnt}</b> записей"
                for src, cnt in sorted(sources.items(), key=lambda x: -x[1])
            ) or "  • Нет данных"

            # Топ результаты
            top_results = result.get("results", [])[:5]
            results_preview = []
            for i, r in enumerate(top_results, 1):
                parts = []
                if r.get("username"):
                    parts.append(f"@{r['username']}")
                if r.get("first_name") or r.get("last_name"):
                    name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                    parts.append(name)
                if r.get("phone"):
                    parts.append(f"📞 {r['phone']}")
                if r.get("email"):
                    parts.append(f"📧 {r['email']}")
                if r.get("tg_id"):
                    parts.append(f"🆔 {r['tg_id']}")
                src = r.get("_source", "")
                score = r.get("_score", 0)
                line = f"<b>{i}.</b> {' | '.join(parts) or 'N/A'}"
                if score:
                    line += f" [{score:.0%}]"
                if src:
                    line += f"\n   <i>📂 {src[:60]}</i>"
                results_preview.append(line)

            # AI данные
            findings = ai.get("key_findings", [])
            findings_text = "\n".join(f"  ▸ {f}" for f in findings[:4]) or "  ▸ Нет"
            risk_icons = {"none": "🟢", "low": "🟡", "medium": "🟠", "high": "🔴"}
            risk = ai.get("risk_level", "none")
            risk_display = f"{risk_icons.get(risk, '⚪')} {risk.upper()}"

            text = (
                f"╔══════════════════════════════╗\n"
                f"║   📊  Р Е З У Л Ь Т А Т     ║\n"
                f"╚══════════════════════════════╝\n\n"
                f"🔍 Запрос: <code>{query}</code>\n"
                f"🎮 Режим: <b>{mode.upper()}</b>\n"
                f"📦 Найдено: <b>{total}</b> совпадений\n"
                f"🪙 Потрачено: <b>{cost}</b> токенов\n"
                f"💰 Остаток: <b>{new_balance}</b> токенов\n\n"
                f"<b>━━━ AI АНАЛИЗ ━━━</b>\n"
                f"{ai.get('summary', 'Нет данных')}\n\n"
                f"📊 <b>Confidence: {int(confidence * 100)}%</b>\n"
                f"⚠️ <b>Risk Level: {risk_display}</b>\n\n"
                f"<b>━━━ ТОП СОВПАДЕНИЯ ━━━</b>\n"
                f"{chr(10).join(results_preview)}\n\n"
                f"<b>━━━ ИСТОЧНИКИ ━━━</b>\n"
                f"{sources_text}\n\n"
                f"<b>━━━ КЛЮЧЕВЫЕ НАХОДКИ ━━━</b>\n"
                f"{findings_text}"
            )

            await progress.edit_text(
                text,
                reply_markup=ai_search_result_kb(history.id),
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error(f"AI search error for user {user_id}: {e}")
            await search_repo.update_result(history.id, 0, 0, 0.0, "Error", {}, "failed")
            await session.commit()
            await progress.edit_text(
                f"❌ Ошибка поиска: {str(e)[:100]}",
                reply_markup=main_menu_kb(),
            )
