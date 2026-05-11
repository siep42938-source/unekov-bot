from fastapi import APIRouter
from .users import router as users_router
from .search import router as search_router
from .admin import router as admin_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
