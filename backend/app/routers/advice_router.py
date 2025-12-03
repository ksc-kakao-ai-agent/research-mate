from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal
from app.database import get_db
from app.models import User
from app.agents.advice_agent import advice_agent

router = APIRouter(
    tags=["advice"]
)

# ------------------------------------
# Request/Response Models
# ------------------------------------

class InterestChangeAdvice(BaseModel):
    advice_type: Literal["interest_change"]
    current_interest: str
    suggested_interest: str
    reason: str


class LevelChangeAdvice(BaseModel):
    advice_type: Literal["level_change"]
    current_level: str
    suggested_level: str
    reason: str
    comprehension_score: int


class NoAdvice(BaseModel):
    advice_type: Literal["none"]
    message: str


class AcceptInterestRequest(BaseModel):
    new_interest: str


class AcceptInterestResponse(BaseModel):
    user_id: int
    updated_interest: str
    message: str


class AcceptLevelRequest(BaseModel):
    new_level: str


class AcceptLevelResponse(BaseModel):
    user_id: int
    updated_level: str
    message: str


# ------------------------------------
# API Endpoints
# ------------------------------------

@router.get("/{user_id}/advice")
async def get_advice(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    사용자의 최근 활동 패턴을 분석하여 관심 분야 또는 난이도 변경을 제안합니다.
    
    Returns:
        - interest_change: 관심 분야 변경 제안
        - level_change: 난이도 변경 제안
        - none: 조언 없음
    """
    # 사용자 존재 여부 확인
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    # AdviceAgent를 통해 조언 생성
    advice_result = await advice_agent.analyze_and_suggest(db, user_id)
    
    return advice_result


@router.post("/{user_id}/advice/accept-interest", response_model=AcceptInterestResponse)
async def accept_interest_change(
    user_id: int,
    request: AcceptInterestRequest,
    db: Session = Depends(get_db)
):
    """
    AI가 제안한 관심 분야 변경을 수락하고 사용자 정보를 업데이트합니다.
    """
    # 사용자 조회
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 빈 문자열 검증 추가
    if not request.new_interest or not request.new_interest.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="관심 분야는 비어있을 수 없습니다."
        )

    # 관심 분야 업데이트
    user.interest = request.new_interest
    db.commit()
    db.refresh(user)

    return AcceptInterestResponse(
        user_id=user.user_id,
        updated_interest=user.interest,
        message="관심 분야가 성공적으로 변경되었습니다."
    )


@router.post("/{user_id}/advice/accept-level", response_model=AcceptLevelResponse)
async def accept_level_change(
    user_id: int,
    request: AcceptLevelRequest,
    db: Session = Depends(get_db)
):
    """
    AI가 제안한 난이도 변경을 수락하고 사용자 정보를 업데이트합니다.
    """
    # 사용자 조회
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    # 난이도 검증 강화
    valid_levels = ["beginner", "intermediate", "advanced"]
    if not request.new_level or request.new_level not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 난이도입니다. 가능한 값: {', '.join(valid_levels)}"
        )

    # 난이도 업데이트
    user.level = request.new_level
    db.commit()
    db.refresh(user)

    return AcceptLevelResponse(
        user_id=user.user_id,
        updated_level=user.level,
        message="난이도가 성공적으로 변경되었습니다."
    )