from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controller.post import PostController
from app.database.session import get_db
from app.schemas.base import ApiResponse
from app.schemas.post import (
    PostCreateResponse,
    PostCreateRequest,
    PostResponse,
)
from app.core.api.exceptions_response import INVALID_CATEGORY_RESPONSE


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