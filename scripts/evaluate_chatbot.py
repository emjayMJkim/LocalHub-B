import requests
import json
import time
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict

# 프로젝트 루트 경로 설정 (scripts/ 폴더 기준 상위 디렉토리)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "evaluation_dataset.csv"

# API 엔드포인트
API_URL = "http://localhost:8000/api/chat"

# 평가 데이터 로드 (CSV 기준)
def load_dataset(filepath: Path = DATA_PATH) -> List[Dict]:
    # pandas로 CSV 읽기 후 딕셔너리 리스트로 변환
    df = pd.read_csv(filepath)
    return df.to_dict(orient='records')

# API 호출 및 응답 시간 측정
def call_api(query: str, context: str = "") -> dict:
    headers = {'Content-Type': 'application/json'}
    payload = {"query": query, "context": context}
    
    start_time = time.time()
    try:
        # 실제 API 호출 시 아래 주석 해제 및 수정
        # response = requests.post(API_URL, headers=headers, json=payload)
        # response.raise_for_status()
        # response_data = response.json()
        
        # 모의 응답 (테스트용)
        time.sleep(np.random.uniform(0.1, 0.5)) # 가상의 지연 시간
        response_data = {
            "answer": "테스트 응답입니다.", 
            "retrieved_docs": ["테스트 문서 1", "테스트 문서 2"],
            "grounded": True 
        }
        
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        response_data = {"answer": "Error", "retrieved_docs": [], "grounded": False}

    end_time = time.time()
    response_time = end_time - start_time
    
    return {
        "answer": response_data.get("answer", ""),
        "retrieved_docs": response_data.get("retrieved_docs", []),
        "grounded": response_data.get("grounded", False),
        "response_time": response_time
    }

# 자동 평가 함수 (간단한 키워드 매칭 방식 - 실제 환경에서는 LLM 기반 평가 모델(LLM-as-a-Judge) 도입 권장)
def evaluate_response(expected: str, actual: str, retrieved_docs: list, is_hallucination_test: bool) -> dict:
    
    # 1. Retrieval Accuracy (Recall@5)
    # 실제 구현에서는 문서 ID나 정확한 내용 매칭 필요
    # 여기서는 검색된 문서가 1개 이상이면 1점으로 처리하는 모의 로직
    recall_at_5 = 1 if len(retrieved_docs) > 0 else 0
    if is_hallucination_test:
        recall_at_5 = 0 # 환각 검증의 경우 문서 검색이 없어야 함
        
    # 2. Answer Accuracy (1~5점)
    # 실제로는 LLM이나 ROUGE, BLEU, BERTScore 등 사용
    # 여기서는 단순 키워드 매칭 여부로 임의 점수 부여
    score = 1
    # 기대 답변의 일부 단어가 포함되어 있는지 확인
    keywords = expected.split()
    match_count = sum(1 for k in keywords if k in actual)
    if match_count > 0:
         score = min(5, int(5 * (match_count / len(keywords))) + 1)
         
    # 환각 검증 문항의 경우 "알 수 없음", "제공하지 않음" 등의 뉘앙스가 포함되면 고득점
    if is_hallucination_test and ("알 수 없" in actual or "불가" in actual or "없습" in actual):
        score = 5

    # 3. Groundedness (0/1)
    # 실제로는 답변이 retrieved_docs에 기반하는지 판단하는 NLI 모델 등 사용
    grounded_score = 1 if score >=3 else 0 
    if is_hallucination_test and score == 5:
        grounded_score = 1

    return {
        "recall@5": recall_at_5,
        "answer_accuracy": score,
        "grounded_score": grounded_score
    }

# 메인 실행 함수
def run_evaluation():
    dataset = load_dataset()
    results = []
    response_times = []

    print(f"총 {len(dataset)}건의 평가를 시작합니다...")
    
    for item in dataset:
        print(f"평가 진행 중... ID: {item['id']}")
        
        # API 호출
        context = item.get("context", "")
        api_result = call_api(item['query'], context)
        
        # 평가 수행
        is_hallucination = item['type'] == "환각 검증"
        eval_metrics = evaluate_response(
            item['expected_answer'], 
            api_result['answer'], 
            api_result['retrieved_docs'],
            is_hallucination
        )
        
        response_times.append(api_result['response_time'])
        
        # 결과 저장
        result_row = {
            "ID": item['id'],
            "유형": item['type'],
            "질의": item['query'],
            "기대_답변": item['expected_answer'],
            "실제_답변": api_result['answer'],
            "Recall@5": eval_metrics['recall@5'],
            "Answer_Accuracy": eval_metrics['answer_accuracy'],
            "Grounded_Score": eval_metrics['grounded_score'],
            "Response_Time(s)": round(api_result['response_time'], 3)
        }
        results.append(result_row)
        
    # 데이터프레임 변환
    df_results = pd.DataFrame(results)
    
    # 종합 지표 계산
    avg_recall = df_results['Recall@5'].mean()
    avg_accuracy = df_results['Answer_Accuracy'].mean()
    avg_grounded = df_results['Grounded_Score'].mean()
    
    p95_time = np.percentile(response_times, 95)
    p99_time = np.percentile(response_times, 99)
    avg_time = np.mean(response_times)

    print("\n" + "="*50)
    print("평가 완료! 종합 결과:")
    print(f"평균 Retrieval Accuracy (Recall@5): {avg_recall:.2f}")
    print(f"평균 Answer Accuracy (1~5점): {avg_accuracy:.2f}")
    print(f"평균 Groundedness Score (0/1): {avg_grounded:.2f}")
    print(f"응답 시간 - 평균: {avg_time:.3f}s, p95: {p95_time:.3f}s, p99: {p99_time:.3f}s")
    print("="*50)

    # 결과 CSV 저장
    result_filename = BASE_DIR / "evaluation_results.csv"
    df_results.to_csv(result_filename, index=False, encoding='utf-8-sig')
    print(f"상세 평가 결과가 {result_filename}에 저장되었습니다.")

if __name__ == "__main__":
    run_evaluation()