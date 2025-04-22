# routes/__init__.py
from fastapi import APIRouter
from .bots import router as bots_router
from .tournaments import router as tournaments_router
from .matches import router as matches_router
from .users import router as users_router

api_v2_router = APIRouter(prefix="/api/v2")

api_v2_router.include_router(bots_router, prefix="/bots", tags=["bots"])
api_v2_router.include_router(tournaments_router, prefix="/tournaments", tags=["tournaments"])
api_v2_router.include_router(matches_router, prefix="/matches", tags=["matches"])
api_v2_router.include_router(users_router, prefix="/users", tags=["users"])