from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.util.constants import CATEGORY_NAME, CATEGORY_LIST
from app.core.exceptions.exceptions import InvalidCategoryException
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