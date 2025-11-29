from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경변수에서 DATABASE_URL 가져오기
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:yourpassword@localhost:5432/ai_paper_db"
)

# DATABASE_URL 검증
if "yourpassword" in DATABASE_URL or "yourdbname" in DATABASE_URL:
    print("⚠️  경고: DATABASE_URL에 기본값이 사용되고 있습니다.")
    print("📝 .env 파일에 실제 DATABASE_URL을 설정해주세요.")
    print("예시: DATABASE_URL=postgresql://postgres:실제비밀번호@localhost:5432/ai_paper_db")

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL, echo=True)  # echo=True → SQL 로그 출력

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 (모든 모델이 상속)
Base = declarative_base()


# DB 세션 의존성 (FastAPI에서 사용)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
