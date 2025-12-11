from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime, date, timedelta
import json

from app.utils.kanana import call_kanana
from starlette.concurrency import run_in_threadpool
import logging


from app.database import get_db
from app.models import Paper, Recommendation, CitationGraph
from app.agents.relation_analysis_agent import RelationAnalysisAgent

router = APIRouter(tags=["recommendations"])

logger = logging.getLogger(__name__)

# ==================== Request/Response 모델 ====================

class PaperItem(BaseModel):
    paper_id: int
    title: str
    authors: List[str]
    recommended_at: str  # YYYY-MM-DD 형식


class TodayRecommendationsResponse(BaseModel):
    date: str  # YYYY-MM-DD 형식ㅌ
    papers: List[PaperItem]
    total_count: int


class RequestPaperRequest(BaseModel):
    paper_id: int = Field(..., description="논문 ID")
    reason: Literal["common_reference"] = Field(..., description="추천 사유")


class RequestPaperResponse(BaseModel):
    message: str
    paper_id: int
    title: str
    scheduled_date: str  # YYYY-MM-DD 형식


# ==================== Relations API Response 모델 ====================

class GraphNode(BaseModel):
    id: int
    title: str
    type: str  # "recommended" or "common_reference"


class GraphEdge(BaseModel):
    source: int
    target: int
    type: str  # "cites"
    is_influential: bool


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class CommonReference(BaseModel):
    paper_id: int
    title: str
    cited_by_count: int
    suggestion: str


class Cluster(BaseModel):
    theme: str
    papers: List[int]


class AnalysisData(BaseModel):
    common_references: List[CommonReference]
    clusters: List[Cluster]


class TodayRelationsResponse(BaseModel):
    date: str  # YYYY-MM-DD 형식
    graph: GraphData
    analysis: AnalysisData


# ==================== 유틸리티 함수 ====================

def parse_json_field(field_value: str) -> List[str]:
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


def format_date(date_obj: datetime) -> str:
    """datetime을 YYYY-MM-DD 형식으로 변환"""
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%Y-%m-%d")
    elif isinstance(date_obj, date):
        return date_obj.strftime("%Y-%m-%d")
    return ""


# ==================== API 엔드포인트 ====================

@router.get("/{user_id}/recommendations/today", response_model=TodayRecommendationsResponse, status_code=status.HTTP_200_OK)
async def get_today_recommendations(user_id: int, db: Session = Depends(get_db)):
    """
    오늘의 추천 논문 조회
    """
    # 오늘 날짜 (시간 제외)
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # 오늘 날짜의 추천 논문 조회
    recommendations = db.query(Recommendation).filter(
        and_(
            Recommendation.user_id == user_id,
            Recommendation.recommended_at >= today_start,
            Recommendation.recommended_at <= today_end
        )
    ).order_by(Recommendation.recommended_at.desc()).all()
    
    papers_list = []
    for rec in recommendations:
        paper = rec.paper
        if not paper:
            continue
        
        # authors 파싱
        authors = parse_json_field(paper.authors) if paper.authors else []
        
        # recommended_at을 YYYY-MM-DD 형식으로 변환
        recommended_at_str = format_date(rec.recommended_at)
        if not recommended_at_str:
            continue
        
        papers_list.append(PaperItem(
            paper_id=paper.paper_id,
            title=paper.title,
            authors=authors,
            recommended_at=recommended_at_str
        ))
    
    return TodayRecommendationsResponse(
        date=today.strftime("%Y-%m-%d"),
        papers=papers_list,
        total_count=len(papers_list)
    )


@router.get("/{user_id}/recommendations/today/relations", response_model=TodayRelationsResponse, status_code=status.HTTP_200_OK)
async def get_today_recommendations_relations(user_id: int, db: Session = Depends(get_db)):
    """
    오늘의 추천 논문 인용 관계 분석
    """
    # 오늘 날짜 (시간 제외)
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # 오늘 날짜의 추천 논문 조회
    recommendations = db.query(Recommendation).filter(
        and_(
            Recommendation.user_id == user_id,
            Recommendation.recommended_at >= today_start,
            Recommendation.recommended_at <= today_end
        )
    ).order_by(Recommendation.recommended_at.desc()).all()
    
    if len(recommendations) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="오늘 추천된 논문이 없습니다."
        )
    
    # 논문 정보 수집 (RelationAnalysisAgent용 형식)
    papers_for_analysis = []
    paper_id_to_paper = {}
    
    for rec in recommendations:
        paper = rec.paper
        if not paper:
            continue
        
        # external_id에서 arxiv_id 추출
        arxiv_id = None
        if paper.external_id:
            if paper.external_id.startswith("arXiv:"):
                arxiv_id = paper.external_id.replace("arXiv:", "")
            else:
                arxiv_id = paper.external_id
        
        if not arxiv_id:
            continue
        
        paper_dict = {
            "arxiv_id": arxiv_id,
            "title": paper.title,
            "db_paper_id": paper.paper_id
        }
        papers_for_analysis.append(paper_dict)
        paper_id_to_paper[paper.paper_id] = paper
    
    if len(papers_for_analysis) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="분석할 수 있는 논문이 없습니다. (arXiv ID 필요)"
        )
    
    # 노드 생성 (추천 논문 + 공통 인용 논문)
    nodes = []
    edges = []
    
    # 추천 논문 노드 생성
    recommended_paper_ids = []
    for paper_dict in papers_for_analysis:
        paper_id = paper_dict.get("db_paper_id")
        if paper_id:
            nodes.append(GraphNode(
                id=paper_id,
                title=paper_dict.get("title", ""),
                type="recommended"
            ))
            recommended_paper_ids.append(paper_id)
    
    # DB의 CitationGraph에서 공통 인용 논문 찾기
    common_references = []  # 여기서 초기화
    
    if len(recommended_paper_ids) >= 2:
        # 각 추천 논문이 인용하는 논문들 찾기
        citations = db.query(CitationGraph).filter(
            CitationGraph.citing_paper_id.in_(recommended_paper_ids)
        ).all()
        
        # cited_paper_id별로 인용한 논문 수 집계
        cited_paper_counts = {}
        citation_edges = {}  # (citing_id, cited_id) -> is_influential
        
        for citation in citations:
            cited_id = citation.cited_paper_id
            citing_id = citation.citing_paper_id
            
            if cited_id not in cited_paper_counts:
                cited_paper_counts[cited_id] = 0
            cited_paper_counts[cited_id] += 1
            
            # 에지 정보 저장
            key = (citing_id, cited_id)
            citation_edges[key] = bool(citation.is_influential)
        
        # 모든 추천 논문이 공통으로 인용한 논문 찾기 (인용 수가 추천 논문 수와 같으면 공통 인용)
        common_reference_papers = []
        for cited_id, count in cited_paper_counts.items():
            if count == len(recommended_paper_ids):  # 모든 추천 논문이 인용
                cited_paper = db.query(Paper).filter(Paper.paper_id == cited_id).first()
                if cited_paper:
                    # common_reference 노드 추가
                    if not any(node.id == cited_paper.paper_id for node in nodes):
                        nodes.append(GraphNode(
                            id=cited_paper.paper_id,
                            title=cited_paper.title,
                            type="common_reference"
                        ))
                    
                    # 에지 생성
                    edge_list = []
                    for citing_id in recommended_paper_ids:
                        key = (citing_id, cited_id)
                        is_influential = citation_edges.get(key, False)
                        edges.append(GraphEdge(
                            source=citing_id,
                            target=cited_id,
                            type="cites",
                            is_influential=is_influential
                        ))
                        edge_list.append({
                            "source": citing_id,
                            "target": cited_id,
                            "is_influential": is_influential
                        })
                    
                    common_reference_papers.append({
                        "paper": cited_paper,
                        "cited_by_count": count,
                        "edges": edge_list
                    })
        
        # 공통 참고문헌 정보 생성
        if len(common_reference_papers) == 0:
            # 공통 인용 논문이 없는 경우 - 빈 리스트 유지
            pass
        elif len(common_reference_papers) == 1:
            # 공통 인용 논문이 1개인 경우 - 바로 추가
            ref_info = common_reference_papers[0]
            paper = ref_info["paper"]
            cited_count = ref_info["cited_by_count"]
            suggestion = f"오늘 추천된 논문 {cited_count}편이 모두 이 논문을 인용하고 있습니다. 내일 추천해드릴까요?"
            
            common_references.append(CommonReference(
                paper_id=paper.paper_id,
                title=paper.title,
                cited_by_count=cited_count,
                suggestion=suggestion
            ))
        else:
            # 공통 인용 논문이 여러 개인 경우 - Kanana로 하나 선택
            try:
                # 오늘 추천된 논문 제목 리스트
                recommended_titles = [p.get("title", "") for p in papers_for_analysis]
                
                # 공통 인용 논문 제목 리스트
                common_ref_titles = [ref_info["paper"].title for ref_info in common_reference_papers]
                
                # Kanana 프롬프트 생성
                prompt = f"""오늘 추천된 논문 3개와 이들이 공통으로 인용하는 논문들이 있습니다.
사용자에게 다음으로 추천할 논문을 공통 인용 논문 중에서 1개만 선택해주세요.

**오늘 추천된 논문:**
{chr(10).join(f"{i+1}. {title}" for i, title in enumerate(recommended_titles))}

**공통으로 인용하는 논문들:**
{chr(10).join(f"{i+1}. {title}" for i, title in enumerate(common_ref_titles))}

위 3개의 추천 논문과 관계가 가장 깊다고 판단되는 공통 인용 논문 1개를 선택하고, 그 이유를 간단히 설명해주세요.

응답 형식은 반드시 다음과 같이 해주세요:
선택된 논문 번호: [번호]
이유: [한 문장으로 간단히]"""

                # Kanana 호출 (비동기)
                response_text = await run_in_threadpool(call_kanana, prompt)
                
                if not response_text:
                    raise Exception("Kanana에서 응답을 받지 못했습니다.")
                
                # 응답 파싱
                selected_index = None
                for line in response_text.split('\n'):
                    if '선택된 논문 번호' in line or '선택' in line:
                        # 숫자 추출
                        import re
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            selected_index = int(numbers[0]) - 1  # 0-based index
                            break
                
                # 선택된 논문 추가
                if selected_index is not None and 0 <= selected_index < len(common_reference_papers):
                    ref_info = common_reference_papers[selected_index]
                    paper = ref_info["paper"]
                    cited_count = ref_info["cited_by_count"]
                    suggestion = f"오늘 추천된 논문 {cited_count}편이 모두 이 논문을 인용하고 있습니다. 내일 추천해드릴까요?"
                    
                    common_references.append(CommonReference(
                        paper_id=paper.paper_id,
                        title=paper.title,
                        cited_by_count=cited_count,
                        suggestion=suggestion
                    ))
                else:
                    # 파싱 실패 시 첫 번째 논문 선택
                    logger.warning(f"Kanana 응답 파싱 실패. 첫 번째 논문 선택. 응답: {response_text}")
                    ref_info = common_reference_papers[0]
                    paper = ref_info["paper"]
                    cited_count = ref_info["cited_by_count"]
                    suggestion = f"오늘 추천된 논문 {cited_count}편이 모두 이 논문을 인용하고 있습니다. 내일 추천해드릴까요?"
                    
                    common_references.append(CommonReference(
                        paper_id=paper.paper_id,
                        title=paper.title,
                        cited_by_count=cited_count,
                        suggestion=suggestion
                    ))
                    
            except Exception as e:
                # Kanana 호출 실패 시 첫 번째 논문 선택
                logger.error(f"Kanana를 이용한 논문 선택 실패: {e}", exc_info=True)
                ref_info = common_reference_papers[0]
                paper = ref_info["paper"]
                cited_count = ref_info["cited_by_count"]
                suggestion = f"오늘 추천된 논문 {cited_count}편이 모두 이 논문을 인용하고 있습니다. 내일 추천해드릴까요?"
                
                common_references.append(CommonReference(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    cited_by_count=cited_count,
                    suggestion=suggestion
                ))
    
    # 클러스터 생성 (간단한 구현: 제목 키워드 기반)
    clusters = []
    if len(papers_for_analysis) >= 2:
        # 간단한 클러스터링: 제목에 공통 키워드가 있는 논문들을 그룹화
        # 실제로는 더 정교한 클러스터링 알고리즘이 필요
        theme = "Transformer-based Retrieval"  # 예시
        cluster_papers = [p.get("db_paper_id") for p in papers_for_analysis[:2] if p.get("db_paper_id")]
        if cluster_papers:
            clusters.append(Cluster(
                theme=theme,
                papers=cluster_papers
            ))
    
    return TodayRelationsResponse(
        date=today.strftime("%Y-%m-%d"),
        graph=GraphData(
            nodes=nodes,
            edges=edges
        ),
        analysis=AnalysisData(
            common_references=common_references,
            clusters=clusters
        )
    )


@router.post("/{user_id}/recommendations/request-paper", response_model=RequestPaperResponse, status_code=status.HTTP_201_CREATED)
async def request_paper(user_id: int, request: RequestPaperRequest, db: Session = Depends(get_db)):
    """
    공통 참고문헌 추천 수락
    인용 관계 분석을 통해 제안된 다음 추천 논문을 내일 추천 목록에 추가
    """
    # 논문 조회
    paper = db.query(Paper).filter(Paper.paper_id == request.paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="논문을 찾을 수 없습니다."
        )
    
    # 내일 날짜 계산
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_datetime = datetime.combine(tomorrow, datetime.min.time())

    # 내일 날짜로 이미 추천 요청한 논문이 있는지 확인
    existing = db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.paper_id == request.paper_id,
        Recommendation.recommended_at == tomorrow_datetime
    ).first()

    if existing:
        # 이미 추천된 논문일 경우 DB 변경 없이 안내 메시지 반환
        return RequestPaperResponse(
            message="이미 추천받기로 한 논문입니다.",
            paper_id=paper.paper_id,
            title=paper.title,
            scheduled_date=tomorrow.strftime("%Y-%m-%d")
        )

    # 중복이 아니면 새 추천 생성
    new_recommendation = Recommendation(
        user_id=user_id,
        paper_id=request.paper_id,
        recommended_at=tomorrow_datetime,
        is_user_requested=True,
        requested_paper_id=request.paper_id if request.reason == "common_reference" else None
    )
    
    db.add(new_recommendation)
    db.commit()
    db.refresh(new_recommendation)
    
    return RequestPaperResponse(
        message="내일 논문 추천 목록에 추가되었습니다.",
        paper_id=paper.paper_id,
        title=paper.title,
        scheduled_date=tomorrow.strftime("%Y-%m-%d")
    )
