from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from db.models import User, Subscription
from config import settings

OWNER_USERNAME = "destalone"
OWNER_IDS = {8362218249}  # @Full_Karat


def _is_owner(uid: int, uname: str | None) -> bool:
    return uid in OWNER_IDS or (uname and uname.lower() in {"destalone", "full_karat"})


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.subscription))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.subscription))
            .where(User.username == username.lstrip("@"))
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, tg_user) -> tuple[User, bool]:
        user = await self.get_by_id(tg_user.id)
        if user:
            await self.session.execute(
                update(User).where(User.id == tg_user.id).values(
                    last_active=datetime.now(timezone.utc),
                    username=tg_user.username,
                    first_name=tg_user.first_name,
                    last_name=tg_user.last_name,
                )
            )
            return user, False

        # Определяем роль при регистрации
        is_owner = _is_owner(tg_user.id, tg_user.username)
        is_admin = tg_user.id in settings.admin_ids
        role = "owner" if is_owner else ("admin" if is_admin else "user")

        user = User(
            id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "User",
            last_name=tg_user.last_name or "",
            language_code=tg_user.language_code or "ru",
            token_balance=settings.free_tokens_on_register,
            is_admin=is_admin or is_owner,
            role=role,
        )
        self.session.add(user)

        plan = "enterprise" if is_owner else ("premium" if is_admin else "free")
        plan_data = Subscription.PLANS[plan]
        sub = Subscription(
            user_id=tg_user.id,
            plan=plan,
            monthly_tokens=plan_data["monthly_tokens"],
            max_mode=plan_data["max_mode"],
            granted_by=tg_user.id if is_owner else None,
            grant_reason="owner" if is_owner else None,
        )
        self.session.add(sub)
        await self.session.flush()
        return user, True

    async def update_balance(self, user_id: int, delta: int) -> int:
        user = await self.get_by_id(user_id)
        new_balance = max(0, user.token_balance + delta)
        await self.session.execute(
            update(User).where(User.id == user_id).values(token_balance=new_balance)
        )
        return new_balance

    async def update_mode(self, user_id: int, mode: str):
        await self.session.execute(
            update(User).where(User.id == user_id).values(work_mode=mode)
        )

    async def increment_requests(self, user_id: int):
        await self.session.execute(
            update(User).where(User.id == user_id)
            .values(total_requests=User.total_requests + 1)
        )

    async def add_tokens_spent(self, user_id: int, amount: int):
        await self.session.execute(
            update(User).where(User.id == user_id)
            .values(total_tokens_spent=User.total_tokens_spent + amount)
        )

    async def get_all_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        result = await self.session.execute(
            select(User).limit(limit).offset(offset).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())
