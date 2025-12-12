from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KANANA_API_KEY", "")

client = OpenAI(
    base_url="https://kanana-2-30b-a3b-s7nyu.a2s-endpoint.kr-central-2.kakaocloud.com/v1",
    api_key=API_KEY
)

SYSTEM_PROMPT = """당신은 카카오(kakao)에서 개발된 친절한 인공지능 언어모델이고 이름은 카나나(kanana)입니다. 
2024년 7월 이후 사건에 대한 정보는 알 수 없다고 답해야합니다. 
현재 시간, 날짜, 사건 등 외부 정보를 참조해야 답할 수 있는 질문에는 외부 검색을 사용하라고 추천하세요. 
URL에 기반한 사용자 질의의 경우 사용자에게 URL에 있는 정보를 직접 입력하도록 요청합니다. 
카나나(kanana)의 모델 사이즈나 파라미터 정보는 비공개입니다."""

def call_kanana(prompt: str, system_prompt: str = SYSTEM_PROMPT, temperature: float = 0, max_tokens: int = 1024) -> str:
    """Kanana 모델 호출 함수"""
    try:
        response = client.chat.completions.create(
            model=client.models.list().data[0].id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Kanana 호출 오류: {e}")
        return ""

