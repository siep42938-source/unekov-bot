import logging
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories import UserRepository
from db.models import TokenTransaction
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MODE_COSTS = {
    "lite":     5,
    "standard": 10,
    "deep":     25,
    "ultra":    50,
}

PLAN_MODE_ACCESS = {
    "free":       ["lite", "standard"],
    "premium":    ["lite", "standard", "deep"],
    "enterprise": ["lite", "standard", "deep", "ultra"],
    "vip":        ["lite", "standard", "deep", "ultra"],
}


class TokenService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_balance(self, user_id: int) -> int:
        user = await self.user_repo.get_by_id(user_id)
        return user.token_balance if user else 0

    async def can_afford(self, user_id: int, mode: str) -> bool:
        cost = MODE_COSTS.get(mode, 10)
        balance = await self.get_balance(user_id)
        return balance >= cost

    async def deduct(self, user_id: int, mode: str, description: str = "") -> tuple[bool, int]:
        cost = MODE_COSTS.get(mode, 10)
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.token_balance < cost:
            return False, user.token_balance if user else 0

        new_balance = await self.user_repo.update_balance(user_id, -cost)
        tx = TokenTransaction(
            user_id=user_id,
            amount=-cost,
            balance_after=new_balance,
            reason="search",
            description=description,
            mode=mode,
        )
        self.session.add(tx)
        # Обновляем счётчик потраченных токенов
        await self.user_repo.add_tokens_spent(user_id, cost)
        return True, new_balance

    async def credit(self, user_id: int, amount: int, reason: str, description: str = "") -> int:
        new_balance = await self.user_repo.update_balance(user_id, amount)
        tx = TokenTransaction(
            user_id=user_id,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            description=description,
        )
        self.session.add(tx)
        return new_balance

    async def claim_daily_bonus(self, user_id: int) -> tuple[bool, int]:
        from config import settings
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False, 0
        now = datetime.now(timezone.utc)
        if user.last_daily_bonus:
            last = user.last_daily_bonus
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if (now - last).days < 1:
                return False, user.token_balance

        from sqlalchemy import update
        from db.models import User
        await self.session.execute(
            update(User).where(User.id == user_id).values(last_daily_bonus=now)
        )
        new_balance = await self.credit(
            user_id, settings.daily_free_tokens, "daily_bonus", "Daily bonus"
        )
        return True, new_balance

    def get_mode_cost(self, mode: str) -> int:
        return MODE_COSTS.get(mode, 10)

    def can_use_mode(self, plan: str, mode: str) -> bool:
        allowed = PLAN_MODE_ACCESS.get(plan, ["lite", "standard"])
        return mode in allowed
