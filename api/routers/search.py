from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from db.repositories import UserRepository
from core.search.universal_search import UniversalSearch
from core.tokens import TokenService
from api.auth import get_current_user_id

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    mode: str = "standard"


@router.post("/")
async def search(
    req: SearchRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    if len(req.query.strip()) < 2:
        raise HTTPException(400, "Query too short")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    token_svc = TokenService(session)
    if not await token_svc.can_afford(user_id, req.mode):
        raise HTTPException(402, "Insufficient tokens")

    searcher = UniversalSearch(session)
    result = await searcher.search(req.query, user_id, req.mode, user.language_code or "en")

    await token_svc.deduct(user_id, req.mode, f"API search: {req.query[:50]}")
    await repo.increment_requests(user_id)
    await session.commit()

    return result
