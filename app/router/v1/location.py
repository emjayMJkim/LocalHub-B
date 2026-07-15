from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controller.location import LocationController
from app.core.util.constants import get_category_name
from app.core.util.content_view import combine_address, select_image_url
from app.core.exceptions.exceptions_response import INVALID_CATEGORY_RESPONSE
from app.database.session import get_db
from app.schemas.base import ApiResponse
from app.schemas.common.location_common import LocationListItemResponse
from app.schemas.response.location_response import LocationInfoListResponse


router = APIRouter(
    prefix="/location",
    tags=["지역 정보 (Locations)"],
)


@router.get(
    "/{category}",
    response_model=ApiResponse[LocationInfoListResponse],
    summary="카테고리별 지역 정보 조회",
    responses=INVALID_CATEGORY_RESPONSE,
)
def get_locations(
    category: str,
    db: Session = Depends(get_db),
) -> ApiResponse[LocationInfoListResponse]:
    normalized_category = category.strip().upper()

    places = LocationController.get_location_infos(
        db=db,
        category=normalized_category,
    )

    category_name = get_category_name(normalized_category)

    items = [
        LocationListItemResponse(
            title=place.title or "",
            phone=place.tel.strip() if place.tel and place.tel.strip() else "",
            address=combine_address(
                addr1=place.addr1,
                addr2=place.addr2,
            ) or "",
            image_url=select_image_url(
                firstimage=place.firstimage,
                firstimage2=place.firstimage2,
            ) or "",
        )
        for place in places
    ]

    message = (
        f"{category_name} 카테고리 정보를 조회했습니다."
        if items
        else "등록된 카테고리 정보가 없습니다."
    )

    return ApiResponse(
        success=True,
        data=LocationInfoListResponse(
            category=normalized_category,
            category_name=category_name,
            items=items,
        ),
        message=message,
    )