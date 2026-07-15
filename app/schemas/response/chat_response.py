from typing import Any

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, Any]


class ChatApiResponse(BaseModel):
    success: bool = True
    data: ChatResponse
    message: str = Field(default="챗봇 응답을 생성했습니다.")
