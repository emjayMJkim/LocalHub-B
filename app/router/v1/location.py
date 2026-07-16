from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controller.location import LocationController
from app.core.util.constants import get_category_name, get_category_code_by_content_type
from app.core.util.content_view import combine_address, select_image_url
from app.core.exceptions.exceptions_response import INVALID_CATEGORY_RESPONSE, NOT_FOUND_LOCATIONS
from app.database.session import get_db
from app.schemas.base import ApiResponse
from app.schemas.common.location_common import LocationListItemResponse
from app.schemas.response.location_response import LocationInfoListResponse, LocationInfoDetailResponse


router = APIRouter(
    prefix="/location",
    tags=["지역 정보 (Locations)"],
)


@router.get(
    "/detail/{content_id}",
    response_model=ApiResponse[LocationInfoDetailResponse | None],
    summary="특정 지역 정보 상세 조회",
    responses=NOT_FOUND_LOCATIONS
)
def get_location_detail(
    content_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[LocationInfoDetailResponse | None]:
    place = LocationController.get_location_detail(
        db=db,
        content_id=content_id,
    )

    category = get_category_code_by_content_type(
        place.contentType or ""
    )
    category_name = get_category_name(category)

    title = place.title or ""

    return ApiResponse(
        success=True,
        data=LocationInfoDetailResponse(
            category=category,
            category_name=category_name,
            location=LocationListItemResponse(
                content_id=place.contentid or "",
                title=title,
                phone=(
                    place.tel.strip()
                    if place.tel and place.tel.strip()
                    else " - "
                ),
                address=(
                    combine_address(
                        addr1=place.addr1,
                        addr2=place.addr2,
                    )
                    or " - "
                ),
                image_url=(
                    select_image_url(
                        firstimage=place.firstimage,
                        firstimage2=place.firstimage2,
                    )
                    or ""
                ),
                mapx=(
                    place.mapx
                    if place.mapx is not None
                    else None
                ),
                mapy=(
                    place.mapy
                    if place.mapy is not None
                    else None
                ),
                createdtime=place.createdtime or "",
            ),
        ),
        message=f"{title} 정보를 조회했습니다.",
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
            content_id=place.contentid or "",
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
            mapx=place.mapx or 0.0,
            mapy=place.mapy or 0.0,
            createdtime=place.createdtime or ""
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