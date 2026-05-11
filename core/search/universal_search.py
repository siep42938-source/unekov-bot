"""
UniversalSearch — главный движок поиска.
Ищет совпадения во ВСЕХ источниках:
  1. PostgreSQL TelegramUsers (отдельная таблица)
  2. IndexedRecords — все проиндексированные файлы (bif BD, TG Users, Chats 63kk)
  3. Загруженные файлы пользователя (CSV/JSON/TXT)
  4. Fuzzy + Semantic re-ranking
  5. AI анализ результатов
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from db.models import TelegramUser, UploadedFile, IndexedRecord
from core.search.fuzzy_search import normalize_query, rank_results
from core.search.file_scanner import scan_file
from core.ai.openai_service import analyze_search_results, get_embedding
from core.search.search_engine import _cosine_similarity

logger = logging.getLogger(__name__)


class UniversalSearch:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self,
        query: str,
        user_id: int,
        mode: str = "standard",
        language: str = "ru",
    ) -> dict:
        """
        Полный поиск по всем источникам.
        Возвращает структурированный отчёт с AI-анализом.
        """
        q = normalize_query(query)
        all_results: list[dict] = []

        # 1. Поиск в TelegramUsers (отдельная таблица)
        tg_results = await self._search_telegram_users(q)
        all_results.extend(tg_results)

        # 2. Поиск в IndexedRecords (bif BD, TG Users файлы, Chats 63kk)
        indexed_results = await self._search_indexed_records(q, mode)
        all_results.extend(indexed_results)

        # 3. Поиск в загруженных файлах пользователя
        file_results = await self._search_user_files(user_id, q)
        all_results.extend(file_results)

        # 4. Fuzzy ranking
        if all_results:
            all_results = rank_results(query, all_results, self._get_search_fields(all_results))

        # 5. Semantic re-ranking для deep/ultra
        if mode in ("deep", "ultra") and all_results:
            all_results = await self._semantic_rerank(query, all_results)

        # 6. AI анализ
        ai_report = await analyze_search_results(
            query=query,
            results=all_results[:20],
            mode=mode,
            language=language,
        )

        return {
            "query": query,
            "mode": mode,
            "total_found": len(all_results),
            "results": all_results[:30],
            "ai_report": ai_report,
            "sources_searched": self._count_sources(all_results),
        }

    async def _search_telegram_users(self, query: str) -> list[dict]:
        """Поиск в таблице telegram_users."""
        try:
            result = await self.session.execute(
                select(TelegramUser).where(
                    or_(
                        func.lower(TelegramUser.username).contains(query.lower()),
                        func.lower(TelegramUser.first_name).contains(query.lower()),
                        func.lower(TelegramUser.last_name).contains(query.lower()),
                        TelegramUser.phone.contains(query),
                        func.cast(TelegramUser.tg_id, type_=None).cast("text") == query,
                    )
                ).limit(50)
            )
            rows = result.scalars().all()
            return [
                {
                    "tg_id": r.tg_id,
                    "username": r.username,
                    "first_name": r.first_name,
                    "last_name": r.last_name,
                    "phone": r.phone,
                    "bio": r.bio,
                    "source": r.source,
                    "source_group": r.source_group,
                    "is_premium": r.is_premium,
                    "_type": "telegram_user",
                    "_source": "TelegramUsers DB",
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"TelegramUser search error: {e}")
            return []

    async def _search_indexed_records(self, query: str, mode: str) -> list[dict]:
        """
        Поиск в IndexedRecords — все проиндексированные файлы:
        bif BD/, Telegram Users/, Telegram_Chats_2022_63kk/
        """
        try:
            q = query.strip().lstrip("@")
            limit = 100 if mode in ("deep", "ultra") else 50

            result = await self.session.execute(
                select(IndexedRecord).where(
                    or_(
                        func.lower(IndexedRecord.username).contains(q.lower()),
                        func.lower(IndexedRecord.first_name).contains(q.lower()),
                        func.lower(IndexedRecord.last_name).contains(q.lower()),
                        IndexedRecord.phone.contains(q),
                        func.lower(IndexedRecord.email).contains(q.lower()),
                        IndexedRecord.tg_id == q,
                        IndexedRecord.raw.ilike(f"%{q}%"),
                    )
                ).limit(limit)
            )
            rows = result.scalars().all()
            return [
                {
                    "tg_id": r.tg_id,
                    "username": r.username,
                    "first_name": r.first_name,
                    "last_name": r.last_name,
                    "phone": r.phone,
                    "email": r.email,
                    "raw_preview": r.raw[:200] if r.raw else None,
                    "_type": "indexed_record",
                    "_source": f"DB: {r.source_tag} / {r.source_file}",
                    "_source_tag": r.source_tag,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"IndexedRecord search error: {e}")
            return []

    async def _search_user_files(self, user_id: int, query: str) -> list[dict]:
        """Поиск в загруженных файлах пользователя."""
        try:
            result = await self.session.execute(
                select(UploadedFile).where(
                    UploadedFile.user_id == user_id,
                    UploadedFile.is_active == True,
                    UploadedFile.is_indexed == True,
                )
            )
            files = result.scalars().all()
            all_file_results = []
            for f in files:
                hits = scan_file(f.file_path, query)
                for hit in hits:
                    hit["_type"] = "file_record"
                    hit["_source"] = f"File: {f.original_name}"
                all_file_results.extend(hits)
            return all_file_results
        except Exception as e:
            logger.error(f"File search error: {e}")
            return []

    def _get_search_fields(self, results: list[dict]) -> list[str]:
        fields = set()
        for r in results[:5]:
            fields.update(k for k in r.keys() if not k.startswith("_"))
        return list(fields)

    async def _semantic_rerank(self, query: str, results: list[dict]) -> list[dict]:
        try:
            q_emb = await get_embedding(query)
            if not q_emb:
                return results
            for r in results:
                text_repr = " ".join(str(v) for k, v in r.items() if not k.startswith("_") and v)
                emb = await get_embedding(text_repr[:500])
                r["_semantic"] = round(_cosine_similarity(q_emb, emb), 3) if emb else 0.0
            return sorted(results, key=lambda x: x.get("_semantic", 0), reverse=True)
        except Exception as e:
            logger.warning(f"Semantic rerank error: {e}")
            return results

    def _count_sources(self, results: list[dict]) -> dict:
        counts: dict[str, int] = {}
        for r in results:
            src = r.get("_source", "unknown")
            counts[src] = counts.get(src, 0) + 1
        return counts
