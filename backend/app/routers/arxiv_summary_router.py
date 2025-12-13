"""
arXiv ID 기반 논문 추가 라우터
backend/app/routers/arxiv_summary_router.py
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Literal
import json
import arxiv

from app.database import get_db
from app.models import Paper, PaperMetadata, User, Recommendation
from app.agents.paper_description_agent import PaperDescriptionAgent
from datetime import datetime


router = APIRouter(
    prefix="/papers",
    tags=["papers"]
)


# Request/Response 모델
class ArxivAddRequest(BaseModel):
    arxiv_id: str = Field(..., description="arXiv 논문 ID (예: 2005.11401)")
    user_id: int = Field(..., description="사용자 ID")


class ArxivAddResponse(BaseModel):
    message: str


def fetch_arxiv_paper(arxiv_id: str) -> dict:
    """arXiv API로 논문 정보 가져오기"""
    try:
        
        # arxiv_id 정규화 (접두사, 버전 번호 제거)
        clean_id = arxiv_id.replace("arXiv:", "").replace("arxiv:", "").split("v")[0].strip()
        
        # arXiv API 호출
        client = arxiv.Client()
        search = arxiv.Search(id_list=[clean_id])
        paper = next(client.results(search))
        
        return {
            "arxiv_id": clean_id,
            "title": paper.title,
            "authors": [author.name for author in paper.authors],
            "abstract": paper.summary,
            "published_date": paper.published.strftime("%Y-%m-%d") if paper.published else None,
            "pdf_url": paper.pdf_url,
            "categories": paper.categories
        }
    except StopIteration:
        raise HTTPException(status_code=404, detail=f"arXiv 논문을 찾을 수 없습니다: {arxiv_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"arXiv API 오류: {str(e)}")


def get_semantic_scholar_metadata(arxiv_id: str) -> dict:
    """Semantic Scholar API로 인용 정보 가져오기"""
    import requests
    
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"
        params = {
            "fields": "citationCount,citationVelocity,influentialCitationCount,year,venue"
        }
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "citation_count": data.get("citationCount", 0),
                "citation_velocity": data.get("citationVelocity", 0),
                "influential_citation_count": data.get("influentialCitationCount", 0),
                "year": data.get("year"),
                "venue": data.get("venue", "")
            }
    except Exception as e:
        print(f"Semantic Scholar API 오류: {e}")
    
    # 기본값 반환
    return {
        "citation_count": 0,
        "citation_velocity": 0,
        "influential_citation_count": 0,
        "year": None,
        "venue": ""
    }


def save_paper_to_db(paper_data: dict, db: Session) -> int:
    """논문을 DB에 저장하고 paper_id 반환"""
    arxiv_id = paper_data.get("arxiv_id")
    external_id = f"arXiv:{arxiv_id}"
    
    # 이미 존재하는 논문인지 확인
    existing = db.query(Paper).filter(Paper.external_id == external_id).first()
    
    if existing:
        paper_id = existing.paper_id
        # 기존 논문 업데이트
        existing.title = paper_data.get("title", existing.title)
        existing.authors = json.dumps(paper_data.get("authors", []))
        existing.published_date = paper_data.get("published_date")
        existing.source = "arXiv"
        existing.pdf_url = paper_data.get("pdf_url")
        existing.abstract = paper_data.get("abstract")
    else:
        # 새 논문 생성
        new_paper = Paper(
            title=paper_data.get("title", ""),
            authors=json.dumps(paper_data.get("authors", [])),
            published_date=paper_data.get("published_date"),
            source="arXiv",
            external_id=external_id,
            pdf_url=paper_data.get("pdf_url"),
            abstract=paper_data.get("abstract", "")
        )
        db.add(new_paper)
        db.flush()
        paper_id = new_paper.paper_id
    
    # PaperMetadata 저장/업데이트
    metadata = db.query(PaperMetadata).filter(
        PaperMetadata.paper_id == paper_id
    ).first()
    
    if not metadata:
        metadata = PaperMetadata(paper_id=paper_id)
        db.add(metadata)
    
    # Semantic Scholar 메트릭 저장
    metadata.citation_count = paper_data.get("citation_count", 0)
    metadata.citation_velocity = paper_data.get("citation_velocity", 0)
    metadata.influential_citation_count = paper_data.get("influential_citation_count", 0)
    
    # 키워드 저장
    if paper_data.get("categories"):
        metadata.keywords = json.dumps(paper_data["categories"])
    
    db.commit()
    return paper_id


@router.post("/add", response_model=ArxivAddResponse)
async def add_arxiv_paper(
    request: ArxivAddRequest,
    db: Session = Depends(get_db)
):
    """
    arXiv ID로 논문을 DB에 추가
    
    - DB에 이미 있으면: "이미 학습한 논문입니다"
    - DB에 없으면: arXiv에서 가져와서 저장 후 "논문이 추가되었습니다. '지금까지 공부한 논문' 화면에서 확인하실 수 있어요!"
    
    Args:
        - arxiv_id: arXiv 논문 ID (예: 2005.11401, arXiv:2005.11401 둘 다 가능)
        - level: beginner, intermediate, advanced
    
    Returns:
        - message: 처리 결과 메시지
    """
    # ✅ 디버깅: 받은 데이터 출력
    print(f"📥 받은 데이터: arxiv_id={request.arxiv_id}, user_id={request.user_id}")
    


    try:

        # 1. user_id로 사용자 조회 및 level 가져오기
        user = db.query(User).filter(User.user_id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        level = user.level  # ✅ User 테이블에서 level 가져오기
        print(f"👤 사용자: user_id={request.user_id}, level={level}")

        # arxiv_id 정규화
        clean_id = request.arxiv_id.replace("arXiv:", "").replace("arxiv:", "").split("v")[0].strip()
        external_id = f"arXiv:{clean_id}"
        
        # DB에 이미 존재하는지 확인
        existing_paper = db.query(Paper).filter(Paper.external_id == external_id).first()
        
        if existing_paper:
            # 이미 학습한 논문
            print(f"⚠️  이미 DB에 존재하는 논문: paper_id={existing_paper.paper_id}")
            return ArxivAddResponse(message="이미 학습한 논문입니다")
        
        # 새로운 논문 처리
        print(f"🔍 새로운 논문 - arXiv 조회 중: {clean_id}")
        
        # 1. arXiv에서 논문 정보 가져오기
        paper_data = fetch_arxiv_paper(clean_id)
        
        # 2. Semantic Scholar에서 인용 정보 가져오기
        print(f"📊 Semantic Scholar 메타데이터 조회 중...")
        ss_metadata = get_semantic_scholar_metadata(paper_data["arxiv_id"])
        paper_data.update(ss_metadata)
        
        # 3. DB에 저장
        print(f"💾 DB에 저장 중...")
        paper_id = save_paper_to_db(paper_data, db)
        paper_data["paper_id"] = paper_id
        paper_data["db_paper_id"] = paper_id
        
        # 4. 요약 생성
        print(f"✍️  요약 생성 중 (level={level})...")  # ✅ 수정
        description_agent = PaperDescriptionAgent(db=db)
        description_agent.describe(paper_data, level=level)  # ✅ 수정
        
        # 5. Recommendation 테이블에 추가 (사용자가 직접 요청한 논문)
        print(f"📝 Recommendation 테이블에 추가 중...")
        recommendation = Recommendation(
            user_id=request.user_id,
            paper_id=paper_id,
            recommended_at=datetime.utcnow(),
            is_user_requested=True,
            requested_paper_id=paper_id
        )
        db.add(recommendation)
        db.commit()
        
        # 6. 성공 메시지 반환
        print(f"✅ 완료: paper_id={paper_id}")
        
        return ArxivAddResponse(
            message="논문이 추가되었습니다. '지금까지 공부한 논문' 화면에서 확인하실 수 있어요!"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"논문 추가 중 오류 발생: {str(e)}")