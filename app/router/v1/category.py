from fastapi import APIRouter, status

from app.controller.category import CategoryController
from app.schemas.base import ApiResponse
from app.schemas.response.category_response import CategoryListResponse
from app.schemas.common.category_common import CategoryItemResponse


router = APIRouter(
    prefix="/category",
    tags=["카테고리 (Categories)"],
)


@router.get(
    "",
    response_model=ApiResponse[CategoryListResponse],
    summary="카테고리 목록 조회",
)
def get_categories() -> ApiResponse[CategoryListResponse]:
    categories = CategoryController.get_categories()

    return ApiResponse(
        success=True,
        data=CategoryListResponse(
            categories=[
                CategoryItemResponse(**category)
                for category in categories
            ],
        ),
        message="카테고리 목록을 조회했습니다.",
    )