from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.agents.chatbot_agent import chatbot_agent
from app.database import get_db
from app.models import ChatHistory

router = APIRouter(
    prefix="/papers/{paper_id}/chat",
    tags=["chatbot"]
)

# ------------------------------------
# Request & Response 모델 정의
# ------------------------------------
class ChatRequest(BaseModel):
    user_id: int
    question: str

class PreviousChat(BaseModel):
    question: str
    answer: str

class ChatResponse(BaseModel):
    chat_id: int
    paper_id: int
    question: str
    answer: str
    created_at: str
    context_used: dict  # {"previous_chats": [...]}

# ------------------------------------
# 챗봇 엔드포인트
# ------------------------------------
@router.post("", response_model=ChatResponse)
async def chat_with_paper(paper_id: int, request: ChatRequest, db: Session = Depends(get_db)):
    # 1. 이전 채팅 기록 조회 (최신 2개)
    history = chatbot_agent.get_chat_history(db, request.user_id, paper_id)

    # 2. 새 질문에 대한 답변 생성
    new_chat = await chatbot_agent.generate_response(
        db=db,
        user_id=request.user_id,
        paper_id=paper_id,
        question=request.question,
        relevant_history=history
    )

    if not new_chat:
        raise HTTPException(status_code=500, detail="답변 생성 실패")

    # --- 데이터베이스 저장 로직 (수정된 부분) ---
    try:
        # 1. new_chat 객체를 현재 세션에 추가 (Persistence 확보)
        db.add(new_chat)
        
        # 2. DB에 커밋하여 created_at 필드 자동 생성
        db.commit()
        
        # 3. 객체를 갱신하여 DB가 생성한 created_at 값을 불러옴 (NoneType 오류 방지)
        db.refresh(new_chat)

    except Exception as e:
        # 실패 시 롤백 및 에러 반환
        db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스에 채팅 기록 저장 실패 (Failed to save chat history to database): {e}")
    # ----------------------------------------------

    # 3. 응답용 이전 대화 변환 (최신 2개)
    recent_history = history[-2:] 
    previous_chats = [{"question": chat.question, "answer": chat.answer} for chat in recent_history]

    # 4. Response 생성
    return ChatResponse(
        chat_id=new_chat.id,         
        paper_id=new_chat.paper_id,        
        question=new_chat.question,
        answer=new_chat.answer,
        created_at=new_chat.created_at.isoformat(),
        context_used={"previous_chats": previous_chats}  
    )

