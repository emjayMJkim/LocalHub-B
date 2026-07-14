from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI

from app.core.config import settings
from app.router.router import api_router
from app.database.init_db import init_db

@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    init_db()
    yield

app = FastAPI(
    title = settings.app_name,
    version = settings.app_version,
    lifespan=lifespan
)

app.include_router(
    api_router,
    prefix=settings.api_v1_prefix
)
