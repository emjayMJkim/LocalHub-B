import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIConnectionError, APIStatusError, OpenAIError


load_dotenv()

DB_PATH = os.getenv("DB_PATH", "localhub.db")
USE_OPENROUTER = os.getenv("USE_OPENROUTER", "false").lower() == "true"

ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"chatbot_{datetime.now().strftime('%Y-%m-%d')}.log"

logger = logging.getLogger("localhub.chatbot")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.propagate = False


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
            
            # [수정] 결과가 없을 경우 명시적인 상수 반환
            if not result:
                return "NO_RESULTS_FOUND"
                
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:  # pragma: no cover - defensive path
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    def _log_event(self, event: str, payload: Any) -> None:
        try:
            if isinstance(payload, (dict, list)):
                formatted = json.dumps(payload, ensure_ascii=False, indent=2)
            else:
                formatted = str(payload)
            logger.info("%s | %s", event, formatted)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.info("%s | logging_error: %s", event, exc)

    def _extract_user_messages(self, messages: list[dict[str, Any]]) -> list[str]:
        normalized_messages = self._normalize_messages(messages)
        return [message.get("content", "") for message in normalized_messages if message.get("role") == "user"]

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
        self._log_event("user_input", self._extract_user_messages(messages))

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
            result = self._handle_tool_call_response(
                response=response,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
            )
            return result
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
        
        current_response_payload = response_payload
        current_tool_calls = tool_calls

        # [수정] 다중 도구 호출(Multi-step Tool Calling) 루프
        while current_tool_calls:
            conversation_messages.append(self._build_assistant_tool_message(current_response_payload))

            for tool_call in current_tool_calls:
                function_name = tool_call.get("function", {}).get("name")
                arguments = tool_call.get("function", {}).get("arguments", "{}")
                if function_name != "execute_sqlite_query":
                    continue

                try:
                    parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
                    query = parsed_args.get("query", "")
                except Exception:
                    query = str(arguments)

                # 로그에 SQL 쿼리 기록
                self._log_event("llm_generated_query", query)
                
                tool_result = self.execute_sqlite_query(query)
                
                # 로그에 SQL 실행 결과 기록
                self._log_event("query_execution_result", tool_result)
                
                # 빈 결과에 대한 명시적 안내 주입
                if tool_result == "NO_RESULTS_FOUND":
                    reported_result = "조회된 데이터가 없습니다. 이 경우 반드시 사용자에게 '조건에 맞는 관광 정보를 찾지 못했습니다.'라고 답변하십시오."
                else:
                    reported_result = tool_result

                conversation_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "name": function_name,
                        "content": reported_result,
                    }
                )

            # 도구 실행 결과를 포함하여 LLM 다시 호출
            payload = self._build_payload(
                model=model,
                messages=conversation_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools, # 다중 호출을 위해 tools 유지
                tool_choice=tool_choice,
                stream=False,
                response_format=response_format,
            )

            next_response = self.client.chat.completions.create(**payload)
            current_response_payload = next_response.model_dump() if hasattr(next_response, "model_dump") else next_response
            current_tool_calls = self._extract_tool_calls(current_response_payload)

        # 도구 호출이 끝난 최종 결과 처리
        final_content = self._extract_message_content(current_response_payload)
        self._log_event("llm_final_response", final_content)
        return current_response_payload

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
        self._log_event("user_input", self._extract_user_messages(messages))

        conversation_messages = self._normalize_messages(messages)
        conversation_messages = self._prepend_system_prompt(conversation_messages)

        has_tool_calls = False

        # [수정] 다중 도구 호출(Multi-step Tool Calling) 루프 - 스트리밍용
        while True:
            payload = self._build_payload(
                model=model,
                messages=conversation_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                stream=False, # 도구 호출을 온전히 받기 위해 비스트리밍으로 실행
                response_format=response_format,
            )

            try:
                response = self.client.chat.completions.create(**payload)
                response_payload = response.model_dump() if hasattr(response, "model_dump") else response
                tool_calls = self._extract_tool_calls(response_payload)

                if not tool_calls:
                    if not has_tool_calls:
                        # 최초 호출에서 도구를 전혀 사용하지 않았다면 그대로 단일 출력 후 종료
                        content = self._extract_message_content(response_payload)
                        if content:
                            self._log_event("llm_final_response", content)
                            yield content
                        return
                    else:
                        # 이전 루프에서 도구를 사용했고 이제 답변할 준비가 완료된 경우
                        break

                has_tool_calls = True
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

                    self._log_event("llm_generated_query", query)
                    tool_result = self.execute_sqlite_query(query)
                    self._log_event("query_execution_result", tool_result)

                    if tool_result == "NO_RESULTS_FOUND":
                        reported_result = "조회된 데이터가 없습니다. 이 경우 반드시 사용자에게 '조건에 맞는 관광 정보를 찾지 못했습니다.'라고 답변하십시오."
                    else:
                        reported_result = tool_result

                    conversation_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", ""),
                            "name": function_name,
                            "content": reported_result,
                        }
                    )
            except Exception as exc:
                print("[chat] stream loop error", type(exc).__name__, exc)
                yield "현재 서버에서 외부 AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요."
                return

        # 모든 도구 호출이 끝나면 스트리밍 모드로 최종 응답 생성
        follow_up_payload = self._build_payload(
            model=model,
            messages=conversation_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=None, # 자연어 생성을 강제하기 위해 도구 비활성화
            tool_choice=None,
            stream=True,
            response_format=response_format,
        )

        try:
            follow_up_stream = self.client.chat.completions.create(**follow_up_payload)
            assembled_chunks: list[str] = []
            for chunk in follow_up_stream:
                delta = getattr(chunk, "choices", [None])[0]
                if delta is None:
                    continue
                chunk_delta = getattr(delta, "delta", None)
                if chunk_delta is None:
                    continue
                content = getattr(chunk_delta, "content", None)
                if content:
                    assembled_chunks.append(content)
                    yield content
            self._log_event("llm_final_response", "".join(assembled_chunks))
        except Exception as exc:
            print("[chat] stream final follow-up error", type(exc).__name__, exc)
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

        # temperature와 max_tokens는 None일 경우 기본값을 설정 (넉넉하게 8192 설정)
        payload["temperature"] = 1.0 if temperature is None else temperature
        payload["max_tokens"] = 8192 if max_tokens is None else max_tokens
        
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