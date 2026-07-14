from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

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

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "message": exc.detail
        },
    )

app.include_router(
    api_router,
    prefix=settings.api_v1_prefix
)
