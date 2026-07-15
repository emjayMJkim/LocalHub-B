from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.api.exceptions_response import INVALID_CATEGORY_RESPONSE, NOT_FOUND_POSTS, FORBIDDEN_PASSWORD
from app.core.api.constants import get_category_name
from app.controller.post import PostController
from app.database.session import get_db
from app.schemas.base import ApiResponse
from app.schemas.request.post_request import PostCreateRequest, PostDeleteRequest
from app.schemas.response.post_response import PostDetailResponse, PostGetResponse, PostDeleteResponse
from app.schemas.common.post_common import PostResponse, PostListItemResponse


router = APIRouter(
    prefix="/community/posts",
    tags=["게시글 (Posts)"],
)


@router.post(
        "",
    response_model=ApiResponse[PostDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="게시글 작성",
    responses=INVALID_CATEGORY_RESPONSE
)
def create_post(
    request: PostCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[PostDetailResponse]:
    post = PostController.create_post(
        db=db,
        request=request,
    )

    return ApiResponse(
        success=True,
        data=PostDetailResponse(
            post=PostResponse.model_validate(post),
        ),
        message="게시글이 작성되었습니다.",
    )

@router.get(
    "/list/{category}",
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

@router.get(
    "/{post_id}",
    response_model=ApiResponse[PostDetailResponse | None],
    summary="게시글 상세 조회",
    responses=NOT_FOUND_POSTS
)
def get_post_detail(
    post_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[PostDetailResponse | None]:
    post = PostController.get_post_detail(
        db=db,
        post_id=post_id,
    )

    return ApiResponse(
        success=True,
        data=PostDetailResponse(
            post=PostResponse.model_validate(post),
        ),
        message="게시글 상세 정보를 조회했습니다.",
    )

@router.put(
    "/{post_id}",
    response_model=ApiResponse[PostDetailResponse],
    summary="게시글 수정",
    responses=FORBIDDEN_PASSWORD | NOT_FOUND_POSTS,
)
def update_post(
    post_id: int,
    request: PostCreateRequest,
    db: Session = Depends(get_db),
):

    post = PostController.update_post(
        db=db,
        post_id=post_id,
        request=request,
    )

    return ApiResponse(
        success=True,
        data=PostDetailResponse(
            post=PostResponse.model_validate(post)
        ),
        message="게시글이 수정되었습니다."
    )

@router.delete(
    "/{post_id}",
    response_model=ApiResponse[PostDeleteResponse],
    summary="게시글 삭제",
    responses=FORBIDDEN_PASSWORD | NOT_FOUND_POSTS,
)
def delete_post(
    post_id: int,
    request: PostDeleteRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[PostDeleteResponse]:
    deleted_post_id = PostController.delete_post(
        db=db,
        post_id=post_id,
        password=request.password,
    )

    return ApiResponse(
        success=True,
        data=PostDeleteResponse(
            deleted_post_id=deleted_post_id,
        ),
        message="게시글이 삭제되었습니다.",
    )