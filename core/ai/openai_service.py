"""
AI Service — поддерживает Groq (бесплатно) и OpenAI.
Groq: llama-3.3-70b-versatile — бесплатно, быстро, качественно.
"""
import json
import logging
from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are NEXUS — advanced AI analytical system for Unekov.help.
Analyze provided data, find connections, assess confidence, generate structured reports.
Always respond in Russian. Be precise and analytical."""

MODE_INSTRUCTIONS = {
    "lite":     "Quick analysis. Brief summary. Max 200 tokens.",
    "standard": "Balanced analysis. Find key connections. Max 500 tokens.",
    "deep":     "Deep analysis. All connections, patterns. Max 1000 tokens.",
    "ultra":    "Ultra-deep reasoning. Full relationship mapping. Max 2000 tokens.",
}

_client = None
_provider = None


def _get_client():
    global _client, _provider

    if _client:
        return _client, _provider

    # 1. Groq (бесплатно — приоритет)
    if settings.groq_api_key:
        try:
            from groq import AsyncGroq
            _client = AsyncGroq(api_key=settings.groq_api_key)
            _provider = "groq"
            logger.info("✅ AI: Groq (llama-3.3-70b) — FREE")
            return _client, _provider
        except ImportError:
            logger.warning("groq not installed, trying OpenAI")

    # 2. OpenAI (если есть ключ)
    if settings.openai_api_key:
        try:
            from openai import AsyncOpenAI
            _client = AsyncOpenAI(api_key=settings.openai_api_key)
            _provider = "openai"
            logger.info("✅ AI: OpenAI GPT-4o-mini")
            return _client, _provider
        except ImportError:
            pass

    # 3. DeepSeek (если есть ключ)
    if settings.deepseek_api_key:
        try:
            from openai import AsyncOpenAI
            _client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
            _provider = "deepseek"
            logger.info("✅ AI: DeepSeek")
            return _client, _provider
        except ImportError:
            pass

    logger.warning("⚠️ No AI provider configured. Add GROQ_API_KEY to .env")
    return None, None


def _get_model(provider: str) -> str:
    models = {
        "groq":     "llama-3.3-70b-versatile",
        "openai":   "gpt-4o-mini",
        "deepseek": "deepseek-chat",
    }
    return models.get(provider, "llama-3.3-70b-versatile")


async def analyze_search_results(
    query: str,
    results: list[dict],
    mode: str = "standard",
    language: str = "ru",
) -> dict:
    """Анализирует результаты поиска через AI."""

    if not results:
        return _empty_report("Данных не найдено.")

    client, provider = _get_client()

    if not client:
        return {
            "summary": f"Найдено {len(results)} совпадений. AI недоступен — добавь GROQ_API_KEY в настройки.",
            "confidence": 0.5,
            "connections": [],
            "entities": [],
            "risk_level": "none",
            "key_findings": [f"Найдено {len(results)} записей"],
            "recommendations": ["Получи бесплатный ключ на console.groq.com"],
        }

    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["standard"])
    results_text = json.dumps(results[:15], ensure_ascii=False, indent=2)
    max_tokens = {"lite": 300, "standard": 600, "deep": 1200, "ultra": 2000}.get(mode, 600)

    prompt = f"""Запрос: "{query}"
Режим: {mode.upper()} — {mode_instruction}
Язык ответа: русский

Данные для анализа:
{results_text}

Верни JSON:
{{
  "summary": "краткий анализ на русском",
  "confidence": 0.0-1.0,
  "risk_level": "none|low|medium|high",
  "key_findings": ["находка 1", "находка 2"],
  "connections": [{{"entity1": "", "entity2": "", "relation": ""}}],
  "entities": [{{"name": "", "type": "", "relevance": 0.0}}],
  "recommendations": ["рекомендация"]
}}"""

    try:
        response = await client.chat.completions.create(
            model=_get_model(provider),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"AI error ({provider}): {e}")
        return {
            "summary": f"Найдено {len(results)} совпадений. Ошибка AI: {str(e)[:80]}",
            "confidence": 0.0,
            "connections": [], "entities": [],
            "risk_level": "none",
            "key_findings": [f"{len(results)} записей найдено"],
            "recommendations": [],
        }


async def get_embedding(text: str) -> list[float]:
    """Эмбеддинги — только OpenAI."""
    if not settings.openai_api_key:
        return []
    try:
        from openai import AsyncOpenAI
        c = AsyncOpenAI(api_key=settings.openai_api_key)
        r = await c.embeddings.create(model=settings.embedding_model, input=text[:8000])
        return r.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return []


def _empty_report(msg: str) -> dict:
    return {
        "summary": msg, "confidence": 0.0,
        "connections": [], "entities": [],
        "risk_level": "none", "key_findings": [], "recommendations": [],
    }
