from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from db.repositories import UserRepository
from api.auth import get_current_user_id
from config import settings

router = APIRouter()


def require_admin(user_id: int = Depends(get_current_user_id)):
    if user_id not in settings.admin_ids:
        raise HTTPException(403, "Admin only")
    return user_id


@router.get("/users")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    admin_id: int = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    repo = UserRepository(session)
    users = await repo.get_all_users(limit=limit, offset=offset)
    return [
        {
            "id": u.id,
            "username": u.username,
            "balance": u.token_balance,
            "plan": u.subscription.plan if u.subscription else "free",
            "total_requests": u.total_requests,
            "is_banned": u.is_banned,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/tokens/grant")
async def grant_tokens(
    target_user_id: int,
    amount: int,
    admin_id: int = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    from core.tokens import TokenService
    svc = TokenService(session)
    new_balance = await svc.credit(target_user_id, amount, "admin", f"Admin grant by {admin_id}")
    await session.commit()
    return {"user_id": target_user_id, "granted": amount, "new_balance": new_balance}


@router.post("/users/{target_id}/ban")
async def ban_user(
    target_id: int,
    admin_id: int = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update
    from db.models import User
    await session.execute(update(User).where(User.id == target_id).values(is_banned=True))
    await session.commit()
    return {"banned": target_id}
