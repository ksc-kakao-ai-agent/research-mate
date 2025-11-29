from sqlalchemy import text
from app.database import engine # engine 객체가 DB 연결 정보를 가지고 있다고 가정

def add_user_request_columns():
    """recommendations 테이블에 사용자 요청 관련 컬럼 추가"""
    
    with engine.connect() as conn:
        # 트랜잭션 시작
        trans = conn.begin()
        
        try:
            # 1. is_user_requested 컬럼 추가 (기본값 FALSE, NOT NULL)
            conn.execute(text("""
                ALTER TABLE recommendations 
                ADD COLUMN IF NOT EXISTS is_user_requested BOOLEAN DEFAULT FALSE NOT NULL
            """))
            
            # 2. requested_paper_id 컬럼 추가 (NULL 허용)
            # NOT NULL을 나중에 추가할 수 있도록 일단 INTEGER로만 추가합니다.
            conn.execute(text("""
                ALTER TABLE recommendations 
                ADD COLUMN IF NOT EXISTS requested_paper_id INTEGER
            """))
            
            # 3. Foreign Key 제약조건 추가
            conn.execute(text("""
                ALTER TABLE recommendations 
                ADD CONSTRAINT fk_requested_paper 
                FOREIGN KEY (requested_paper_id) 
                REFERENCES papers(paper_id) 
                ON DELETE SET NULL
            """))
            
            trans.commit()
            print("✅ 마이그레이션 성공: recommendations 테이블에 컬럼 추가 완료")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ 마이그레이션 실패: {e}")
            raise

if __name__ == "__main__":
    print("\n=== recommendations 테이블 마이그레이션 시작 ===\n")
    # 'app.database.py'가 실행되어야 engine 객체를 사용할 수 있으므로, 
    # 실행 환경에 따라 engine을 import 하는 데 필요한 준비가 되어 있어야 합니다.
    add_user_request_columns()
    print("\n=== 마이그레이션 완료 ===\n")