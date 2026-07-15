from pydantic import BaseModel, ConfigDict

from app.schemas.common.post_common import PostResponse, PostListItemResponse


class PostDetailResponse(BaseModel):
    post: PostResponse

class PostGetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    category_name: str
    posts: list[PostListItemResponse]