from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from datetime import datetime

from app.model.post import Post
from app.schemas.request.post_request import PostCreateRequest
from app.core.api.constants import CATEGORY_LIST
from app.core.api.exceptions import InvalidCategoryException, InvalidPasswordException, PostNotFoundException 


class PostController:
    @staticmethod
    def create_post(
        db: Session,
        request: PostCreateRequest,
    ) -> Post:
        if request.category not in CATEGORY_LIST:
            raise InvalidCategoryException()

        new_post = Post(
            category=request.category,
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
    

    @staticmethod
    def get_posts(
        db: Session,
        category: str,
    ) -> list[Post]:

        category = category.upper()

        # DEFAULT -> 전체 조회
        if category == "DEFAULT":

            posts = (
                db.execute(
                    select(Post).order_by(Post.created_at.desc())
                )
                .scalars()
                .all()
            )

            return posts

        # 카테고리 검증
        if category not in CATEGORY_LIST:
            raise InvalidCategoryException()

        posts = (
            db.execute(
                select(Post)
                .where(Post.category == category)
                .order_by(Post.created_at.desc())
            )
            .scalars()
            .all()
        )

        return posts
    

    @staticmethod
    def get_post_detail(
        db: Session,
        post_id: int,
    ) -> Post | None:
        post = db.get(Post, post_id)

        if post is None:
            raise PostNotFoundException()

        try:
            post.view_count += 1

            db.commit()
            db.refresh(post)

            return post

        except SQLAlchemyError as error:
            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="게시글 상세 조회 중 오류가 발생했습니다.",
            ) from error


    @staticmethod
    def update_post(
        db: Session,
        post_id: int,
        request: PostCreateRequest,
    ) -> Post:

        if request.category not in CATEGORY_LIST:
            raise InvalidCategoryException()

        post = db.get(Post, post_id)

        if post is None:
            raise PostNotFoundException()

        if post.password != request.password:
            raise InvalidPasswordException()

        post.category = request.category
        post.title = request.title
        post.content = request.content
        post.updated_at = datetime.now()

        try:

            db.commit()
            db.refresh(post)

            return post

        except SQLAlchemyError as error:

            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="게시글 수정 중 오류가 발생했습니다."
            ) from error


    @staticmethod
    def delete_post(
        db: Session,
        post_id: int,
        password: str,
    ) -> int:
        post = db.get(Post, post_id)

        if post is None:
            raise PostNotFoundException()

        if post.password != password:
            raise InvalidPasswordException()

        try:
            db.delete(post)
            db.commit()

            return post_id

        except SQLAlchemyError as error:
            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="게시글 삭제 중 오류가 발생했습니다.",
            ) from error