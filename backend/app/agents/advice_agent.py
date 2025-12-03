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
               pass

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
    
    # ============================================
    # API 스펙에 맞는 구조화된 조언 생성
    # ============================================
    async def analyze_and_suggest(
        self,
        db: Session,
        user_id: int
    ) -> dict:
        """
        사용자 활동을 분석하여 관심 분야/난이도 변경 제안 또는 조언 없음을 반환합니다.
        
        Returns:
            dict: {
                "advice_type": "interest_change" | "level_change" | "none",
                ... (각 타입에 맞는 추가 필드)
            }
        """
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {
                "advice_type": "none",
                "message": "사용자 정보를 찾을 수 없습니다."
            }

        analysis_data = self._get_analysis_data(db, user_id)

        if analysis_data["total_read_count"] == 0:
            return {
                "advice_type": "none",
                "message": "아직 읽은 논문 기록이 없어요. 첫 논문을 읽어보시면 맞춤 조언을 드릴 수 있어요!"
            }

        # ----------------------------------------
        # 1. 관심 분야 변경 제안 로직
        # ----------------------------------------
        keywords = analysis_data['keywords']


        if len(keywords) >= 5:  # 충분한 데이터가 있을 때
            # 키워드 빈도 계산
            keyword_freq = {}
            for kw in keywords:
                kw_lower = kw.lower().strip()
                if kw_lower:
                    keyword_freq[kw_lower] = keyword_freq.get(kw_lower, 0) + 1
            
            # 가장 빈번한 키워드 추출
            if keyword_freq:
                top_keyword = max(keyword_freq.items(), key=lambda x: x[1])[0]
                current_interest_lower = (user.interest or "").lower().strip()

            # 현재 관심 분야와 다른 키워드가 주로 나타날 경우
            if current_interest_lower and top_keyword not in current_interest_lower and current_interest_lower not in top_keyword:
                # 빈도가 충분히 높은지 확인 (전체 키워드의 30% 이상)
                if keyword_freq[top_keyword] >= len(keywords) * 0.3:
                    return {
                        "advice_type": "interest_change",
                        "current_interest": user.interest or "미설정",
                        "suggested_interest": top_keyword.title(),
                        "reason": f"최근 '{top_keyword}'에 대한 관심이 많아지신 것 같아요. 관심 분야를 변경할까요?"
                    }

        # ----------------------------------------
        # 2. 난이도 변경 제안 로직
        # ----------------------------------------
        questions = analysis_data['questions']
        if len(questions) >= 3 and user.level:
            # 간단한 휴리스틱: 질문 길이와 복잡도로 이해도 추정
            avg_question_length = sum(len(q) for q in questions) / len(questions)
            
            # Beginner -> Intermediate 제안
            if user.level == "beginner" and avg_question_length > 100:
                return {
                    "advice_type": "level_change",
                    "current_level": user.level,
                    "suggested_level": "intermediate",
                    "reason": f"최근 '{user.interest or '연구 분야'}'에 대한 질문들이 깊이 있어지고 있어요. 레벨을 높여볼까요?",
                    "comprehension_score": 75
                }
            # Intermediate -> Advanced 제안
            elif user.level == "intermediate" and avg_question_length > 150:
                return {
                    "advice_type": "level_change",
                    "current_level": user.level,
                    "suggested_level": "advanced",
                    "reason": f"최근 '{user.interest or '연구 분야'}'에 대한 이해도가 높아지신 것 같아요. 레벨을 높여볼까요?",
                    "comprehension_score": 85
                }

        # ----------------------------------------
        # 3. 조언 없음
        # ----------------------------------------
        return {
            "advice_type": "none",
            "message": "오늘도 열심히 논문 공부를 해보아요!"
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