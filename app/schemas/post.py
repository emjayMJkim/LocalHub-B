from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.category import CategoryCode


class PostCreateRequest(BaseModel):
    category: CategoryCode
    title: str = Field(min_length=1, max_length=100,)
    content: str = Field(min_length=1, max_length=5000,)
    password: str = Field(min_length=2, max_length=20,)

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


class PostCreateResponse(BaseModel):
    post: PostResponse