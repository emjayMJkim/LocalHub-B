from pydantic import BaseModel

from app.schemas.common.category_common import CategoryItemResponse


class CategoryListResponse(BaseModel):
    categories: list[CategoryItemResponse]