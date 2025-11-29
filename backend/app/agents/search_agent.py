import arxiv
import requests
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.utils.kanana import call_kanana # 키워드 확장용 LLM 호출
from app.models import Paper, User

class SearchAgent:
    """논문 검색 Agent: 키워드 확장, arXiv 검색, Semantic Scholar 메타데이터 보강"""
    
    def __init__(self, db: Session):
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
        self.db = db
    
    def expand_keywords(self, interest: str) -> List[str]:
        """LLM으로 관심 분야 키워드 확장"""
        prompt = f"""다음 연구 관심 분야와 관련된 검색 키워드 5개를 영어로 제시해주세요.
각 키워드는 논문 검색에 적합한 형태여야 합니다.
관심 분야: {interest}

키워드만 쉼표로 구분하여 나열해주세요. 예: RAG, Retrieval Augmented Generation, retrieval-based QA"""
        
        response = call_kanana(prompt, temperature=0.3, max_tokens=256)
        keywords = [k.strip() for k in response.replace("\n", "").split(",")]
        return keywords[:5]  # 최대 5개
    
    def search_arxiv(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
        """arXiv API로 논문 검색"""
        papers = []
        query = " OR ".join([f'all:"{kw}"' for kw in keywords[:3]])  # 상위 3개 키워드로 검색
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=min(max_results,50),
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            for result in search.results():
                papers.append({
                    "arxiv_id": result.entry_id.split("/")[-1],
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "abstract": result.summary,
                    "published_date": result.published.strftime("%Y-%m-%d") if result.published else None,
                    "pdf_url": result.pdf_url,
                    "categories": result.categories
                })
        except Exception as e:
            print(f"arXiv 검색 오류: {e}")
        
        return papers
    
    def enrich_with_semantic_scholar(self, papers: List[Dict]) -> List[Dict]:
        """Semantic Scholar API로 메타데이터 보강"""
        enriched = []
        
        for paper in papers:
            arxiv_id = paper.get("arxiv_id", "")
            if not arxiv_id:
                enriched.append(paper)
                continue
            
            try:
                # arXiv ID로 Semantic Scholar에서 검색
                url = f"{self.semantic_scholar_base}/paper/arXiv:{arxiv_id}"
                params = {
                    "fields": "citationCount,citationVelocity,influentialCitationCount,year,venue"
                }
                response = requests.get(url, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    paper["citation_count"] = data.get("citationCount", 0)
                    paper["citation_velocity"] = data.get("citationVelocity", 0)
                    paper["influential_citation_count"] = data.get("influentialCitationCount", 0)
                    paper["year"] = data.get("year")
                    paper["venue"] = data.get("venue", "")
                else:
                    # 기본값 설정
                    paper["citation_count"] = 0
                    paper["citation_velocity"] = 0
                    paper["influential_citation_count"] = 0
            except Exception as e:
                print(f"Semantic Scholar 보강 오류 (arXiv:{arxiv_id}): {e}")
                paper["citation_count"] = 0
                paper["citation_velocity"] = 0
                paper["influential_citation_count"] = 0
            
            enriched.append(paper)
        
        return enriched
    
    def _check_existing_paper(self, arxiv_id: str) -> Optional[Paper]:
        """DB에 이미 존재하는 논문인지 확인"""
        return self.db.query(Paper).filter(Paper.external_id == f"arXiv:{arxiv_id}").first()
    
    def get_user_interest(self, user_id: int) -> str | None :
        """DB에서 사용자의 관심 분야 가져오기"""
        
        user = self.db.query(User).filter(User.user_id == user_id).first()
        return user.interest if user else None
    
    def search(self, interest: Optional[str] = None, user_id: Optional[int] = None, max_results: int = 20) -> List[Dict]:
        """전체 검색 프로세스 실행
        
        Args:
            interest: 관심 분야 (직접 입력)
            user_id: 사용자 ID (DB에서 interest 가져오기)
            max_results: 최대 검색 결과 수
        """
        # interest가 없으면 DB에서 가져오기
        if not interest and user_id and self.db:
            interest = self.get_user_interest(user_id)
        
        if not interest:
            raise ValueError("interest 또는 user_id가 필요합니다.")
        
        # 1. 키워드 확장
        keywords = self.expand_keywords(interest)
        print(f"확장된 키워드: {keywords}")
        
        # 2. arXiv 검색
        papers = self.search_arxiv(keywords, max_results)
        print(f"arXiv 검색 결과: {len(papers)}편")
        
        # 3. Semantic Scholar 메타데이터 보강
        enriched_papers = self.enrich_with_semantic_scholar(papers)
        
        # 4. DB에 이미 존재하는 논문인지 확인 (중복 방지)
        if self.db:
            arxiv_ids = [p["arxiv_id"] for p in enriched_papers if p.get("arxiv_id")]
            external_ids = [f"arXiv:{aid}" for aid in arxiv_ids]
            existing_papers = (
                self.db.query(Paper)
                .filter(Paper.external_id.in_(external_ids))
                .all()
            )
            existing_map = {p.external_id: p for p in existing_papers}

            for paper in enriched_papers:
                aid = paper.get("arxiv_id")
                if not aid:
                    continue
                ext_id = f"arXiv:{aid}"
                existing = existing_map.get(ext_id)
                paper["exists_in_db"] = existing is not None
                if existing:
                    paper["db_paper_id"] = existing.paper_id
        
        return enriched_papers

