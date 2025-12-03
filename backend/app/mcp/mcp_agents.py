"""
MCP 전용 경량 Agent (DB 저장 없음, 속도 최적화)
backend/mcp/mcp_agents.py
"""

import arxiv
import requests
from typing import List, Dict, Literal
from datetime import datetime
from ..utils.kanana import call_kanana

class MCPSearchAgent:
    """논문 검색 Agent (MCP 전용 - DB 없음)"""
    
    def __init__(self):
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
    
    def expand_keywords(self, interest: str) -> List[str]:
        """LLM으로 관심 분야 키워드 확장"""
        prompt = f"""다음 연구 관심 분야와 관련된 검색 키워드 5개를 영어로 제시해주세요.
각 키워드는 논문 검색에 적합한 형태여야 합니다.
관심 분야: {interest}

키워드만 쉼표로 구분하여 나열해주세요. 예: RAG, Retrieval Augmented Generation, retrieval-based QA"""
        
        response = call_kanana(prompt, temperature=0.3, max_tokens=256)
        keywords = [k.strip() for k in response.replace("\n", "").split(",")]
        return keywords[:5]
    
    def search_arxiv(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
        """arXiv API로 논문 검색"""
        papers = []
        query = " OR ".join([f'all:"{kw}"' for kw in keywords[:3]])
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=min(max_results, 50),
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
    
    def search(self, interest: str, max_results: int = 20) -> List[Dict]:
        """전체 검색 프로세스 실행"""
        # 1. 키워드 확장
        keywords = self.expand_keywords(interest)
        print(f"확장된 키워드: {keywords}")
        
        # 2. arXiv 검색
        papers = self.search_arxiv(keywords, max_results)
        print(f"arXiv 검색 결과: {len(papers)}편")
        
        # 3. Semantic Scholar 메타데이터 보강
        enriched_papers = self.enrich_with_semantic_scholar(papers)
        
        return enriched_papers


class MCPSelectionAgent:
    """논문 선정 Agent (MCP 전용 - 하이브리드 점수 계산, DB/PDF 없음)"""
    
    def __init__(self):
        pass
    
    def calculate_score_heuristic(self, paper: Dict, interest: str) -> float:
        """휴리스틱 기반 빠른 점수 계산 (1단계 필터링용)"""
        scores = {
            "recentness": self._score_recentness(paper),
            "citation": self._score_citation(paper),
            "keyword_simple": self._score_keyword_simple(paper, interest)
        }
        
        weights = {
            "recentness": 0.3,
            "citation": 0.4,
            "keyword_simple": 0.3
        }
        
        return sum(scores[k] * weights[k] for k in scores)
    
    def calculate_score_llm(self, paper: Dict, interest: str, level: str) -> float:
        """LLM 기반 정밀 점수 계산 (2단계 정밀 평가용)"""
        scores = {
            "keyword_match": self._score_keyword_match(paper, interest),
            "difficulty": self._score_difficulty(paper, level)
        }
        
        # 휴리스틱 점수도 포함
        heuristic_score = self.calculate_score_heuristic(paper, interest)
        
        # 최종 점수: 휴리스틱 50% + LLM 50%
        llm_score = (scores["keyword_match"] + scores["difficulty"]) / 2
        return heuristic_score * 0.5 + llm_score * 0.5
    
    def _score_recentness(self, paper: Dict) -> float:
        """최신성 점수 (0-1)"""
        if not paper.get("published_date"):
            return 0.5
        
        try:
            pub_date = datetime.strptime(paper["published_date"], "%Y-%m-%d")
            days_ago = (datetime.now() - pub_date).days
            
            if days_ago <= 30:
                return 1.0
            elif days_ago <= 90:
                return 0.8
            elif days_ago <= 180:
                return 0.6
            elif days_ago <= 365:
                return 0.4
            else:
                return 0.2
        except:
            return 0.5
    
    def _score_citation(self, paper: Dict) -> float:
        """인용 수 점수 (0-1)"""
        citation_count = paper.get("citation_count", 0)
        citation_velocity = paper.get("citation_velocity", 0)
        
        citation_score = min(citation_count / 100, 1.0) if citation_count > 0 else 0
        velocity_score = min(citation_velocity / 10, 1.0) if citation_velocity > 0 else 0
        
        return (citation_score * 0.7 + velocity_score * 0.3)
    
    def _score_keyword_simple(self, paper: Dict, interest: str) -> float:
        """간단한 키워드 매칭 점수 (문자열 포함 여부)"""
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        interest_lower = interest.lower()
        
        # 제목에 포함되면 높은 점수
        if interest_lower in title:
            return 1.0
        
        # 초록에 포함되면 중간 점수
        if interest_lower in abstract:
            return 0.6
        
        # 단어 단위로 매칭
        interest_words = interest_lower.split()
        matches = sum(1 for word in interest_words if word in title or word in abstract)
        return min(matches / len(interest_words), 1.0) if interest_words else 0.3
    
    def _score_keyword_match(self, paper: Dict, interest: str) -> float:
        """키워드 일치도 점수 (LLM 평가)"""
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")[:500]
        
        prompt = f"""다음 논문이 주어진 관심 분야와 얼마나 관련이 있는지 0-1 사이의 점수로 평가해주세요.
관심 분야: {interest}

논문 제목: {title}
초록: {abstract}

관련성 점수만 숫자로 답해주세요 (예: 0.85)"""
        
        try:
            response = call_kanana(prompt, temperature=0, max_tokens=10)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except:
            return 0.5
    
    def _score_difficulty(self, paper: Dict, level: str) -> float:
        """난이도 적합성 점수 (LLM 평가)"""
        abstract = paper.get("abstract", "")[:500]
        
        level_map = {
            "beginner": "초보자",
            "intermediate": "중급자",
            "advanced": "고급자"
        }
        level_kr = level_map.get(level, "중급자")
        
        prompt = f"""다음 논문 초록을 보고 {level_kr} 수준의 사용자가 이해하기 적합한지 0-1 사이의 점수로 평가해주세요.

초록: {abstract}

적합성 점수만 숫자로 답해주세요 (예: 0.75)"""
        
        try:
            response = call_kanana(prompt, temperature=0, max_tokens=10)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except:
            return 0.5
    
    def select_papers(
        self,
        candidate_papers: List[Dict],
        interest: str,
        level: str,
        top_n: int = 3
    ) -> List[Dict]:
        """
        하이브리드 논문 선정 프로세스
        1단계: 휴리스틱으로 20편 → 10편 필터링
        2단계: LLM으로 10편 정밀 평가
        3단계: 상위 3편 선정
        """
        if not candidate_papers:
            return []
        
        # 1단계: 휴리스틱 점수로 빠른 필터링
        print(f"1단계: 휴리스틱 필터링 ({len(candidate_papers)}편)")
        for paper in candidate_papers:
            paper["heuristic_score"] = self.calculate_score_heuristic(paper, interest)
        
        # 상위 10편 선정
        top_10 = sorted(
            candidate_papers,
            key=lambda x: x["heuristic_score"],
            reverse=True
        )[:10]
        
        print(f"2단계: LLM 정밀 평가 ({len(top_10)}편)")
        # 2단계: LLM으로 정밀 평가
        for paper in top_10:
            paper["final_score"] = self.calculate_score_llm(paper, interest, level)
        
        # 3단계: 최종 상위 N편 선정
        selected = sorted(
            top_10,
            key=lambda x: x["final_score"],
            reverse=True
        )[:top_n]
        
        print(f"3단계: 최종 {len(selected)}편 선정 완료")
        return selected


class MCPPaperDescriptionAgent:
    """논문 설명 Agent (MCP 전용 - DB 없음, 초록 기반 요약)"""
    
    def __init__(self):
        self.level_prompts = {
            "beginner": """초보자 수준의 사용자를 위해 다음 내용을 포함하여 설명해주세요:
1. 핵심 개념과 용어를 쉽게 설명
2. 논문의 주요 목적과 기여를 간단명료하게
3. 기술적 세부사항보다는 전체적인 흐름과 의미 중심
4. 전문 용어가 나오면 괄호 안에 쉬운 설명 추가""",
            
            "intermediate": """중급자 수준의 사용자를 위해 다음 내용을 포함하여 설명해주세요:
1. 논문의 핵심 기여와 방법론 요약
2. 주요 기술적 개념과 접근 방식 설명
3. 연구의 의의와 기존 연구와의 차별점
4. 적절한 수준의 기술 용어 사용""",
            
            "advanced": """고급자 수준의 사용자를 위해 다음 내용을 포함하여 설명해주세요:
1. 논문의 핵심 기여를 압축적으로 정리
2. 방법론의 기술적 세부사항과 혁신점
3. 연구의 한계와 향후 방향성
4. 전문 용어와 기술적 표현 사용"""
        }
        
        self.level_labels = {
            "beginner": "초보자",
            "intermediate": "중급자",
            "advanced": "고급자",
        }
    
    def generate_summary(self, paper: Dict, level: str = "intermediate") -> str:
        """난이도별 맞춤 요약 생성"""
        title = paper.get("title", "")
        abstract = paper.get("abstract", "") or ""
        authors = paper.get("authors", [])
        if isinstance(authors, list):
            authors = ", ".join(authors)
        
        level_prompt = self.level_prompts.get(
            level,
            self.level_prompts["intermediate"],
        )
        level_label = self.level_labels.get(level, "중급자")
        
        prompt = f"""{level_prompt}

논문 제목: {title}
저자: {authors}
원문 초록:
{abstract}

위 논문에 대한 {level_label} 수준의 요약을 작성해주세요."""
        
        summary = call_kanana(prompt, temperature=0.2, max_tokens=1024)
        return summary
    
    def describe(self, paper: Dict, level: str = "intermediate") -> Dict:
        """논문 설명 생성 (최종 메서드)"""
        summary = self.generate_summary(paper, level)
        
        return {
            "arxiv_id": paper.get("arxiv_id", ""),
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "published_date": paper.get("published_date", ""),
            "pdf_url": paper.get("pdf_url", ""),
            "abstract": paper.get("abstract", ""),
            "summary": summary,
            "level": level,
            "citation_count": paper.get("citation_count", 0),
            "final_score": paper.get("final_score", 0)
        }