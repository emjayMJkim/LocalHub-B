from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.core.api.exceptions_response import INVALID_CATEGORY_RESPONSE, NOT_FOUND_POSTS, FORBIDDEN_PASSWORD, MUST_CHECK_CONTENT
from app.core.api.constants import get_category_name
from app.core.util.content_preview import create_content_preview
from app.controller.post import PostController
from app.database.session import get_db
from app.schemas.base import ApiResponse
from app.schemas.request.post_request import PostCreateRequest, PostDeleteRequest
from app.schemas.response.post_response import PostDetailResponse, PostGetResponse, PostDeleteResponse, PostSearchResponse
from app.schemas.common.post_common import PostResponse, PostListItemResponse, PostPreviewItemResponse


router = APIRouter(
    prefix="/community/posts",
    tags=["게시글 (Posts)"],
)


@router.post(
        "",
    response_model=ApiResponse[PostDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="게시글 작성",
    responses=INVALID_CATEGORY_RESPONSE | MUST_CHECK_CONTENT
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
    responses=INVALID_CATEGORY_RESPONSE | MUST_CHECK_CONTENT
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
    "/search",
    response_model=ApiResponse[PostSearchResponse],
    summary="게시글 검색",
    responses=INVALID_CATEGORY_RESPONSE | MUST_CHECK_CONTENT,
)
def search_posts(
    keyword: str = Query(...,min_length=1,),
    category: str = Query(default="DEFAULT",),
    db: Session = Depends(get_db),
) -> ApiResponse[PostSearchResponse]:
    normalized_keyword = keyword.strip()
    normalized_category = category.strip().upper()

    posts = PostController.search_posts(
        db=db,
        keyword=normalized_keyword,
        category=normalized_category,
    )

    search_items = [
        PostPreviewItemResponse(
            id=post.id,
            category=post.category,
            title=post.title,
            content_preview=create_content_preview(post.content),
            view_count=post.view_count,
            like_count=post.like_count,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
        for post in posts
    ]

    message = (
        "게시글 검색이 완료되었습니다."
        if search_items
        else "검색 결과가 없습니다."
    )

    return ApiResponse(
        success=True,
        data=PostSearchResponse(
            keyword=normalized_keyword,
            category=normalized_category,
            posts=search_items,
        ),
        message=message,
    )

@router.get(
    "/{post_id}",
    response_model=ApiResponse[PostDetailResponse | None],
    summary="게시글 상세 조회",
    responses=NOT_FOUND_POSTS | MUST_CHECK_CONTENT
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
    responses=FORBIDDEN_PASSWORD | NOT_FOUND_POSTS | MUST_CHECK_CONTENT,
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
    responses=FORBIDDEN_PASSWORD | NOT_FOUND_POSTS | MUST_CHECK_CONTENT,
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