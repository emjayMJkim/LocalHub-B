from fastapi import APIRouter

from app.router.default import router as default_router
from app.router.v1.post import router as post_router
from app.router.v1.location import router as location_router
from app.router.v1.category import router as category_router

api_router = APIRouter()

api_router.include_router(default_router)
api_router.include_router(post_router)
api_router.include_router(location_router)
api_router.include_router(category_router)