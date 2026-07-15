import json

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.controller.chat import ChatController
from app.schemas.base import ApiResponse
from app.schemas.request.chat_request import ChatRequest
from app.schemas.response.chat_response import ChatResponse

router = APIRouter(prefix="/chat", tags=["챗봇 (Chat)"])


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="챗봇 응답 생성",
)
def create_chat(request: ChatRequest):
    print("[chat] request received", request.model_dump())

    normalized_messages = [
        message.model_dump() if hasattr(message, "model_dump") else message
        for message in request.messages
    ]

    stream_kwargs = {
        "model": None,
        "messages": normalized_messages,
        "response_format": request.response_format,
    }

    if getattr(request, "stream", False):
        def event_generator():
            try:
                for chunk in ChatController.stream_chat_completion(**stream_kwargs):
                    yield f"data: {json.dumps({'delta': chunk})}\n\n"
            except Exception as exc:
                print("[chat] stream route error", exc)
                yield f"data: {json.dumps({'delta': '현재 서버에서 외부 AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.'})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    payload = ChatController.create_chat_completion(
        **{**stream_kwargs, "stream": False},
    )

    return ApiResponse(
        success=True,
        data=ChatResponse.model_validate(payload),
        message="챗봇 응답을 생성했습니다.",
    )
