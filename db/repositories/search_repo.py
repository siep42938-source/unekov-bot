from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from db.models import SearchHistory


class SearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, query: str, mode: str) -> SearchHistory:
        record = SearchHistory(
            user_id=user_id,
            query=query,
            mode=mode,
            status="pending",
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def update_result(
        self,
        record_id: int,
        tokens_spent: int,
        results_count: int,
        confidence_score: float,
        result_summary: str,
        result_data: dict,
        status: str = "completed",
    ):
        from sqlalchemy import update
        await self.session.execute(
            update(SearchHistory)
            .where(SearchHistory.id == record_id)
            .values(
                tokens_spent=tokens_spent,
                results_count=results_count,
                confidence_score=confidence_score,
                result_summary=result_summary,
                result_data=result_data,
                status=status,
            )
        )

    async def get_user_history(
        self, user_id: int, limit: int = 10, offset: int = 0
    ) -> list[SearchHistory]:
        result = await self.session.execute(
            select(SearchHistory)
            .where(SearchHistory.user_id == user_id)
            .order_by(desc(SearchHistory.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> SearchHistory | None:
        result = await self.session.execute(
            select(SearchHistory).where(SearchHistory.id == record_id)
        )
        return result.scalar_one_or_none()
