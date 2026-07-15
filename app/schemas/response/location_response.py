from pydantic import BaseModel

from app.schemas.common.location_common import LocationListItemResponse


class LocationInfoListResponse(BaseModel):
    category: str
    category_name: str
    items: list[LocationListItemResponse]