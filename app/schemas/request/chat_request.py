from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(default="user")
    content: str = Field(default="")


class ChatRequest(BaseModel):
    messages: list[ChatMessage] | list[dict[str, Any]] = Field(
        ...,
        description="OpenAI API 포맷의 대화 히스토리",
    )
    stream: bool = Field(default=False)
