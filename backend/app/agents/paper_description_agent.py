from typing import Dict, Optional
import json
from sqlalchemy.orm import Session
from app.utils.kanana import call_kanana
from app.models import Paper, PaperMetadata


class PaperDescriptionAgent:
    """논문 설명 Agent: 사용자 난이도에 맞춘 초록 요약 생성"""
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        # 난이도별 요약 스타일 프롬프트
        self.level_prompts = {
            "beginner": """다음 논문을 초보자가 이해할 수 있도록 200-300자 이내로 요약해주세요.

요구사항:
- 논문이 해결하려는 문제를 한 문장으로 설명
- 제안하는 방법이나 아이디어를 쉽게 설명
- 왜 중요한지 간단히 설명
- 전문 용어는 괄호 안에 쉬운 설명 추가
- 마크다운 강조 표시(**, ##, ---)를 사용하지 말 것
- 자연스러운 문장으로 작성""",
            
            "intermediate": """다음 논문을 중급자가 이해할 수 있도록 300-400자 이내로 요약해주세요.

요구사항:
- 논문의 핵심 기여 2-3가지
- 주요 방법론이나 접근 방식
- 기존 연구와의 차별점
- 마크다운 강조 표시(**, ##, ---)를 사용하지 말 것
- 자연스러운 문장으로 작성""",
            
            "advanced": """다음 논문을 고급자가 이해할 수 있도록 300-400자 이내로 요약해주세요.

요구사항:
- 핵심 기술적 기여를 압축적으로 정리
- 방법론의 기술적 세부사항과 혁신점
- 연구의 한계나 향후 방향성
- 마크다운 강조 표시(**, ##, ---)를 사용하지 말 것
- 자연스러운 문장으로 작성"""
        }
    
    def _get_paper_from_db(self, paper_id: int) -> Optional[Dict]:
        """DB에서 논문 정보 + 메타데이터(full_text) 가져오기"""
        if not self.db:
            return None
        
        paper = (
            self.db.query(Paper)
            .filter(Paper.paper_id == paper_id)
            .first()
        )
        if not paper:
            return None
        
        metadata = (
            self.db.query(PaperMetadata)
            .filter(PaperMetadata.paper_id == paper_id)
            .first()
        )
        
        return {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "authors": json.loads(paper.authors) if paper.authors else [],
            "abstract": paper.abstract,
            "full_text": metadata.full_text if metadata else None,
        }
    
    def generate_summary(self, paper: Dict, level: str = "intermediate") -> str:
        """난이도별 맞춤 요약 생성 (단일 LLM 호출)"""
        title = paper.get("title", "")
        abstract = paper.get("abstract", "") or ""
        authors = paper.get("authors", [])
        if isinstance(authors, list):
            authors = ", ".join(authors[:3])
            if len(paper.get("authors", [])) > 3:
                authors += " 외"
        
        # full_text가 있으면 더 풍부한 내용 기반으로 요약
        full_text = paper.get("full_text", "") or ""
        content = full_text[:2000] if full_text else abstract[:1000]
        
        level_prompt = self.level_prompts.get(
            level,
            self.level_prompts["intermediate"],
        )
        
        prompt = f"""{level_prompt}

논문 제목: {title}
저자: {authors}
초록:
{content}

위 내용을 바탕으로 요약을 작성해주세요."""
        
        summary = call_kanana(prompt, temperature=0.2, max_tokens=512)
        return summary.strip()
    
    def validate_quality(self, summary: str, abstract: str) -> bool:
        """요약 품질 검증 (간단한 휴리스틱)"""
        if not summary:
            return False
        
        # 1) 너무 짧으면 의미 있는 요약이 아닐 가능성 높음
        if len(summary.strip()) < 100:
            return False
        
        # 2) 원문 초록을 거의 그대로 복붙한 경우 막기
        head_abstract = (abstract or "")[:200].strip()
        head_summary = summary[:200].strip()
        
        # 앞부분 200자가 완전히 동일하거나,
        # 초록 앞 150자가 요약 안에 그대로 포함되어 있으면 실패
        if head_abstract and (
            head_summary == head_abstract
            or head_abstract[:150] in summary
        ):
            return False
        
        return True
    
    def generate_with_validation(
        self,
        paper: Dict,
        level: str = "intermediate",
        max_retries: int = 2,
    ) -> str:
        """품질 검증 후 필요시 재생성"""
        abstract = paper.get("abstract", "") or ""
        summary = ""
        
        for attempt in range(max_retries):
            summary = self.generate_summary(paper, level)
            
            if self.validate_quality(summary, abstract):
                return summary
            
            if attempt < max_retries - 1:
                print(f"요약 품질 검증 실패, 재생성 시도 {attempt + 2}/{max_retries}")
        
        # 최종 시도 실패 시 마지막 생성 결과 또는 기본 메시지 반환
        return summary if summary else "요약 생성에 실패했습니다."
    
    def _save_summary_to_db(self, paper_id: int, summary: str, level: str):
        """요약을 PaperMetadata에 저장"""
        if not self.db:
            return
        
        try:
            metadata = (
                self.db.query(PaperMetadata)
                .filter(PaperMetadata.paper_id == paper_id)
                .first()
            )
            
            if not metadata:
                metadata = PaperMetadata(paper_id=paper_id)
                self.db.add(metadata)
            
            metadata.summary_level = level
            metadata.summary_content = summary
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"요약 저장 오류: {e}")
    
    def describe(self, paper: Dict, level: str = "intermediate") -> Dict:
        """
        논문 설명 생성 (최종 메서드)
        - paper dict에 paper_id / db_paper_id가 있으면 DB에서 full_text를 보강
        - 요약 생성 + 품질 검증
        - 메타데이터에 요약 저장
        """
        paper_id = paper.get("db_paper_id") or paper.get("paper_id")
        
        # DB에 저장된 full_text/abstract로 보강
        if paper_id and self.db:
            db_paper = self._get_paper_from_db(paper_id)
            if db_paper:
                # 외부에서 넘겨준 paper 정보 위에 DB 정보를 덮어씀
                paper.update(db_paper)
        
        summary = self.generate_with_validation(paper, level)
        
        # DB에 요약 저장
        if paper_id and self.db:
            self._save_summary_to_db(paper_id, summary, level)
        
        return {
            "paper_id": paper_id or paper.get("arxiv_id", ""),
            "title": paper.get("title", ""),
            "original_abstract": paper.get("abstract", ""),
            "summary": summary,
            "level": level,
        }