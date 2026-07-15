import os
import json
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 1. 환경 변수 로드
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "localhub.db")
USE_OPENROUTER = os.getenv("USE_OPENROUTER", "false").lower() == "true"

# 2. 클라이언트 초기화 (OpenAI vs OpenRouter)
if USE_OPENROUTER:
    print("🤖 OpenRouter API를 사용하여 챗봇을 시작합니다.")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
else:
    print("🤖 OpenAI API를 사용하여 챗봇을 시작합니다.")
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# 3. 데이터베이스 조회 도구(Tool) 정의
def execute_sqlite_query(query: str) -> str:
    """LLM이 작성한 SQL을 받아 SQLite에서 실행하고 JSON 문자열로 반환합니다."""
    print(f"\n[실행된 SQL Query]\n{query}\n")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        result = [dict(row) for row in rows]
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

tools = [
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
                        "description": "실행할 SQLite SELECT 쿼리문 (BM25, FTS5, Haversine Bounding Box 등 적용)"
                    }
                },
                "required": ["query"],
            },
        }
    }
]

# 4. 시스템 프롬프트 파일에서 읽어오기
def load_system_prompt() -> str:
    BASE_DIR = Path(__file__).resolve().parent
    prompt_file = BASE_DIR / "prompts" / "system_instruction_ko.md"
    
    if not prompt_file.exists():
        print(f"⚠️ 경고: 시스템 프롬프트 파일을 찾을 수 없습니다. ({prompt_file.resolve()})")
        return "당신은 대전·충청권 관광정보 챗봇입니다. 데이터베이스를 조회하여 답변하세요."
    
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()

SYSTEM_PROMPT = load_system_prompt()

# 5. 챗봇 대화 루프
def chat():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() in ['exit', 'quit', '종료']:
            break
            
        messages.append({"role": "user", "content": user_input})
        
        # 1차 LLM 호출 (도구 사용 여부 판단)
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # 도구(SQL 쿼리)를 사용해야 하는 경우
        if tool_calls:
            messages.append(response_message) # Assistant의 Tool call 메시지 추가
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "execute_sqlite_query":
                    query = function_args.get("query")
                    # SQL 실행 및 결과 반환
                    query_result = execute_sqlite_query(query)
                    
                    # Tool 결과를 메시지에 추가
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": query_result,
                    })
            
            # 2차 LLM 호출 (DB 결과를 바탕으로 최종 자연어 응답 생성)
            final_response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
            )
            bot_reply = final_response.choices[0].message.content
        else:
            # 도구 호출이 필요 없는 일반 대답의 경우
            bot_reply = response_message.content
            
        print(f"\n챗봇: {bot_reply}")
        messages.append({"role": "assistant", "content": bot_reply})

if __name__ == "__main__":
    chat()