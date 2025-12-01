from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import User, Paper, PaperMetadata, ChatHistory, UserReadPaper, Recommendation
from app.utils.kanana import call_kanana
from typing import List, Optional
from datetime import datetime, timedelta
import json

# ------------------------------------
# Agent 객체 정의
# ------------------------------------

class AdviceAgent:
    """
    사용자 활동 패턴 (논문 키워드, 챗봇 질문) 분석 후 학습 조언을 제공하는 Agent
    """

    def _get_analysis_data(self, db: Session, user_id: int) -> dict:
        """최근 1주일 활동 데이터를 조회하여 조언 생성에 필요한 자료를 수집합니다."""
        one_week_ago = datetime.utcnow() - timedelta(days=7)

        # 1. 최근 1주일 읽은 논문의 키워드 조회 (PaperMetadata)
        recent_read_keywords = (
            db.query(PaperMetadata.keywords)
            .join(UserReadPaper, UserReadPaper.paper_id == PaperMetadata.paper_id)
            .filter(UserReadPaper.user_id == user_id, UserReadPaper.read_at >= one_week_ago)
            .all()
        )

        all_keywords = []
        for keywords_text in recent_read_keywords:
            keyword_data = keywords_text[0] if keywords_text and keywords_text[0] else None

            if not keyword_data:
                continue

            try:
                parsed = json.loads(keyword_data)

                if isinstance(parsed, list): # JSON으로 가정
                    all_keywords.extend(parsed)
                else: # JSON이지만 리스트가 아닌 경우 (예: {"key": "value"}) 또는 단일 문자열로 저장된 경우
                    all_keywords.append(str(parsed))
            except json.JSONDecodeError: # JSON이 아니면 그냥 문자열로 처리
                all_keywords.append(keyword_data)

        # 2. 최근 1주일 챗봇 질문 기록 (ChatHistory)
        recent_questions = (
            db.query(ChatHistory.question)
            .join(Paper, ChatHistory.paper_id == Paper.paper_id)
            .filter(ChatHistory.user_id == user_id, ChatHistory.created_at >= one_week_ago)
            .all()
        )
        recent_question_texts = [q[0] for q in recent_questions]

        # 3. 총 읽은 논문 수
        total_read_count = db.query(UserReadPaper).filter(UserReadPaper.user_id == user_id).count()

        return {
            "keywords": all_keywords,
            "questions": recent_question_texts,
            "total_read_count": total_read_count
        }

    async def generate_study_advice(
        self,
        db: Session,
        user_id: int
    ) -> str:

        """
        사용자 정보를 기반으로 학습 조언을 생성하고 실시간 응답합니다.
        """

        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return "사용자 정보를 찾을 수 없어 조언을 드릴 수 없습니다."

        analysis_data = self._get_analysis_data(db, user_id)

        if analysis_data["total_read_count"] == 0:
            return "아직 읽은 논문 기록이 없어 조언을 생성할 수 없습니다. 첫 논문을 읽어보시면 맞춤 조언을 드릴 수 있어요!"

        user_interest = user.interest if user.interest else "미설정"
        user_level = user.level if user.level else "미설정"

        # 1. Kanana에 전달할 상세 프롬프트 구성(user.interest, user.level 사용)
        prompt = f"""
        [사용자 프로필]
        - 이름: {user.username}
        - 관심 분야: {user.interest}
        - 희망 학습 레벨: {user.level}
        - 총 논문 읽은 개수: {analysis_data['total_read_count']}개

        [최근 1주간 활동 패턴 분석]
        - 최근 다룬 키워드: {', '.join(set(analysis_data['keywords'])) or '키워드 없음 (읽은 논문 부족)'}
        - 최근 챗봇 질문 내용 요약: {'; '.join(analysis_data['questions']) or '챗봇 질문 기록 없음'}
        ---

        위 분석 자료를 바탕으로 다음 세 가지 측면에 대해 구체적인 조언을 제공하세요:
        1. 연구 주제의 일관성 및 집중도
        2. 현재 희망 레벨({user.level})에 맞는 학습 속도 및 방법
        3. 다음 1주간 구체적으로 시도해 볼 만한 학습 목표나 액션 아이템

        전문적이면서도 친절한 AI 조언 Agent의 말투로 5~7줄 이내로 조언을 생성해주세요.
        """

        # 2. Kanana 함수 호출
        try:
            advice = call_kanana(prompt)

            if not advice:
                advice = "Kanana 모델이 현재 사용자에게 맞는 조언을 생성하지 못했습니다."

        except Exception as e:
            print(f"Kanana 호출 중 에러 발생: {e}")
            advice = "API 호출 중 시스템 오류가 발생했습니다. (조언 실패)"

        # 3. DB 저장 없이 실시간 응답 (Agent 정의에 따라 저장 로직 제거)
        return advice

advice_agent = AdviceAgent()