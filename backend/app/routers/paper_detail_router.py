from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_db
from app.models import Paper, PaperMetadata, Recommendation, ChatHistory

router = APIRouter(tags=["papers_detail"])


# ==================== Response 모델 ====================

class PaperHistoryItem(BaseModel):
    paper_id: int
    title: str
    authors: List[str]
    recommended_at: str  # YYYY-MM-DD 형식


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
    전체 논문 목록 조회
    정렬: recommended_at 내림차순 (최신순)
    """
    # 사용자의 추천 논문 목록 조회 (recommended_at 내림차순)
    recommendations = db.query(Recommendation).filter(
        Recommendation.user_id == user_id
    ).order_by(desc(Recommendation.recommended_at)).all()
    
    papers_list = []
    for rec in recommendations:
        paper = rec.paper
        if not paper:
            continue
        
        # authors 파싱
        authors = parse_json_field(paper.authors)
        
        # recommended_at을 YYYY-MM-DD 형식으로 변환
        recommended_at_str = format_date(rec.recommended_at)
        if not recommended_at_str:
            continue
        
        papers_list.append(PaperHistoryItem(
            paper_id=paper.paper_id,
            title=paper.title,
            authors=authors,
            recommended_at=recommended_at_str
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

