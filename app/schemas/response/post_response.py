from pydantic import BaseModel, ConfigDict


from app.schemas.common.post_common import PostResponse, PostListItemResponse, PostPreviewItemResponse


class PostDetailResponse(BaseModel):
    post: PostResponse

class PostGetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    category_name: str
    posts: list[PostListItemResponse]

class PostDeleteResponse(BaseModel):
    deleted_post_id: int

class PostSearchResponse(BaseModel):
    keyword: str
    category: str
    posts: list[PostPreviewItemResponse]

class PostLikeResponse(BaseModel):
    post_id: int
    like_count: int