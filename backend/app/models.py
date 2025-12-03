from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


# --------------------------
# User
# --------------------------
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    interest = Column(Text, nullable=True)        # 관심 분야
    level = Column(String(50), nullable=True)     # 난이도 (beginner/intermediate/advanced)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relations
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    read_papers = relationship("UserReadPaper", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")


# --------------------------
# Paper (기본 논문 정보)
# --------------------------
class Paper(Base):
    __tablename__ = "papers"

    paper_id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=True)         # JSON 형태로 저장 가능
    published_date = Column(String(50), nullable=True)
    source = Column(String(50), nullable=True)    # arXiv / Semantic Scholar 등
    external_id = Column(String(200), nullable=True)  # arXiv ID, DOI 등
    pdf_url = Column(Text, nullable=True)
    abstract = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relations
    paper_metadata = relationship("PaperMetadata", back_populates="paper", uselist=False, cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="paper", cascade="all, delete-orphan", foreign_keys="[Recommendation.paper_id]")
    #위에 foreign_keys="[Recommendation.paper_id]" 추가
    read_by_users = relationship("UserReadPaper", back_populates="paper", cascade="all, delete-orphan")
    chats = relationship("ChatHistory", back_populates="paper", cascade="all, delete-orphan")

    outgoing_citations = relationship(
        "CitationGraph",
        foreign_keys="CitationGraph.citing_paper_id",
        back_populates="citing_paper",
        cascade="all, delete-orphan"
    )
    incoming_citations = relationship(
        "CitationGraph",
        foreign_keys="CitationGraph.cited_paper_id",
        back_populates="cited_paper",
        cascade="all, delete-orphan"
    )


# --------------------------
# PaperMetadata (논문 메타데이터 - 별도 테이블)
# --------------------------
class PaperMetadata(Base):
    __tablename__ = "paper_metadata"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.paper_id", ondelete="CASCADE"), unique=True)
    
    # PDF 텍스트 및 요약
    full_text = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)         # JSON 배열로 저장
    
    # 사용자가 선택한 난이도에 따라 하나만 저장
    summary_level = Column(String(50), nullable=True)      # beginner/intermediate/advanced
    summary_content = Column(Text, nullable=True)          # 해당 난이도의 요약 내용
    
    # Semantic Scholar 메트릭
    citation_count = Column(Integer, default=0, nullable=True)
    citation_velocity = Column(Float, nullable=True)       # 최근 인용 증가율
    influential_citation_count = Column(Integer, default=0, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relation
    paper = relationship("Paper", back_populates="paper_metadata")
    #metadata->paper_metadata로 수정


# --------------------------
# Recommendation (오늘의 추천 논문 기록)
# --------------------------
class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    paper_id = Column(Integer, ForeignKey("papers.paper_id", ondelete="CASCADE"))
    recommended_at = Column(DateTime, default=datetime.utcnow)

    is_user_requested = Column(Boolean, default=False, nullable=False)
    requested_paper_id = Column(Integer, ForeignKey("papers.paper_id", ondelete="SET NULL"), nullable=True)

    user = relationship("User", back_populates="recommendations")
    paper = relationship("Paper", back_populates="recommendations", foreign_keys=[paper_id])
    #위에 foreign_keys=[paper_id] 추가


# --------------------------
# UserReadPaper (사용자가 읽은 논문 로그)
# --------------------------
class UserReadPaper(Base):
    __tablename__ = "user_read_papers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    paper_id = Column(Integer, ForeignKey("papers.paper_id", ondelete="CASCADE"))
    read_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="read_papers")
    paper = relationship("Paper", back_populates="read_by_users")


# --------------------------
# ChatHistory (논문별 Q&A 기록 - 별도 테이블)
# --------------------------
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    paper_id = Column(Integer, ForeignKey("papers.paper_id", ondelete="CASCADE"))
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chats")
    paper = relationship("Paper", back_populates="chats")


# --------------------------
# CitationGraph (논문 인용 관계)
# --------------------------
class CitationGraph(Base):
    __tablename__ = "citation_graph"

    id = Column(Integer, primary_key=True, index=True)
    citing_paper_id = Column(Integer, ForeignKey("papers.paper_id", ondelete="CASCADE"))
    cited_paper_id = Column(Integer, ForeignKey("papers.paper_id", ondelete="CASCADE"))
    
    # 인용 관계 정보
    relation_type = Column(String(50), nullable=True)  # "reference", "citation" 등
    is_influential = Column(Integer, default=0)        # Semantic Scholar의 influential citation 여부
    created_at = Column(DateTime, default=datetime.utcnow)

    citing_paper = relationship(
        "Paper",
        foreign_keys=[citing_paper_id],
        back_populates="outgoing_citations"
    )
    cited_paper = relationship(
        "Paper",
        foreign_keys=[cited_paper_id],
        back_populates="incoming_citations"
    )
