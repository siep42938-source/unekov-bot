import json
import logging
import io
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from db.database import AsyncSessionLocal
from db.repositories import SearchRepository
from bot.keyboards import main_menu_kb

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("export:json:"))
async def cb_export_json(call: CallbackQuery):
    history_id = int(call.data.split("export:json:")[1])
    await call.answer("⏳ Генерирую JSON...")

    async with AsyncSessionLocal() as session:
        repo = SearchRepository(session)
        record = await repo.get_by_id(history_id)

    if not record or record.user_id != call.from_user.id:
        await call.answer("❌ Запись не найдена", show_alert=True)
        return

    export_data = {
        "query": record.query,
        "mode": record.mode,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "results_count": record.results_count,
        "confidence_score": record.confidence_score,
        "summary": record.result_summary,
        "data": record.result_data,
    }

    json_bytes = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
    file = BufferedInputFile(json_bytes, filename=f"unekov_report_{history_id}.json")
    await call.message.answer_document(file, caption="📄 Экспорт результатов — Unekov.help")


@router.callback_query(F.data.startswith("export:pdf:"))
async def cb_export_pdf(call: CallbackQuery):
    history_id = int(call.data.split("export:pdf:")[1])
    await call.answer("⏳ Генерирую PDF...")

    async with AsyncSessionLocal() as session:
        repo = SearchRepository(session)
        record = await repo.get_by_id(history_id)

    if not record or record.user_id != call.from_user.id:
        await call.answer("❌ Запись не найдена", show_alert=True)
        return

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import cm

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("UNEKOV.HELP — AI OSINT Report", styles["Title"]))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(f"Query: {record.query}", styles["Heading2"]))
        story.append(Paragraph(f"Mode: {record.mode.upper()}", styles["Normal"]))
        story.append(Paragraph(f"Results: {record.results_count}", styles["Normal"]))
        story.append(Paragraph(f"Confidence: {int((record.confidence_score or 0) * 100)}%", styles["Normal"]))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("AI Summary:", styles["Heading3"]))
        story.append(Paragraph(record.result_summary or "No summary", styles["Normal"]))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        file = BufferedInputFile(pdf_bytes, filename=f"unekov_report_{history_id}.pdf")
        await call.message.answer_document(file, caption="📑 PDF Отчёт — Unekov.help")

    except ImportError:
        # Fallback: plain text as PDF substitute
        text = (
            f"UNEKOV.HELP Report\n"
            f"Query: {record.query}\n"
            f"Mode: {record.mode}\n"
            f"Results: {record.results_count}\n"
            f"Summary: {record.result_summary or 'N/A'}"
        )
        file = BufferedInputFile(text.encode("utf-8"), filename=f"unekov_report_{history_id}.txt")
        await call.message.answer_document(
            file,
            caption="📄 Отчёт (установите reportlab для PDF): pip install reportlab"
        )
