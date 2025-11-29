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
        # 프롬프트에 넣을 한글 레벨 라벨
        self.level_labels = {
            "beginner": "초보자",
            "intermediate": "중급자",
            "advanced": "고급자",
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
            authors = ", ".join(authors)
        
        # full_text가 있으면 더 풍부한 내용 기반으로 요약
        full_text = paper.get("full_text", "") or ""
        content = full_text[:2000] if full_text else abstract  # 처음 2000자만 사용
        
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

{f'논문 전문 (일부):\n{content}' if full_text else ''}

위 논문에 대한 {level_label} 수준의 요약을 작성해주세요."""
        
        summary = call_kanana(prompt, temperature=0.2, max_tokens=1024)
        return summary
    
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