from sqlalchemy.orm import Session
from app.models import Paper, PaperMetadata, ChatHistory 
from app.utils.kanana import call_kanana
from typing import List, Optional
from fastapi.concurrency import run_in_threadpool
import logging

logger = logging.getLogger(__name__)

# ------------------------------------
# Agent 객체 정의
# ------------------------------------
class ChatbotAgent:
    """
    논문(Paper)의 전체 텍스트(Full-Text)를 기반으로 사용자 질문에 답변하는 챗봇 에이전트.
    별도의 RAG 시스템 없이, PaperMetadata에 저장된 텍스트를 LLM에 직접 전달(Prompting)하여 답변을 생성하고,
    그 결과를 데이터베이스에 기록(ChatHistory)합니다.
    """

    def _get_paper_full_text(self, db: Session, paper_id: int) -> Optional[str]:
        """
        주어진 논문 ID를 사용하여 데이터베이스에서 PaperMetadata의 full_text를 조회합니다.
        Paper와 PaperMetadata는 1:1 관계입니다.
        """
        try:
            paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
            if paper and paper.paper_metadata:
                return paper.paper_metadata.full_text
            
        except Exception as e:
            logger.error(f"논문 ID {paper_id}의 full_text 조회 중 DB 오류 발생: {e}", exc_info=True)
            return None
        
        return None
    
    def _format_history_for_prompt(self, history: List[ChatHistory]) -> str:
        """
        ChatHistory 객체 리스트를 LLM 프롬프트용 텍스트 형식으로 변환합니다.
        """
        if not history:
            return "없음"
        
        recent_history = history[-2:]
        
        formatted_text = ""
        for i, chat in enumerate(recent_history):
            formatted_text += f"Q{i+1}: {chat.question}\n"
            formatted_text += f"A{i+1}: {chat.answer}\n"
            
        return formatted_text.strip()


    async def generate_response(
        self,
        db: Session,
        user_id: int,
        paper_id: int,
        question: str,
        relevant_history: List[ChatHistory] = None
    ) -> ChatHistory:
        
        """
        Kanana LLM에 전달할 RAG(Retrieval-Augmented Generation) 스타일의 프롬프트를 구성합니다.
        full_text는 MAX_TEXT_LENGTH에 맞게 잘라서 사용합니다.
        """

        # 1. DB에서 논문 정보 및 텍스트 가져오기 (paper_metadata.full_text 조회)
        full_text = self._get_paper_full_text(db, paper_id)
        
        if not full_text:
            return ChatHistory(
                user_id=user_id,
                paper_id=paper_id,
                question=question,
                answer="현재 이 논문의 full text가 등록되어 있지 않아 답변을 생성할 수 없습니다."
            )
        
        # 2. Kanana에 전달할 프롬프트 구성
        text_preview = full_text
        history_text = self._format_history_for_prompt(relevant_history or [])
        
        prompt = f"""
당신은 아래 주어진 '논문 내용'과 '이전 대화'를 기반으로 '사용자의 새 질문'에 답해야 하는 논문 분석 AI입니다.
**외부 정보는 절대 사용하지 마세요.** 오직 주어진 논문 내용과 대화 맥락만으로 답변을 생성해야 합니다.

또한, 답변은 반드시 다음 두 부분으로 구성해야 합니다:

1) **답변(Answer)**: 사용자의 질문에 대한 명확하고 친절한 설명
2) **근거(Evidence)**: 위 '논문 내용'에서 직접 발췌한 문장 또는 문단. 
   - 임의로 생성하지 말고, 반드시 주어진 논문 텍스트에서 그대로 가져와야 합니다.
   - 사용된 근거가 어떤 질문 부분을 뒷받침하는지 간단히 설명해주세요.

출력 형식은 아래 템플릿을 따르세요:

[답변]
(여기에 사용자의 질문에 대한 설명을 작성)

[근거]
- 원문 발췌: "..."
- 설명: 이 문장이 위 답변의 ○○ 내용을 뒷받침함.

----------------------------------

--- 논문 내용 (Paper full text) ---
{text_preview}
----------------------------------

--- 이전 대화 (Context) ---
{history_text}
----------------------------------

--- 새 질문 ---
{question}
----------------------------------

위 논문 텍스트와 이전 대화 내용을 기반으로 위 템플릿 형식에 맞춰 답변을 생성하세요.
"""

    
        # 3. Kanana 함수 호출 (동기 함수 call_kanana 호출)
        try:
            answer = await run_in_threadpool(call_kanana, prompt)
            if not answer:
                answer = "Kanana 모델에서 답변을 생성하지 못했습니다."
        except Exception as e:
            logging.error(f"Kanana 호출 중 에러 발생: {e}", exc_info=True)
            answer = "API 호출 중 시스템 오류가 발생했습니다."

        # 4. ChatHistory에 저장
        try:
            new_chat = ChatHistory(
                user_id=user_id,
                paper_id=paper_id,
                question=question,
                answer=answer
            )
            db.add(new_chat)
            db.commit()
            db.refresh(new_chat)
            return new_chat
        except Exception as e:
            logger.error(f"ChatHistory 저장 중 DB 오류 발생: User {user_id}, Paper {paper_id}, Error: {e}", exc_info=True)
            db.rollback()

    def get_chat_history(
        self,
        db: Session,
        user_id: int,
        paper_id: int
    ) -> List[ChatHistory]:
        """
        특정 논문에 대한 이전 채팅 기록을 반환합니다.
        """
        history = db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.paper_id == paper_id
        ).order_by(ChatHistory.created_at.asc()).all()
        
        return history

chatbot_agent = ChatbotAgent()