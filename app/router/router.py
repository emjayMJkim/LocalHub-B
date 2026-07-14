from fastapi import APIRouter

from app.router.default import router as default_router


api_router = APIRouter()

api_router.include_router(default_router)