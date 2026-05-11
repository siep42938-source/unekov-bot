from aiogram import Router
from .start import router as start_router
from .search import router as search_router
from .ai_search import router as ai_search_router
from .tools import router as tools_router
from .tg_users import router as tg_users_router
from .databases import router as databases_router
from .profile import router as profile_router
from .mode import router as mode_router
from .export import router as export_router
from .admin import router as admin_router

main_router = Router()
main_router.include_routers(
    admin_router,       # admin first — приоритет команд
    start_router,
    ai_search_router,
    search_router,
    tools_router,
    tg_users_router,
    databases_router,
    profile_router,
    mode_router,
    export_router,
)

__all__ = ["main_router"]
