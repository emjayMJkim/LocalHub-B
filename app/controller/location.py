from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.util.constants import CATEGORY_NAME, CATEGORY_LIST
from app.core.exceptions.exceptions import InvalidCategoryException, LocationNotFoundException
from app.model.location import Location


class LocationController:
    @staticmethod
    def get_location_infos(
        db: Session,
        category: str,
    ) -> list[Location]:
        normalized_category = category.strip().upper()

        if normalized_category not in CATEGORY_LIST:
            raise InvalidCategoryException()
        
        # DEFAULT: 각 카테고리별 첫 번째 장소 1개씩 조회
        if normalized_category == "DEFAULT":
            ranked_places = (
                select(
                    Location.contentid.label("contentid"),
                    func.row_number()
                    .over(
                        partition_by=Location.contentType,
                        order_by=Location.title.asc(),
                    )
                    .label("row_number"),
                )
                .subquery()
            )

            statement = (
                select(Location)
                .join(
                    ranked_places,
                    Location.contentid == ranked_places.c.contentid,
                )
                .where(ranked_places.c.row_number == 1)
                .order_by(Location.contentType.asc())
            )

            return list(db.scalars(statement).all())

        content_type = CATEGORY_NAME[normalized_category]

        statement = (
            select(Location)
            .where(Location.contentType == content_type)
            .order_by(Location.title.asc())
        )

        return list(db.scalars(statement).all())
    
    @staticmethod
    def get_location_detail(
        db: Session,
        content_id: int,
    ) -> Location | None:
        
        location_detail = db.get(Location, str(content_id))

        if location_detail is None:
            raise LocationNotFoundException

        try:
            return location_detail
    
        except SQLAlchemyError as error:
                db.rollback()

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="지역 정보 상세 조회 중 오류가 발생했습니다.",
                ) from error
