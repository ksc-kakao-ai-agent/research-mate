"""
추천 API 테스트를 위한 더미 데이터 생성 스크립트
"""
from .database import SessionLocal
from .models import User, Paper, Recommendation, PaperMetadata, CitationGraph
from datetime import datetime, date, timedelta
import json
import bcrypt

def create_dummy_data():
    db = SessionLocal()
    
    try:
        # 1. 테스트용 사용자 생성 (없는 경우에만)
        test_user = db.query(User).filter(User.username == "testuser").first()
        if not test_user:
            hashed_password = bcrypt.hashpw("testpass123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            test_user = User(
                username="testuser",
                password=hashed_password,
                interest="RAG",
                level="intermediate"
            )
            db.add(test_user)
            db.flush()
            print(f"✅ 사용자 생성: user_id={test_user.user_id}, username={test_user.username}")
        else:
            print(f"✅ 기존 사용자 사용: user_id={test_user.user_id}, username={test_user.username}")
        
        # 2. 더미 논문 생성
        papers_data = [
            {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
                "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
                "published_date": "2018-10-11",
                "source": "arXiv",
                "external_id": "1810.04805",
                "pdf_url": "https://arxiv.org/pdf/1810.04805.pdf",
                "abstract": "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers."
            },
            {
                "title": "Dense Passage Retrieval for Open-Domain Question Answering",
                "authors": ["Kaitao Song", "Xu Tan", "Tao Qin", "Jianfeng Lu", "Tie-Yan Liu"],
                "published_date": "2020-10-01",
                "source": "arXiv",
                "external_id": "2004.04906",
                "pdf_url": "https://arxiv.org/pdf/2004.04906.pdf",
                "abstract": "Open-domain question answering relies on efficient passage retrieval to select candidate contexts."
            },
            {
                "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
                "authors": ["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus", "Fabio Petroni", "Vladimir Karpukhin"],
                "published_date": "2020-05-22",
                "source": "arXiv",
                "external_id": "2005.11401",
                "pdf_url": "https://arxiv.org/pdf/2005.11401.pdf",
                "abstract": "Large pre-trained language models have been shown to store factual knowledge in their parameters."
            },
            {
                "title": "Attention Is All You Need",
                "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones"],
                "published_date": "2017-06-12",
                "source": "arXiv",
                "external_id": "1706.03762",
                "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
                "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks."
            },
            {
                "title": "GPT-3: Language Models are Few-Shot Learners",
                "authors": ["Tom B. Brown", "Benjamin Mann", "Nick Ryder", "Melanie Subbiah", "Jared Kaplan"],
                "published_date": "2020-05-28",
                "source": "arXiv",
                "external_id": "2005.14165",
                "pdf_url": "https://arxiv.org/pdf/2005.14165.pdf",
                "abstract": "Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text."
            }
        ]
        
        created_papers = []
        today = date.today()
        
        for paper_data in papers_data:
            # 논문이 이미 있는지 확인 (title로)
            existing_paper = db.query(Paper).filter(Paper.title == paper_data["title"]).first()
            if existing_paper:
                created_papers.append(existing_paper)
                print(f"✅ 기존 논문 사용: paper_id={existing_paper.paper_id}, title={existing_paper.title[:50]}...")
                continue
            
            # authors를 JSON 문자열로 변환
            authors_json = json.dumps(paper_data["authors"])
            
            # external_id에 arXiv: 접두사 추가
            external_id = paper_data.get("external_id", "")
            if external_id and not external_id.startswith("arXiv:"):
                external_id = f"arXiv:{external_id}"
            
            paper = Paper(
                title=paper_data["title"],
                authors=authors_json,
                published_date=paper_data["published_date"],
                source=paper_data["source"],
                external_id=external_id,
                pdf_url=paper_data["pdf_url"],
                abstract=paper_data["abstract"]
            )
            db.add(paper)
            db.flush()
            created_papers.append(paper)
            print(f"✅ 논문 생성: paper_id={paper.paper_id}, title={paper.title[:50]}...")
        
        db.commit()
        
        # 3. 오늘 날짜의 추천 논문 생성 (3개 - relations API 테스트용)
        today_start = datetime.combine(today, datetime.min.time())
        
        # 기존 오늘 추천이 있는지 확인
        existing_today_recs = db.query(Recommendation).filter(
            Recommendation.user_id == test_user.user_id,
            Recommendation.recommended_at >= today_start,
            Recommendation.recommended_at < today_start + timedelta(days=1)
        ).all()
        
        recommended_papers = []
        if existing_today_recs:
            print(f"✅ 기존 오늘 추천 논문 {len(existing_today_recs)}개 발견")
            recommended_papers = [rec.paper for rec in existing_today_recs if rec.paper]
        else:
            # 오늘 추천 논문 3개 생성 (relations API 테스트용)
            for i, paper in enumerate(created_papers[:3]):
                rec_time = today_start + timedelta(hours=i*2)  # 시간 간격을 두고
                recommendation = Recommendation(
                    user_id=test_user.user_id,
                    paper_id=paper.paper_id,
                    recommended_at=rec_time,
                    is_user_requested=False
                )
                db.add(recommendation)
                recommended_papers.append(paper)
                print(f"✅ 오늘 추천 논문 생성: paper_id={paper.paper_id}, recommended_at={rec_time}")
            
            db.commit()
        
        # 4. 공통 인용 논문 생성 (Attention Is All You Need - relations API 테스트용)
        common_ref_paper = None
        if len(created_papers) >= 4:
            common_ref_paper = created_papers[3]  # Attention Is All You Need
        else:
            # 없으면 새로 생성
            common_ref_data = {
                "title": "Attention Is All You Need",
                "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones"],
                "published_date": "2017-06-12",
                "source": "arXiv",
                "external_id": "arXiv:1706.03762",
                "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
                "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks."
            }
            
            existing_common = db.query(Paper).filter(
                Paper.external_id == "arXiv:1706.03762"
            ).first()
            
            if existing_common:
                common_ref_paper = existing_common
                print(f"✅ 기존 공통 인용 논문 사용: paper_id={common_ref_paper.paper_id}")
            else:
                authors_json = json.dumps(common_ref_data["authors"])
                common_ref_paper = Paper(
                    title=common_ref_data["title"],
                    authors=authors_json,
                    published_date=common_ref_data["published_date"],
                    source=common_ref_data["source"],
                    external_id=common_ref_data["external_id"],
                    pdf_url=common_ref_data["pdf_url"],
                    abstract=common_ref_data["abstract"]
                )
                db.add(common_ref_paper)
                db.flush()
                print(f"✅ 공통 인용 논문 생성: paper_id={common_ref_paper.paper_id}")
                db.commit()
        
        # 5. 인용 관계 생성 (3개 추천 논문이 모두 공통 인용 논문을 인용)
        if common_ref_paper and len(recommended_papers) >= 3:
            for rec_paper in recommended_papers[:3]:
                # 기존 인용 관계 확인
                existing_citation = db.query(CitationGraph).filter(
                    CitationGraph.citing_paper_id == rec_paper.paper_id,
                    CitationGraph.cited_paper_id == common_ref_paper.paper_id
                ).first()
                
                if existing_citation:
                    print(f"✅ 기존 인용 관계 사용: {rec_paper.paper_id} -> {common_ref_paper.paper_id}")
                    continue
                
                # 인용 관계 생성 (첫 번째는 influential, 나머지는 일반)
                is_influential = 1 if rec_paper == recommended_papers[0] else 0
                citation = CitationGraph(
                    citing_paper_id=rec_paper.paper_id,
                    cited_paper_id=common_ref_paper.paper_id,
                    relation_type="cites",
                    is_influential=is_influential
                )
                db.add(citation)
                print(f"✅ 인용 관계 생성: paper_id={rec_paper.paper_id} -> {common_ref_paper.paper_id} (influential={is_influential})")
            
            db.commit()
        
        # 6. 일부 논문에 메타데이터 추가
        for i, paper in enumerate(created_papers[:2]):
            existing_metadata = db.query(PaperMetadata).filter(
                PaperMetadata.paper_id == paper.paper_id
            ).first()
            
            if existing_metadata:
                print(f"✅ 기존 메타데이터 사용: paper_id={paper.paper_id}")
                continue
            
            keywords_json = json.dumps(["RAG", "Retrieval", "Knowledge-Intensive NLP", "Language Models"])
            metadata = PaperMetadata(
                paper_id=paper.paper_id,
                summary_level="intermediate",
                summary_content="이 논문은 대규모 언어모델에 외부 지식 검색 기능을 결합한 Retrieval-Augmented Generation (RAG) 방법을 제안합니다.",
                keywords=keywords_json,
                citation_count=1523,
                citation_velocity=45.2,
                influential_citation_count=234
            )
            db.add(metadata)
            print(f"✅ 메타데이터 생성: paper_id={paper.paper_id}")
        
        db.commit()
        
        print("\n" + "="*60)
        print("✅ 더미 데이터 생성 완료!")
        print("="*60)
        print(f"\n📌 테스트 사용자 정보:")
        print(f"   user_id: {test_user.user_id}")
        print(f"   username: {test_user.username}")
        print(f"\n📌 생성된 논문 수: {len(created_papers)}개")
        if common_ref_paper:
            print(f"   공통 인용 논문: paper_id={common_ref_paper.paper_id}, title={common_ref_paper.title[:50]}...")
        print(f"\n📌 오늘 추천 논문: {len(recommended_papers)}개")
        for i, paper in enumerate(recommended_papers[:3], 1):
            print(f"   {i}. paper_id={paper.paper_id}, title={paper.title[:50]}...")
        print(f"\n📌 테스트할 API:")
        print(f"   1. GET /api/v1/{test_user.user_id}/recommendations/today")
        print(f"      → 오늘의 추천 논문 조회")
        print(f"   2. GET /api/v1/{test_user.user_id}/recommendations/today/relations")
        print(f"      → 오늘의 추천 논문 인용 관계 분석")
        if common_ref_paper:
            print(f"   3. POST /api/v1/{test_user.user_id}/recommendations/request-paper")
            print(f"      → 공통 참고문헌 추천 수락")
            print(f"      (body: {{'paper_id': {common_ref_paper.paper_id}, 'reason': 'common_reference'}})")
        print("\n")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 에러 발생: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n=== 추천 API 테스트용 더미 데이터 생성 시작 ===\n")
    create_dummy_data()
    print("\n=== 완료 ===\n")