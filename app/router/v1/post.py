from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.api.exceptions_response import INVALID_CATEGORY_RESPONSE
from app.core.api.constants import get_category_name
from app.controller.post import PostController
from app.database.session import get_db
from app.schemas.base import ApiResponse
from app.schemas.request.post_request import PostCreateRequest
from app.schemas.response.post_response import PostCreateResponse, PostGetResponse, PostListItemResponse
from app.schemas.common.post_common import PostResponse


router = APIRouter(
    prefix="/community/posts",
    tags=["게시글 (Posts)"],
)


@router.post(
        "",
    response_model=ApiResponse[PostCreateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="게시글 작성",
    responses=INVALID_CATEGORY_RESPONSE
)
def create_post(
    request: PostCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[PostCreateResponse]:
    post = PostController.create_post(
        db=db,
        request=request,
    )

    return ApiResponse(
        success=True,
        data=PostCreateResponse(
            post=PostResponse.model_validate(post),
        ),
        message="게시글이 작성되었습니다.",
    )

@router.get(
    "/{category}",
    response_model=ApiResponse[PostGetResponse],
    summary="카테고리별 게시글 목록 조회",
    responses=INVALID_CATEGORY_RESPONSE
)
def get_posts(
    category: str,
    db: Session = Depends(get_db),
) -> ApiResponse[PostGetResponse] :
    
    category = category.upper()

    posts = PostController.get_posts(
        db=db,
        category=category,
    )

    category_name = get_category_name(category)

    if not posts:
        message = "등록된 게시글이 없습니다."
    else:
        message = f"{category_name} 카테고리의 게시글 목록을 조회했습니다."

    return ApiResponse(
        success=True,
        data=PostGetResponse(
            category=category,
            category_name=category_name,
            posts=[
                PostListItemResponse.model_validate(post)
                for post in posts
            ],
        ),
        message=message,
    )