from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=['테스트 (Default)'])

@router.get("/", summary="서버 테스트")
def root():
    return {
        "success": True,
        "data": {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
        },
        "message": "지역정보 커뮤니티 Server is running",
    }