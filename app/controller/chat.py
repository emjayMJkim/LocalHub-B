from typing import Any

from app.chatbot.chatbot import ChatbotService


class ChatController:
    @staticmethod
    def create_chat_completion(
        *,
        model: str | None,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        stream: bool = False,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        service = ChatbotService()
        return service.create_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            stream=stream,
            response_format=response_format,
        )

    @staticmethod
    def stream_chat_completion(
        *,
        model: str | None,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        response_format: dict[str, Any] | None = None,
    ):
        service = ChatbotService()
        yield from service.stream_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
        )
