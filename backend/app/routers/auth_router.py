from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
import bcrypt
from typing import Literal

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ==================== Request/Response 모델 ====================

class RegisterRequest(BaseModel):
    username: str = Field(..., description="사용자 ID")
    password: str = Field(..., description="비밀번호")
    interest: str = Field(..., description="관심분야")
    level: Literal["beginner", "intermediate", "advanced"] = Field(..., description="단계 (beginner / intermediate / advanced)")


class RegisterResponse(BaseModel):
    user_id: int
    username: str
    interest: str
    level: str
    created_at: datetime


class LoginRequest(BaseModel):
    username: str = Field(..., description="사용자 ID")
    password: str = Field(..., description="비밀번호")


class LoginResponse(BaseModel):
    user_id: int
    username: str
    interest: str
    level: str

# ==================== 유틸리티 함수 ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


# ==================== API 엔드포인트 ====================

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    회원가입 API
    """
    # 중복 사용자명 확인
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 사용자명입니다."
        )
    
    # 새 사용자 생성
    hashed_password = get_password_hash(request.password)
    new_user = User(
        username=request.username,
        password=hashed_password,
        interest=request.interest,
        level=request.level
    )
    
    db.add(new_user)
    db.flush()  # DB에 flush하여 user_id를 받아옴
    db.commit()
    db.refresh(new_user)  # 최신 데이터로 새로고침
    
    return RegisterResponse(
        user_id=new_user.user_id,
        username=new_user.username,
        interest=new_user.interest,
        level=new_user.level,
        created_at=new_user.created_at
    )


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    로그인 API
    """
    # 사용자 조회
    user = db.query(User).filter(User.username == request.username).first()
    
    # 사용자가 없거나 비밀번호가 일치하지 않는 경우
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.example.com/errors/invalid-credentials",
                "title": "Invalid Credentials",
                "status": 400,
                "detail": "아이디 또는 비밀번호가 일치하지 않습니다."
            }
        )
    
    return LoginResponse(
        user_id=user.user_id,
        username=user.username,
        interest=user.interest,
        level=user.level
    )