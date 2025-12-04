from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import User, Paper, PaperMetadata, ChatHistory, UserReadPaper, Recommendation
from app.utils.kanana import call_kanana
from typing import List, Optional
from datetime import datetime, timedelta
import json
import re

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

        # 4. 최근 3개 논문 보고 지은 질문 (난이도 Advice Agent용)
        # 최근 3개 논문에 대한 질문 9개 수집 가정
        recent_papers_id = db.query(UserReadPaper.paper_id).filter(UserReadPaper.user_id == user_id).order_by(UserReadPaper.read_at.desc()).limit(3).all()
        recent_paper_ids = [p[0] for p in recent_papers_id]

        recent_questions_for_level = (
            db.query(ChatHistory.question)
            .filter(ChatHistory.user_id == user_id, ChatHistory.paper_id.in_(recent_paper_ids))
            .order_by(ChatHistory.created_at.desc())
            .limit(9)
            .all()
        )
        recent_level_question_texts = [q[0] for q in recent_questions_for_level]

        return {
            "keywords": all_keywords,
            "questions": recent_question_texts,
            "total_read_count": total_read_count,
            "recent_level_questions": recent_level_question_texts
        }
    

    # ============================================
    # 사용자 스펙에 맞는 구조화된 조언 생성
    # ============================================
    async def analyze_and_suggest(
        self,
        db: Session,
        user_id: int
    ) -> dict:
        """
        사용자 활동을 분석하여 관심 분야/난이도 변경 제안 또는 조언 없음을 반환합니다.
        (관심 분야 Advice Agent, 난이도 Advice Agent 로직을 Kanana 호출로 대체)
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
        # 1. 관심 분야 변경 제안 로직 (LLM(Kanana) 사용)
        # ----------------------------------------
        keywords = analysis_data['keywords']
        current_interest = user.interest or "미설정"
        
        # 관심 분야 Advice Agent 프롬프트
        interest_prompt = f"""
        [사용자 프로필]
        - 현재 관심 분야: {current_interest}
        
        [최근 1주간 활동 패턴]
        - 최근 다룬 키워드: {', '.join(keywords) or '키워드 없음'}
        ---
        
        당신은 **친절한 전문 멘토 AI**입니다. 위 정보를 바탕으로 사용자의 실제 관심사가 현재 설정된 관심 분야와 다른지 분석하세요.
        분석 결과에 따라 다음 중 하나의 JSON 형식으로만 응답하세요.
        
        1. **새로운 관심 분야를 제안해야 하는 경우:**
            (조건: 활동 키워드가 현재 관심 분야와 명확히 다르며, 충분한 빈도로 나타날 때)
        {{
            "advice_type": "interest_change",
            "suggested_interest": "사용자 활동에서 가장 자주 나타나는 새로운 키워드",
            "reason": "**친절하고 부드러운 대화체(말 끝에 '~네요', '~하셨어요' 등 사용)**를 기반으로 제안형 어투를 사용하여 2~3줄 이내의 변경 제안 이유. 이유의 마지막 문장을 반드시 '새 관심 분야를 [suggested_interest]로 변경해 보시겠어요?'와 같이 구체적인 액션을 유도하는 질문형으로 마무리하세요."
        }}
        
        2. **현재 관심 분야를 유지해야 하는 경우:**
            (조건: 제안할 새로운 키워드가 없거나, 활동 키워드가 현재 관심 분야와 동일하거나 유사할 때)
        {{
            "advice_type": "none",
            "message": "전문 멘토의 말투로 2~3줄 이내의 친근하고 부드러운 유지 제안 이유"
        }}
        
        **주의:** 만약 가장 자주 나타나는 키워드가 **현재 관심 분야와 동일**하다면, **반드시 "advice_type": "none"을 반환**해야 합니다.
        """

        try:
            # Kanana 호출
            interest_advice_raw = call_kanana(interest_prompt)
            
            # JSON 파싱
            match = re.search(r"\{.*\}", interest_advice_raw, re.DOTALL)
            if match:
                interest_advice = json.loads(match.group(0))
            else:
                raise ValueError("LLM 응답에서 JSON을 찾을 수 없습니다.")

            # LLM이 interest_change를 반환했을 경우, 후처리 로직 실행 (안전 장치)
            if interest_advice.get("advice_type") == "interest_change":
                suggested = interest_advice.get('suggested_interest', '').lower().strip()
                current = current_interest.lower().strip()
                
                # 후처리: 제안된 키워드가 현재 키워드와 동일하면 none으로 변경
                if suggested == current or current in suggested or suggested in current:
                    pass
                else:
                    return {
                        "advice_type": "interest_change",
                        "current_interest": current_interest,
                        "suggested_interest": interest_advice['suggested_interest'],
                        "reason": interest_advice['reason']
                    }

        except Exception as e:
            print(f"Kanana (관심 분야) 호출 또는 파싱 중 에러 발생: {e}")
            # 에러 발생 시 난이도 제안 로직으로 넘어감
            pass
            
        # ----------------------------------------
        # 2. 난이도 변경 제안 로직 (LLM(Kanana) 사용)
        # (관심 분야 변경 제안이 없었을 경우에만 실행)
        # ----------------------------------------
        questions_for_level = analysis_data['recent_level_questions']
        current_level = user.level or "beginner"
        
        # 난이도 Advice Agent 프롬프트
        level_prompt = f"""
        [사용자 프로필]
        - 현재 학습 레벨: {current_level}
        
        [최근 3개 논문에 대한 질문 9개]
        - 질문 목록: {'; '.join(questions_for_level) or '질문 기록 없음'}
        ---
        
        당신은 **친절한 전문 멘토 AI**입니다. 사용자의 최근 질문 목록을 분석하여 **이해도의 점수 (comprehension_scoring)**를 1부터 100 사이의 숫자로 매기고, 현재 레벨보다 **높은 레벨로 상향 조정 (suggest higher level)**이 필요한지 판단하세요.
        
        * **상향 조정 기준:** 질문의 깊이, 전문성, 복잡도를 종합적으로 고려합니다. (예: 단순 용어 질문 < 개념 간 관계 질문 < 한계나 확장 질문)
        * **상향 조정 임계값:** Beginner에서 Intermediate로 제안은 70점 이상, Intermediate에서 Advanced로 제안은 80점 이상일 때 고려합니다.
        
        분석 결과에 따라 다음 중 하나의 JSON 형식으로만 응답하세요.
        
        1. **레벨 상향을 제안해야 하는 경우 (answer > threshold):**
        {{
            "advice_type": "level_change",
            "comprehension_score": "분석된 이해도 점수 (1~100)",
            "suggested_level": "intermediate" | "advanced",
            "reason": "**친절하고 부드러운 대화체(말 끝에 '~네요', '~하셨어요' 등 사용)**를 기반으로 제안형 어투를 사용하여 2~3줄 이내의 상향 제안 이유. 이유의 마지막 문장을 반드시 '학습 레벨을 [suggested_level]로 상향 조정해 보시겠어요?'와 같이 구체적인 액션을 유도하는 질문형으로 마무리하세요."
        }}
        
        2. **레벨을 유지해야 하는 경우:**
        {{
            "advice_type": "none",
            "message": "전문 멘토의 말투로 **제안형 어투('~해보시는 게 좋겠어요', '~하는 것이 어떨까요?')를 사용하여** 2~3줄 이내의 레벨 유지 제안 이유"
        }}
        
        질문이 3개 미만이거나 레벨이 'advanced'인 경우 레벨 변경을 제안하지 않습니다.
        """

        if len(questions_for_level) >= 3 and current_level != "advanced":
            try:
                # Kanana 호출
                level_advice_raw = call_kanana(level_prompt)
                
                # JSON 파싱
                match = re.search(r"\{.*\}", level_advice_raw, re.DOTALL)
                if match:
                    level_advice = json.loads(match.group(0))
                else:
                    raise ValueError("LLM 응답에서 JSON을 찾을 수 없습니다.")

                # 난이도 변경 제안이 있을 경우 즉시 반환 (워크플로우 흐름)
                if level_advice.get("advice_type") == "level_change":
                    suggested_level = level_advice['suggested_level']
                    
                    # LLM이 제안한 레벨이 유효한지 확인하고 현재 레벨보다 높은지 확인
                    if suggested_level in ["intermediate", "advanced"] and suggested_level != current_level:
                        return {
                            "advice_type": "level_change",
                            "current_level": current_level,
                            "suggested_level": suggested_level,
                            "reason": level_advice['reason'],
                            "comprehension_score": level_advice['comprehension_score']
                        }

            except Exception as e:
                print(f"Kanana (난이도) 호출 또는 파싱 중 에러 발생: {e}")
                # 에러 발생 시 조언 없음 로직으로 넘어감
                pass

        # ----------------------------------------
        # 3. 조언 없음 (두 LLM Agent 모두 변경 제안이 없었을 경우)
        # ----------------------------------------
        return {
            "advice_type": "none",
            "message": "오늘도 열심히 논문 공부를 해보아요! 현재 학습 방향이 매우 좋습니다."
        }


    async def generate_study_advice(
        self,
        db: Session,
        user_id: int
    ) -> str:

        """
        사용자 정보를 기반으로 학습 조언을 생성하고 실시간 응답합니다.
        (LLM을 통해 실질적인 학습 조언을 생성하도록 프롬프트 강화)
        """

        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return "사용자 정보를 찾을 수 없어 조언을 드릴 수 없습니다."

        analysis_data = self._get_analysis_data(db, user_id)

        if analysis_data["total_read_count"] == 0:
            return "아직 읽은 논문 기록이 없어 조언을 생성할 수 없습니다. 첫 논문을 읽어보시면 맞춤 조언을 드릴 수 있어요!"
        
        # 1. 구조화된 조언 결과를 먼저 가져옵니다.
        # analyze_and_suggest는 비동기 함수이므로 await 필요
        structured_advice = await self.analyze_and_suggest(db, user_id)
        
        advice_context = ""
        if structured_advice.get("advice_type") == "interest_change":
            reason = structured_advice.get("reason", "활동 패턴이 새로운 분야로 이동했습니다.")
            suggested = structured_advice.get("suggested_interest", "새로운 주제")
            current = structured_advice.get("current_interest", "미설정")
            advice_context = f"[중요 변경 제안] 관심 분야 변경 제안! 현재 '{current}'에서 '{suggested}'(으)로 변경을 추천합니다. 추천 사유: {reason}"
        
        elif structured_advice.get("advice_type") == "level_change":
            reason = structured_advice.get("reason", "질문 수준이 현 레벨을 초과합니다.")
            suggested = structured_advice.get("suggested_level", "상위 레벨")
            current = structured_advice.get("current_level", "미설정")
            score = structured_advice.get("comprehension_score", 0)
            advice_context = f"[중요 변경 제안] 학습 레벨 상향 제안! 현재 '{current}'에서 '{suggested}'(으)로 상향을 추천합니다. 이해도 점수 {score}점. 추천 사유: {reason}"

        elif structured_advice.get("advice_type") == "none":
            message = structured_advice.get("message", "현재 학습 방향이 일치하여 변경이 불필요함")
            advice_context = f"[현재 상태] 현재 학습 방향이 일치합니다. 멘토 의견: {message}"

        # 2. Kanana에 전달할 상세 프롬프트 구성(user.interest, user.level 사용)
        prompt = f"""
        [사용자 프로필]
        - 이름: {user.username}
        - 관심 분야: {user.interest or "미설정"}
        - 희망 학습 레벨: {user.level or "미설정"}
        - 총 논문 읽은 개수: {analysis_data['total_read_count']}개

        [최근 1주간 활동 패턴 분석]
        - 최근 다룬 키워드: {', '.join(set(analysis_data['keywords'])) or '키워드 없음 (읽은 논문 부족)'}
        - 최근 챗봇 질문 내용 요약: {'; '.join(analysis_data['questions']) or '챗봇 질문 기록 없음'}

        [구조화된 조언 결과]
        {advice_context}
        ---

        당신은 사용자의 **성장을 돕는 전문 멘토 AI**입니다.
        친절하고 **따뜻하며**, 사용자의 노력을 인정하고 동기 부여와 실천을 유도하는 **친근한 대화체와 제안형 말투**로 다음 4가지 코칭 요소를 모두 포함하는 **자연스러운 대화 형식**의 학습 코칭 메시지를 생성하세요.
        

        1. **조언 결과 통합:** [구조화된 조언 결과] 섹션의 내용을 **가장 먼저** 자연스러운 말투로 언급하며 시작하세요.
        2. **집중도 코칭:** 최근 활동 키워드를 분석하여, 현재 관심 분야 내에서 **가장 깊이 파야 할 세부 주제**를 1~2개 꼽고, 관련 논문 1~2편을 더 찾아보도록 조언하세요. (관심 분야가 미설정이라면, 가장 자주 나온 키워드를 중심으로 주제를 확정하도록 조언)
        3. **학습 효율성 조언:** 챗봇 질문의 경향(빈도 및 깊이)을 바탕으로, **현재 레벨({user.level or "미설정"})**에 맞게 **'논문을 읽는 방법'**이나 **'질문하는 습관'**을 개선할 수 있는 구체적인 팁을 제시하세요.
        4. **다음 주 액션 플랜:** 다음 1주간 **정량적으로 달성 가능한 학습 목표**와 구체적인 **실천 방법**을 1~2가지 제시하세요. (예: "매일 15분 동안 읽은 논문의 핵심 구조를 마인드맵으로 정리하기" 또는 "세미나 자료를 만들듯 핵심 내용을 5줄 요약하는 연습하기")

        메시지는 모든 정보를 담으면서도 2줄 내외의 간결한 길이로 유지해주세요.
        """

        # 2. Kanana 함수 호출
        try:
            advice = call_kanana(prompt, max_tokens=100)

            if not advice:
                advice = "Kanana 모델이 현재 사용자에게 맞는 조언을 생성하지 못했습니다."

        except Exception as e:
            print(f"Kanana 호출 중 에러 발생: {e}")
            advice = "API 호출 중 시스템 오류가 발생했습니다. (조언 실패)"

        # 3. DB 저장 없이 실시간 응답 (Agent 정의에 따라 저장 로직 제거)
        return advice

advice_agent = AdviceAgent()