import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIConnectionError, APIStatusError, OpenAIError


load_dotenv()

DB_PATH = os.getenv("DB_PATH", "localhub.db")
USE_OPENROUTER = os.getenv("USE_OPENROUTER", "false").lower() == "true"


class ChatbotService:
    def __init__(self) -> None:
        if USE_OPENROUTER:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
            )
            self.model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        else:
            self.client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
            )
            self.model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

        self.system_prompt = self._load_system_prompt()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_sqlite_query",
                    "description": "대전·충청권 관광정보 SQLite 데이터베이스에 SELECT 쿼리를 실행하여 정보를 검색합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "실행할 SQLite SELECT 쿼리문 (BM25, FTS5, Haversine Bounding Box 등 적용)",
                            }
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

    def _load_system_prompt(self) -> str:
        base_dir = Path(__file__).resolve().parent
        prompt_file = base_dir / "prompts" / "system_instruction_ko.md"

        if not prompt_file.exists():
            return "당신은 대전·충청권 관광정보 챗봇입니다. 데이터베이스를 조회하여 답변하세요."

        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()

    def execute_sqlite_query(self, query: str) -> str:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            result = [dict(row) for row in rows]
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:  # pragma: no cover - defensive path
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    def create_completion(
        self,
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
        payload = self._build_payload(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            stream=stream,
            response_format=response_format,
        )

        try:
            print("[chat] calling provider with payload", payload)
            response = self.client.chat.completions.create(**payload)
            if stream:
                chunks: list[str] = []
                for chunk in response:
                    delta = getattr(chunk, "choices", [None])[0]
                    if delta is None:
                        continue
                    chunk_delta = getattr(delta, "delta", None)
                    if chunk_delta is None:
                        continue
                    content = getattr(chunk_delta, "content", None)
                    if content:
                        chunks.append(content)
                assembled = "".join(chunks)
                return {
                    "id": "streaming",
                    "object": "chat.completion",
                    "created": 0,
                    "model": model or self.model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": assembled,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                }

            print("[chat] provider response ok", response.model_dump().get("id"))
            return self._handle_tool_call_response(
                response=response,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
            )
        except Exception as exc:
            print("[chat] provider error", type(exc).__name__, exc)
            return {
                "id": "chatcmpl-local-fallback",
                "object": "chat.completion",
                "created": 0,
                "model": model or self.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "현재 서버에서 외부 AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }

    def _handle_tool_call_response(
        self,
        *,
        response: Any,
        model: str | None,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response_payload = response.model_dump() if hasattr(response, "model_dump") else response
        tool_calls = self._extract_tool_calls(response_payload)
        if not tool_calls:
            return response_payload

        conversation_messages = self._normalize_messages(messages)
        conversation_messages = self._prepend_system_prompt(conversation_messages)
        conversation_messages.append(self._build_assistant_tool_message(response_payload))

        for tool_call in tool_calls:
            function_name = tool_call.get("function", {}).get("name")
            arguments = tool_call.get("function", {}).get("arguments", "{}")
            if function_name != "execute_sqlite_query":
                continue

            try:
                parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
                query = parsed_args.get("query", "")
            except Exception:
                query = str(arguments)

            tool_result = self.execute_sqlite_query(query)
            conversation_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "name": function_name,
                    "content": tool_result,
                }
            )

        # 2차 호출에서는 tools를 전달하지 않음 (자연어 답변 생성만)
        follow_up_payload = self._build_payload(
            model=model,
            messages=conversation_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=None,
            tool_choice=None,
            stream=False,
            response_format=response_format,
        )

        follow_up_response = self.client.chat.completions.create(**follow_up_payload)
        return follow_up_response.model_dump() if hasattr(follow_up_response, "model_dump") else follow_up_response

    def _extract_tool_calls(self, response_payload: dict[str, Any]) -> list[dict[str, Any]]:
        choices = response_payload.get("choices", [])
        if not choices:
            return []
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else getattr(choices[0], "message", None)
        if isinstance(message, dict):
            return message.get("tool_calls", []) or []
        return getattr(message, "tool_calls", []) or []

    def _build_assistant_tool_message(self, response_payload: dict[str, Any]) -> dict[str, Any]:
        choices = response_payload.get("choices", [])
        if not choices:
            return {"role": "assistant", "content": ""}
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else getattr(choices[0], "message", None)
        if isinstance(message, dict):
            return {
                "role": "assistant",
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", []),
            }
        return {
            "role": "assistant",
            "content": getattr(message, "content", ""),
            "tool_calls": getattr(message, "tool_calls", []),
        }

    def _normalize_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for message in messages:
            if hasattr(message, "model_dump"):
                normalized.append(message.model_dump())
            elif isinstance(message, dict):
                normalized.append(dict(message))
            else:
                normalized.append({"role": "user", "content": str(message)})
        return normalized

    def _prepend_system_prompt(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.system_prompt:
            return messages
        if messages and messages[0].get("role") == "system":
            messages[0] = {"role": "system", "content": self.system_prompt}
            return messages
        return [{"role": "system", "content": self.system_prompt}, *messages]

    def stream_completion(
        self,
        *,
        model: str | None,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        response_format: dict[str, Any] | None = None,
    ):
        first_payload = self._build_payload(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            stream=False,
            response_format=response_format,
        )

        try:
            first_response = self.client.chat.completions.create(**first_payload)
            response_payload = first_response.model_dump() if hasattr(first_response, "model_dump") else first_response
            tool_calls = self._extract_tool_calls(response_payload)

            if tool_calls:
                conversation_messages = self._normalize_messages(messages)
                conversation_messages = self._prepend_system_prompt(conversation_messages)
                conversation_messages.append(self._build_assistant_tool_message(response_payload))

                for tool_call in tool_calls:
                    function_name = tool_call.get("function", {}).get("name")
                    arguments = tool_call.get("function", {}).get("arguments", "{}")
                    if function_name != "execute_sqlite_query":
                        continue

                    try:
                        parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
                        query = parsed_args.get("query", "")
                    except Exception:
                        query = str(arguments)

                    tool_result = self.execute_sqlite_query(query)
                    conversation_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", ""),
                            "name": function_name,
                            "content": tool_result,
                        }
                    )

                follow_up_payload = self._build_payload(
                    model=model,
                    messages=conversation_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=None,
                    tool_choice=None,
                    stream=True,
                    response_format=response_format,
                )

                follow_up_stream = self.client.chat.completions.create(**follow_up_payload)
                for chunk in follow_up_stream:
                    delta = getattr(chunk, "choices", [None])[0]
                    if delta is None:
                        continue
                    chunk_delta = getattr(delta, "delta", None)
                    if chunk_delta is None:
                        continue
                    content = getattr(chunk_delta, "content", None)
                    if content:
                        yield content
                return

            content = self._extract_message_content(response_payload)
            if content:
                yield content
        except Exception as exc:
            print("[chat] stream error", type(exc).__name__, exc)
            yield "현재 서버에서 외부 AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요."

    def _extract_message_content(self, response_payload: Any) -> str:
        choices = response_payload.get("choices", []) if isinstance(response_payload, dict) else []
        if not choices:
            if hasattr(response_payload, "choices"):
                choices = response_payload.choices
            else:
                return ""

        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else getattr(choices[0], "message", None)
        if isinstance(message, dict):
            content = message.get("content", "")
        else:
            content = getattr(message, "content", "")

        if isinstance(content, str):
            return content
        if content is None:
            return ""
        return json.dumps(content, ensure_ascii=False)

    def _build_payload(
        self,
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
        normalized_messages: list[dict[str, Any]] = []
        for message in messages:
            if hasattr(message, "model_dump"):
                normalized_messages.append(message.model_dump())
            elif isinstance(message, dict):
                normalized_messages.append(dict(message))
            else:
                normalized_messages.append({"role": "user", "content": str(message)})

        if self.system_prompt:
            if normalized_messages and normalized_messages[0].get("role") == "system":
                normalized_messages[0] = {
                    "role": "system",
                    "content": self.system_prompt,
                }
            else:
                normalized_messages = [
                    {"role": "system", "content": self.system_prompt},
                    *normalized_messages,
                ]

        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": normalized_messages,
            "stream": stream,
        }

        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        # tools 처리: 명시적으로 전달된 경우와 기본값 구분
        if tools is not None:
            if tools:  # 빈 리스트가 아니면 포함
                payload["tools"] = tools
        elif self.tools:  # tools가 None이고 self.tools가 있으면 기본값으로 사용
            payload["tools"] = self.tools
        
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        elif "tools" in payload:  # tools가 포함되었으면 기본 tool_choice 추가
            payload["tool_choice"] = "auto"
        
        if response_format is not None:
            payload["response_format"] = response_format

        return payload
