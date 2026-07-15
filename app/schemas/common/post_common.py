from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    title: str
    content: str
    view_count: int
    like_count: int
    created_at: datetime
    updated_at: datetime | None

class PostListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    title: str
    view_count: int
    like_count: int
    created_at: datetime
    updated_at: datetime | None