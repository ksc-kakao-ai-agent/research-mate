from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime, date, timedelta
import json
from app.models import UserReadPaper
from app.playmcp_client import playmcp_client

from pydantic import BaseModel

from app.database import get_db
from app.models import Paper, PaperMetadata, Recommendation, ChatHistory

router = APIRouter(tags=["papers_detail"])


# ==================== Response 모델 ====================

class PaperHistoryItem(BaseModel):
    paper_id: int
    title: str
    authors: List[str]
    recommended_at: str  # YYYY-MM-DD 형식
    is_user_requested: bool


class PaperHistoryResponse(BaseModel):
    papers: List[PaperHistoryItem]
    total_count: int


class SummaryResponse(BaseModel):
    level: str
    content: str


class MetadataResponse(BaseModel):
    citation_count: int
    citation_velocity: float
    influential_citation_count: int
    keywords: List[str]


class ChatHistoryItem(BaseModel):
    chat_id: int
    question: str
    answer: str
    created_at: str  # ISO 8601 형식


class PaperDetailResponse(BaseModel):
    paper_id: int
    title: str
    authors: List[str]
    published_date: str
    source: str
    arxiv_id: Optional[str] = None
    pdf_url: Optional[str] = None
    abstract: Optional[str] = None
    summary: Optional[SummaryResponse] = None
    metadata: Optional[MetadataResponse] = None
    chat_history: List[ChatHistoryItem] = []


# ==================== 유틸리티 함수 ====================

def parse_json_field(field_value: Optional[str]) -> List[str]:
    """JSON 문자열을 파싱하여 리스트로 반환"""
    if not field_value:
        return []
    try:
        parsed = json.loads(field_value)
        if isinstance(parsed, list):
            return parsed
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def format_date(date_obj: Optional[datetime]) -> Optional[str]:
    """datetime을 YYYY-MM-DD 형식으로 변환"""
    if not date_obj:
        return None
    return date_obj.strftime("%Y-%m-%d")


# ==================== API 엔드포인트 ====================

@router.get("/{user_id}/papers/history", response_model=PaperHistoryResponse, status_code=status.HTTP_200_OK)
async def get_paper_history(user_id: int, db: Session = Depends(get_db)):
    """
    오늘까지 추천된 논문 목록 조회
    정렬: recommended_at 내림차순 (최신순)
    """
    today = date.today()
    today_end = datetime.combine(today, datetime.max.time())

    # 오늘까지 추천된 논문만 조회
    recommendations = db.query(Recommendation).filter(
        and_(
            Recommendation.user_id == user_id,
            Recommendation.recommended_at <= today_end
        )
    ).order_by(desc(Recommendation.recommended_at)).all()
    
    papers_list = []
    for rec in recommendations:
        paper = rec.paper
        if not paper:
            continue
        
        authors = parse_json_field(paper.authors)
        recommended_at_str = format_date(rec.recommended_at)
        if not recommended_at_str:
            continue
        
        papers_list.append(PaperHistoryItem(
            paper_id=paper.paper_id,
            title=paper.title,
            authors=authors,
            recommended_at=recommended_at_str,
            is_user_requested=rec.is_user_requested
        ))
    
    return PaperHistoryResponse(
        papers=papers_list,
        total_count=len(papers_list)
    )


@router.get("/papers/{paper_id}/{user_id}", response_model=PaperDetailResponse, status_code=status.HTTP_200_OK)
async def get_paper_detail(paper_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    논문 상세 정보 조회
    """
    # 논문 조회
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="논문을 찾을 수 없습니다."
        )

    # ----------------------------
    # 1. UserReadPaper 자동 기록
    # ----------------------------
    read_exists = db.query(UserReadPaper).filter(
        UserReadPaper.user_id == user_id,
        UserReadPaper.paper_id == paper_id
    ).first()

    if not read_exists:
        new_read = UserReadPaper(
            user_id=user_id,
            paper_id=paper_id,
            read_at=datetime.utcnow()
        )
        db.add(new_read)
        db.commit()
        db.refresh(new_read)
    
    # 논문 메타데이터 조회
    metadata = db.query(PaperMetadata).filter(PaperMetadata.paper_id == paper_id).first()
    
    # 채팅 히스토리 조회
    chat_histories = db.query(ChatHistory).filter(
        ChatHistory.paper_id == paper_id,
        ChatHistory.user_id == user_id
    ).order_by(ChatHistory.created_at).all()
    
    # authors 파싱
    authors = parse_json_field(paper.authors)
    
    # summary 구성
    summary = None
    if metadata and metadata.summary_level and metadata.summary_content:
        summary = SummaryResponse(
            level=metadata.summary_level,
            content=metadata.summary_content
        )
    
    # metadata 구성
    metadata_response = None
    if metadata:
        keywords = parse_json_field(metadata.keywords)
        metadata_response = MetadataResponse(
            citation_count=metadata.citation_count or 0,
            citation_velocity=metadata.citation_velocity or 0.0,
            influential_citation_count=metadata.influential_citation_count or 0,
            keywords=keywords
        )
    
    # chat_history 구성
    chat_history_list = []
    for chat in chat_histories:
        chat_history_list.append(ChatHistoryItem(
            chat_id=chat.id,
            question=chat.question,
            answer=chat.answer,
            created_at=chat.created_at.isoformat() + "Z" if chat.created_at else ""
        ))
    
    return PaperDetailResponse(
        paper_id=paper.paper_id,
        title=paper.title,
        authors=authors,
        published_date=paper.published_date or "",
        source=paper.source or "",
        arxiv_id=paper.external_id if paper.source == "arXiv" else None,
        pdf_url=paper.pdf_url,
        abstract=paper.abstract,
        summary=summary,
        metadata=metadata_response,
        chat_history=chat_history_list
    )

# ==================== 카카오톡 공유 ====================

# KakaoShareRequest 모델 수정
class KakaoShareRequest(BaseModel):
    paper_title: str
    pdf_url: Optional[str] = None
    ai_summary: Optional[str] = None


@router.post("/papers/{paper_id}/share-kakao", status_code=status.HTTP_200_OK)
async def share_paper_to_kakao(
    paper_id: int,
    request: KakaoShareRequest,
    db: Session = Depends(get_db)
):
    """
    논문 정보를 카카오톡 나와의 채팅방에 공유
    """
    try:
        # 논문이 존재하는지 확인
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="논문을 찾을 수 없습니다."
            )
        
        # 카카오톡 메시지 구성 (포맷팅)
        message_parts = [
            "📚 Research Mate에서 추천한 논문을 공유해요!",
            "",
            "📄 논문 제목",
            f"{request.paper_title}",
            ""
        ]
        
        # PDF URL 추가
        if request.pdf_url:
            message_parts.extend([
                "🔗 PDF 다운로드",
                f"{request.pdf_url}",
                ""
            ])
        
        # AI 설명 추가
        if request.ai_summary:
            message_parts.extend([
                "🤖 AI가 설명하는 이 논문",
                f"{request.ai_summary}"
            ])
        
        message = "\n".join(message_parts)
        
        # 200자 초과 시 AI 설명 제거하고 안내 메시지로 대체
        if len(message) > 200:
            message_parts_without_ai = [
                "📚 Research Mate에서 추천한 논문을 공유해요!",
                "",
                "📄 논문 제목",
                f"{request.paper_title}",
                ""
            ]
            
            if request.pdf_url:
                message_parts_without_ai.extend([
                    "🔗 PDF 다운로드",
                    f"{request.pdf_url}",
                    ""
                ])
            
            message_parts_without_ai.extend([
                "💡 이 논문에 대한 AI 맞춤 설명은 Research Mate에서 확인해보세요!"
            ])
            
            message = "\n".join(message_parts_without_ai)
        
        # PlayMCP를 통해 카카오톡 전송
        result = await playmcp_client.send_kakao_message(message)
        
        return {
            "success": True,
            "message": "카카오톡으로 공유되었습니다.",
            "result": result
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"카카오톡 공유 중 오류가 발생했습니다: {str(e)}"
        )

class CalendarEventRequest(BaseModel):
    event_date: str  # YYYY-MM-DD 형식


@router.post("/add-to-calendar", status_code=status.HTTP_200_OK)
async def add_to_calendar(request: CalendarEventRequest):
    """
    내일 Research Mate 사용 알림 일정을 톡캘린더에 추가
    """
    try:
        from datetime import datetime, timedelta # 이 두 가지를 추가해야 합니다.
        
        # 고정된 제목/설명
        title = "Research Mate에서 오늘의 추천 논문 확인하기"
        description = "오늘도 화이팅!"
        
        # 날짜/시간 포맷 변환 (하루종일 고정)
        event_date = request.event_date # YYYY-MM-DD
        
        # 1. start_date 설정
        start_date = datetime.strptime(event_date, "%Y-%m-%d").date()
        
        # 2. end_date는 시작일 다음 날 (하루 종일 일정의 표준)
        end_date = start_date + timedelta(days=1)
        
        # 3. PlayMCP 형식 (T00:00:00)으로 변환
        start_at = f"{start_date.strftime('%Y-%m-%d')}T00:00:00"
        end_at = f"{end_date.strftime('%Y-%m-%d')}T00:00:00" # <--- 이 부분이 핵심 수정
        
        # 고정된 알림 설정 (30분 전, 1일 전)
        reminders = [30, 1440]
        
        # PlayMCP를 통해 톡캘린더에 일정 생성
        result = await playmcp_client.create_calendar_event(
            title=title,
            start_at=start_at,
            end_at=end_at, # 수정된 end_at 사용
            all_day=True,
            description=description,
            reminders=reminders
        )
        
        return {
            "success": True,
            "message": "톡캘린더에 일정이 추가되었습니다.",
            "result": result,
            "event_summary": {
                "title": title,
                "date": event_date,
                "time": "하루종일"
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"톡캘린더 일정 추가 중 오류가 발생했습니다: {str(e)}"
        )