import requests
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.utils.kanana import call_kanana
from app.models import Paper, CitationGraph


class RelationAnalysisAgent:
    """관계 분석 Agent: Semantic Scholar 인용 관계 분석, 그래프 데이터 생성, 자연어 설명"""
    
    def __init__(self, db: Session):
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
        self.db = db
    

    def get_citations(self, arxiv_id: str) -> Dict:
        """Semantic Scholar에서 인용/참고문헌 관계 가져오기"""
        try:
            url = f"{self.semantic_scholar_base}/paper/arXiv:{arxiv_id}"
            params = {
                "fields": (
                    "citations.paperId,citations.title,citations.authors,"
                    "references.paperId,references.title,references.authors"
                )
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(
                    f"인용 관계 조회 실패 (arXiv:{arxiv_id}, "
                    f"status={response.status_code}, text={response.text[:200]!r})"
                )
                return {}
        except Exception as e:
            print(f"인용 관계 조회 오류 (arXiv:{arxiv_id}): {e}")
            return {}
    

    def find_common_citations(self, papers: List[Dict]) -> Dict:
        """
        여러 논문 간 공통 인용 논문 찾기 + 각 논문이 인용한 논문 ID 집합 유지
        
        반환:
            {
              "papers": [
                {
                  "arxiv_id": "2301.00001",
                  "title": "...",
                  "cited_ids": { "SS_paper_id_1", "SS_paper_id_2", ... }
                },
                ...
              ],
              "common_citation_ids": ["SS_paper_id_1", "SS_paper_id_3", ...]
            }
        """
        if len(papers) < 2:
            return {}
        
        citation_sets = []
        for paper in papers:
            arxiv_id = paper.get("arxiv_id")
            if not arxiv_id:
                continue
            
            data = self.get_citations(arxiv_id)
            cited_ids = {
                ref.get("paperId")
                for ref in data.get("references", [])
                if ref.get("paperId")
            }
            
            citation_sets.append({
                "arxiv_id": arxiv_id,
                "title": paper.get("title", ""),
                "cited_ids": cited_ids
            })
        
        if len(citation_sets) < 2:
            return {}
        
        # 모든 논문이 공통으로 인용한 논문 ID 집합
        common_citations = set(citation_sets[0]["cited_ids"])
        for citation_set in citation_sets[1:]:
            common_citations &= citation_set["cited_ids"]
        
        return {
            "papers": citation_sets,
            "common_citation_ids": list(common_citations)[:10]  # 최대 10개
        }
    

    def build_graph_data(
        self,
        papers: List[Dict],
        common_data: Optional[Dict] = None
    ) -> Dict:
        """
        그래프 데이터 구조 생성.
        - nodes: 논문 / 공통 인용 논문
        - edges: 실제로 인용 관계가 있는 경우에만 생성
        """
        nodes: List[Dict] = []
        edges: List[Dict] = []
        
        # 원 논문 노드
        for i, paper in enumerate(papers):
            nodes.append({
                "id": paper.get("arxiv_id", f"paper_{i}"),
                "label": paper.get("title", ""),
                "type": "paper"
            })
        
        # 공통 인용 데이터가 없다면 새로 계산
        if common_data is None:
            common_data = self.find_common_citations(papers)
        
        citation_sets = common_data.get("papers", [])
        common_ids = set(common_data.get("common_citation_ids", []))
        
        # 공통 인용 논문 노드
        for i, cited_id in enumerate(common_ids):
            nodes.append({
                "id": cited_id,
                "label": f"Cited Paper {i+1}",
                "type": "cited_paper"
            })
        
        # 실제로 그 논문이 그 cited_id를 인용하는 경우에만 엣지 생성
        for cset in citation_sets:
            src_arxiv = cset["arxiv_id"]
            for cited_id in cset["cited_ids"]:
                if cited_id in common_ids:
                    edges.append({
                        "source": src_arxiv,
                        "target": cited_id,
                        "type": "cites"
                    })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "common_citations_count": len(common_ids)
        }
    

    def generate_explanation(self, graph_data: Dict, papers: List[Dict]) -> str:
        """LLM으로 관계 구조를 자연어 설명으로 변환"""
        paper_titles = [p.get("title", "") for p in papers]
        common_count = graph_data.get("common_citations_count", 0)
        
        prompt = f"""다음 논문들 간의 인용 관계를 분석하여 사용자에게 친절하게 설명해주세요.

논문 목록:
{chr(10).join([f"- {title}" for title in paper_titles])}

공통으로 인용하는 논문 수: {common_count}개

이 정보를 바탕으로 논문들 간의 관계와 연구 맥락을 설명하고, 
공통 인용 논문이 있다면 그것이 의미하는 바를 설명해주세요.
한국어로 2-3문단으로 작성해주세요."""
        
        explanation = call_kanana(prompt, temperature=0.3, max_tokens=512)
        return explanation
    

    def _save_citation_relations(
        self,
        arxiv_to_db: Dict[str, int],
        citation_data: Dict
    ):
        """
        인용 관계를 DB에 저장.
        arxiv_to_db: arXiv ID -> DB paper_id 매핑
        citation_data: find_common_citations() 결과
        """
        if not self.db or not arxiv_to_db:
            return
        
        try:
            for paper_dict in citation_data.get("papers", []):
                arxiv_id = paper_dict.get("arxiv_id")
                if not arxiv_id:
                    continue
                
                citing_paper_id = arxiv_to_db.get(arxiv_id)
                if not citing_paper_id:
                    continue
                
                # 이 논문이 인용하는 모든 Semantic Scholar paperId에 대해
                for ref_paper_id in paper_dict.get("cited_ids", set()):
                    if not ref_paper_id:
                        continue
                    
                    # DB에서 해당 ref_paper_id와 매칭되는 논문 찾기
                    cited_paper = (
                        self.db.query(Paper)
                        .filter(Paper.external_id.like(f"%{ref_paper_id}%"))
                        .first()
                    )
                    
                    if not cited_paper or cited_paper.paper_id == citing_paper_id:
                        continue
                    
                    # 중복 관계 체크
                    existing = (
                        self.db.query(CitationGraph)
                        .filter(
                            CitationGraph.citing_paper_id == citing_paper_id,
                            CitationGraph.cited_paper_id == cited_paper.paper_id
                        )
                        .first()
                    )
                    
                    if not existing:
                        citation = CitationGraph(
                            citing_paper_id=citing_paper_id,
                            cited_paper_id=cited_paper.paper_id,
                            relation_type="reference",
                            is_influential=0
                        )
                        self.db.add(citation)
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"인용 관계 저장 오류: {e}")
    

    def analyze(self, papers: List[Dict]) -> Dict:
        """전체 관계 분석 프로세스 실행"""
        # 1) arXiv ID -> DB paper_id 매핑 만들기
        arxiv_to_db: Dict[str, int] = {}
        paper_ids: List[int] = []
        
        for paper in papers:
            arxiv_id = paper.get("arxiv_id")
            if not arxiv_id:
                continue
            
            db_paper = self.db.query(Paper).filter(
                Paper.external_id == f"arXiv:{arxiv_id}"
            ).first()
            
            if db_paper:
                arxiv_to_db[arxiv_id] = db_paper.paper_id
                paper_ids.append(db_paper.paper_id)
                paper["db_paper_id"] = db_paper.paper_id
        
        # 2) 공통 인용 분석 + 그래프 생성
        common_data = self.find_common_citations(papers)
        graph_data = self.build_graph_data(papers, common_data)
        
        # 3) LLM 설명 생성
        explanation = self.generate_explanation(graph_data, papers)
        
        # 4) 인용 관계 DB 저장
        if arxiv_to_db and common_data:
            self._save_citation_relations(arxiv_to_db, common_data)
        
        return {
            "graph": graph_data,
            "explanation": explanation,
            "paper_ids": paper_ids
        }