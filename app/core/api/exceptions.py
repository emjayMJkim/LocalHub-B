from fastapi import HTTPException, status


class InvalidCategoryException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원하지 않는 카테고리입니다."
        )