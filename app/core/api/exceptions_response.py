INVALID_CATEGORY_RESPONSE = {
    400: {
        "description": "잘못된 카테고리",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "data": {},
                    "message": "지원하지 않는 카테고리입니다.",
                }
            }
        },
    }
}

NOT_FOUND_POSTS = {
    404 : {
        "description": "게시글 없음",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "data": {},
                    "message": "게시글을 찾을 수 없습니다.",
                }
            }
        },
    }
}

POST_CREATE_DB_ERROR_RESPONSE = {
    500: {
        "description": "DB 오류",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "data": {},
                    "message": "게시글 작성 중 오류가 발생했습니다.",
                }
            }
        },
    }
}