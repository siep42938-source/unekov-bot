from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from db.repositories import UserRepository
from api.auth import get_current_user_id

router = APIRouter()


@router.get("/me")
async def get_me(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user.id,
        "username": user.username,
        "balance": user.token_balance,
        "plan": user.subscription.plan if user.subscription else "free",
        "mode": user.work_mode,
        "total_requests": user.total_requests,
    }


@router.get("/history")
async def get_history(
    limit: int = 10,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    from db.repositories import SearchRepository
    repo = SearchRepository(session)
    history = await repo.get_user_history(user_id, limit=limit)
    return [
        {
            "id": h.id,
            "query": h.query,
            "mode": h.mode,
            "results_count": h.results_count,
            "confidence": h.confidence_score,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in history
    ]
