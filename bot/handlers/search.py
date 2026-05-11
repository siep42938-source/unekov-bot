import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.database import AsyncSessionLocal
from db.repositories import UserRepository, SearchRepository
from core.tokens import TokenService, MODE_COSTS
from core.search.universal_search import UniversalSearch
from bot.keyboards import search_menu_kb, search_result_kb, cancel_kb, main_menu_kb
from bot import ui_texts as T

router = Router()
logger = logging.getLogger(__name__)


class SearchState(StatesGroup):
    waiting_query = State()


@router.callback_query(F.data == "menu:search")
async def cb_search_menu(call: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(call.from_user.id)
        mode = user.work_mode if user else "standard"
        cost = MODE_COSTS.get(mode, 10)

    text = T.SEARCH_MENU.format(mode=mode.upper(), cost=cost)
    await call.message.edit_text(text, reply_markup=search_menu_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.in_({"search:new", "search:by_name", "search:by_email",
                                    "search:by_phone", "search:by_tgid", "search:cross"}))
async def cb_start_search(call: CallbackQuery, state: FSMContext):
    search_type = call.data.split(":")[1] if ":" in call.data else "new"
    await state.set_state(SearchState.waiting_query)
    await state.update_data(search_type=search_type)

    hints = {
        "by_name":  "Введите имя или @username:",
        "by_email": "Введите email адрес:",
        "by_phone": "Введите номер телефона:",
        "by_tgid":  "Введите Telegram ID (число):",
        "cross":    "Введите запрос для поиска во всех базах:",
        "new":      T.ENTER_QUERY,
    }
    hint = hints.get(search_type, T.ENTER_QUERY)
    await call.message.edit_text(hint, reply_markup=cancel_kb(), parse_mode="HTML")
    await call.answer()


@router.message(SearchState.waiting_query)
async def process_search_query(message: Message, state: FSMContext):
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
        plan = user.subscription.plan if user.subscription else "free"
        lang = user.language_code or "ru"

        # Check balance
        token_svc = TokenService(session)
        if not await token_svc.can_afford(user_id, mode):
            await message.answer(
                T.NOT_ENOUGH_TOKENS.format(balance=user.token_balance, cost=cost),
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
            return

        # Show progress
        progress_msg = await message.answer(
            T.SEARCH_WAITING.format(query=query, mode=mode.upper()),
            parse_mode="HTML",
        )

        # Create history record
        search_repo = SearchRepository(session)
        history = await search_repo.create(user_id, query, mode)
        await session.commit()

        # Run search
        try:
            await progress_msg.edit_text(T.SEARCH_ANALYZING, parse_mode="HTML")
            searcher = UniversalSearch(session)
            result = await searcher.search(query, user_id, mode, lang)

            # Deduct tokens
            ok, new_balance = await token_svc.deduct(user_id, mode, f"Search: {query[:50]}")
            await repo.increment_requests(user_id)

            # Save result
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

            # Format response
            if result["total_found"] == 0:
                text = T.NO_RESULTS.format(query=query)
                await progress_msg.edit_text(text, reply_markup=search_result_kb(history.id), parse_mode="HTML")
                return

            sources_text = "\n".join(
                f"  • {src}: {cnt} записей"
                for src, cnt in result.get("sources_searched", {}).items()
            ) or "  • Нет данных"

            findings = ai.get("key_findings", [])
            findings_text = "\n".join(f"  ▸ {f}" for f in findings[:5]) or "  ▸ Нет"

            risk_icons = {"none": "🟢", "low": "🟡", "medium": "🟠", "high": "🔴"}
            risk = ai.get("risk_level", "none")
            risk_display = f"{risk_icons.get(risk, '⚪')} {risk.upper()}"

            text = T.SEARCH_RESULT.format(
                query=query,
                mode=mode.upper(),
                total=result["total_found"],
                tokens=cost,
                ai_summary=ai.get("summary", "Нет данных"),
                confidence=int(confidence * 100),
                risk=risk_display,
                sources=sources_text,
                findings=findings_text,
            )
            await progress_msg.edit_text(
                text,
                reply_markup=search_result_kb(history.id),
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error(f"Search error for user {user_id}: {e}")
            await search_repo.update_result(
                history.id, 0, 0, 0.0, "Error", {}, "failed"
            )
            await session.commit()
            await progress_msg.edit_text(
                f"❌ Ошибка поиска: {str(e)[:100]}",
                reply_markup=main_menu_kb(),
            )
