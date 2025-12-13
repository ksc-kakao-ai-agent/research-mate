"""
논문 추천 파이프라인
SearchAgent -> SelectionAgent -> PaperDescriptionAgent -> DB 저장
"""

import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.agents.search_agent import SearchAgent
from app.agents.selection_agent import SelectionAgent
from app.agents.paper_description_agent import PaperDescriptionAgent
from app.models import User, Recommendation
from datetime import datetime


class PaperRecommendationPipeline:
    """논문 추천 전체 파이프라인"""
    
    def __init__(self, db: Session):
        self.db = db
        self.search_agent = SearchAgent(db=db)
        self.selection_agent = SelectionAgent(db=db)
        self.description_agent = PaperDescriptionAgent(db=db)
    
    def run(self, user_id: int, top_n: int = 3) -> dict:
        """
        전체 파이프라인 실행
        
        Args:
            user_id: 사용자 ID
            top_n: 선정할 논문 수 (기본 3편)
        
        Returns:
            dict: 실행 결과 요약
        """
        print(f"\n{'='*60}")
        print(f"📚 논문 추천 파이프라인 시작 (user_id={user_id})")
        print(f"{'='*60}\n")
        
        # 1. 사용자 정보 가져오기
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            print(f"❌ 사용자를 찾을 수 없습니다: user_id={user_id}")
            return {"success": False, "error": "User not found"}
        
        interest = user.interest
        level = user.level or "intermediate"
        
        print(f"👤 사용자: {user.username}")
        print(f"🎯 관심 분야: {interest}")
        print(f"📊 난이도: {level}")
        print()
        
        # 2. SearchAgent: 논문 검색
        print(f"🔍 Step 1: 논문 검색 중...")
        try:
            candidate_papers = self.search_agent.search(
                user_id=user_id,
                max_results=20
            )
            print(f"✅ 검색 완료: {len(candidate_papers)}편의 후보 논문 발견")
        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return {"success": False, "error": str(e)}
        
        if not candidate_papers:
            print("❌ 검색된 논문이 없습니다.")
            return {"success": False, "error": "No papers found"}
        
        print()
        
        # 3. SelectionAgent: 최적 논문 선정 및 PDF 다운로드
        print(f"📝 Step 2: 상위 {top_n}편 선정 및 PDF 다운로드 중...")
        try:
            selected_papers = self.selection_agent.select_papers(
                candidate_papers=candidate_papers,
                interest=interest,
                level=level,
                top_n=top_n
            )
            print(f"✅ 선정 완료: {len(selected_papers)}편")
        except Exception as e:
            print(f"❌ 선정 실패: {e}")
            return {"success": False, "error": str(e)}
        
        if not selected_papers:
            print("❌ 선정된 논문이 없습니다.")
            return {"success": False, "error": "No papers selected"}
        
        print()
        
        # 4. PaperDescriptionAgent: 난이도별 요약 생성
        print(f"✍️  Step 3: 난이도별 요약 생성 중 (level={level})...")
        summaries = []
        for i, paper in enumerate(selected_papers, 1):
            print(f"  [{i}/{len(selected_papers)}] {paper.get('title', 'Unknown')[:50]}...")
            try:
                result = self.description_agent.describe(paper, level=level)
                summaries.append(result)
            except Exception as e:
                print(f"    ⚠️  요약 생성 실패: {e}")
                continue
        
        print(f"✅ 요약 완료: {len(summaries)}편")
        print()
        
        # 5. Recommendation 테이블에 기록
        print(f"💾 Step 4: Recommendation 테이블에 저장 중...")
        saved_count = 0
        for paper in selected_papers:
            paper_id = paper.get("db_paper_id")
            if not paper_id:
                print(f"  ⚠️  paper_id 없음: {paper.get('title', 'Unknown')[:50]}")
                continue
            
            try:
                recommendation = Recommendation(
                    user_id=user_id,
                    paper_id=paper_id,
                    recommended_at=datetime.utcnow(),
                    is_user_requested=False
                )
                self.db.add(recommendation)
                saved_count += 1
            except Exception as e:
                print(f"  ⚠️  Recommendation 저장 실패: {e}")
                continue
        
        try:
            self.db.commit()
            print(f"✅ Recommendation 저장 완료: {saved_count}건")
        except Exception as e:
            self.db.rollback()
            print(f"❌ Recommendation 커밋 실패: {e}")
            return {"success": False, "error": str(e)}
        
        print()
        print(f"{'='*60}")
        print(f"🎉 파이프라인 완료!")
        print(f"{'='*60}\n")
        
        # 결과 요약
        result = {
            "success": True,
            "user_id": user_id,
            "username": user.username,
            "interest": interest,
            "level": level,
            "candidate_count": len(candidate_papers),
            "selected_count": len(selected_papers),
            "summary_count": len(summaries),
            "saved_count": saved_count,
            "papers": [
                {
                    "paper_id": p.get("db_paper_id"),
                    "title": p.get("title"),
                    "arxiv_id": p.get("arxiv_id"),
                    "selection_score": p.get("selection_score"),
                }
                for p in selected_papers
            ]
        }
        
        return result


def main():
    """메인 실행 함수 (더미 데이터 생성용)"""
    # DB 세션 생성
    db = SessionLocal()
    
    try:
        # 파이프라인 생성
        pipeline = PaperRecommendationPipeline(db=db)
        
        # testuser (user_id=3) 대상 실행
        result = pipeline.run(user_id=3, top_n=3)
        
        # 결과 출력
        if result["success"]:
            print("\n📊 최종 결과:")
            print(f"  - 사용자: {result['username']} (ID: {result['user_id']})")
            print(f"  - 관심 분야: {result['interest']}")
            print(f"  - 난이도: {result['level']}")
            print(f"  - 검색된 후보: {result['candidate_count']}편")
            print(f"  - 선정된 논문: {result['selected_count']}편")
            print(f"  - 생성된 요약: {result['summary_count']}편")
            print(f"  - DB 저장: {result['saved_count']}건")
            print("\n선정된 논문:")
            for i, paper in enumerate(result["papers"], 1):
                print(f"  {i}. [{paper['arxiv_id']}] {paper['title']}")
                print(f"     점수: {paper['selection_score']:.3f}")
        else:
            print(f"\n❌ 파이프라인 실패: {result.get('error')}")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()