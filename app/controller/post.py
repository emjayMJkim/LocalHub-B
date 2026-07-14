from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.model.post import Post
from app.schemas.post import PostCreateRequest


class PostController:
    @staticmethod
    def create_post(
        db: Session,
        request: PostCreateRequest,
    ) -> Post:
        new_post = Post(
            category=request.category.value,
            title=request.title,
            content=request.content,
            password=request.password,
            view_count=0,
            like_count=0,
        )

        try:
            db.add(new_post) # 세션에 게시글 객체 추가
            db.commit() # SQLite에 실제 저장
            db.refresh(new_post) # 자동 생성된 값 다시 조회

            return new_post

        except SQLAlchemyError as error:
            db.rollback() # 저장 중 오류 발생 시 트랜잭션 취소

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="게시글 작성 중 오류가 발생했습니다.",
            ) from error