import arxiv
import pdfplumber
import requests
import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.utils.kanana import call_kanana
from app.models import Paper, PaperMetadata

class SelectionAgent:
    """논문 선정 Agent: 가중치 기반 평가, 최적 3편 선정, PDF 다운로드 및 텍스트 추출"""
    
    def __init__(self, db: Optional[Session] = None):
        self.temp_dir = "/tmp/arxiv_papers"
        os.makedirs(self.temp_dir, exist_ok=True)
        self.db = db
    
    def calculate_score(self, paper: Dict, interest: str, level: str) -> float:
        """가중치 기반 종합 점수 계산"""
        scores = {
            "recentness": self._score_recentness(paper),
            "citation": self._score_citation(paper),
            "keyword_match": self._score_keyword_match(paper, interest),
            "difficulty": self._score_difficulty(paper, level)
        }
        
        # 가중치
        weights = {
            "recentness": 0.2,
            "citation": 0.3,
            "keyword_match": 0.3,
            "difficulty": 0.2
        }
        
        total_score = sum(scores[k] * weights[k] for k in scores)
        return total_score
    
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
        
        # 정규화 (최대값 기준)
        citation_score = min(citation_count / 100, 1.0) if citation_count > 0 else 0
        velocity_score = min(citation_velocity / 10, 1.0) if citation_velocity > 0 else 0
        
        return (citation_score * 0.7 + velocity_score * 0.3)
    
    def _score_keyword_match(self, paper: Dict, interest: str) -> float:
        """키워드 일치도 점수 (LLM 평가)"""
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")[:500]  # 처음 500자만
        
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
    
    def download_pdf(self, arxiv_id: str) -> str:
        """arXiv에서 PDF 다운로드"""
        try:
            paper = next(arxiv.Search(id_list=[arxiv_id]).results())
            paper.download_pdf(dirpath=self.temp_dir, filename=f"{arxiv_id}.pdf")
            return os.path.join(self.temp_dir, f"{arxiv_id}.pdf")
        except Exception as e:
            print(f"PDF 다운로드 오류 (arXiv:{arxiv_id}): {e}")
            return None
    
    def extract_text(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        if not pdf_path or not os.path.exists(pdf_path):
            return ""
        
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            print(f"텍스트 추출 오류: {e}")
            return ""
    
    def _save_paper_to_db(self, paper_data: Dict) -> Optional[int]:
        """논문을 DB에 저장하고 paper_id 반환"""
        if not self.db:
            return None
        
        arxiv_id = paper_data.get("arxiv_id", "")
        if not arxiv_id:
            return None
        
        # 이미 존재하는 논문인지 확인
        existing = self.db.query(Paper).filter(
            Paper.external_id == f"arXiv:{arxiv_id}"
        ).first()
        
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
                external_id=f"arXiv:{arxiv_id}",
                pdf_url=paper_data.get("pdf_url"),
                abstract=paper_data.get("abstract", "")
            )
            self.db.add(new_paper)
            self.db.flush()
            paper_id = new_paper.paper_id
        
        # PaperMetadata 저장/업데이트
        metadata = self.db.query(PaperMetadata).filter(
            PaperMetadata.paper_id == paper_id
        ).first()
        
        if not metadata:
            metadata = PaperMetadata(paper_id=paper_id)
            self.db.add(metadata)
        
        # PDF 텍스트 저장
        if paper_data.get("full_text"):
            metadata.full_text = paper_data["full_text"]
        
        # Semantic Scholar 메트릭 저장
        metadata.citation_count = paper_data.get("citation_count", 0)
        metadata.citation_velocity = paper_data.get("citation_velocity", 0)
        metadata.influential_citation_count = paper_data.get("influential_citation_count", 0)
        
        # 키워드 저장 (categories를 JSON으로)
        if paper_data.get("categories"):
            metadata.keywords = json.dumps(paper_data["categories"])
        
        try:
            self.db.commit()
            return paper_id
        except Exception as e:
            self.db.rollback()
            print(f"DB 저장 오류: {e}")
            return None
    
    def select_papers(self, candidate_papers: List[Dict], interest: str, level: str, top_n: int = 3) -> List[Dict]:
        """최적 논문 3편 선정 및 PDF 처리, DB 저장"""
        # 점수 계산 및 정렬
        scored_papers = []
        for paper in candidate_papers:
            # DB에 이미 존재하는 논문은 건너뛰기 (중복 체크)
            if self.db and paper.get("exists_in_db"):
                continue
            score = self.calculate_score(paper, interest, level)
            paper["selection_score"] = score
            scored_papers.append(paper)
        
        # 상위 N개 선정
        selected = sorted(scored_papers, key=lambda x: x["selection_score"], reverse=True)[:top_n]
        
        # PDF 다운로드 및 텍스트 추출, DB 저장
        saved_paper_ids = []
        for paper in selected:
            arxiv_id = paper.get("arxiv_id")
            if arxiv_id:
                pdf_path = self.download_pdf(arxiv_id)
                if pdf_path:
                    full_text = self.extract_text(pdf_path)
                    paper["full_text"] = full_text
                    # 임시 파일 삭제
                    try:
                        os.remove(pdf_path)
                    except:
                        pass
            
            # DB에 저장
            paper_id = self._save_paper_to_db(paper)
            if paper_id:
                paper["db_paper_id"] = paper_id
                saved_paper_ids.append(paper_id)
        
        return selected

