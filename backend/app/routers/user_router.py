from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/users", tags=["users"])

# ✅ 관심 분야를 리스트가 아니라 단일 문자열로 받도록 변경
class UpdateProfileRequest(BaseModel):
    interest: str
    level: str

@router.put("/{user_id}")
def update_user_profile(
    user_id: int,
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db)
):
    # 1. 유저 조회
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. DB 업데이트
    user.interest = payload.interest
    user.level = payload.level

    db.commit()
    db.refresh(user)

    return {
        "message": "Profile updated successfully",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "interest": user.interest,
            "level": user.level
        }
    }
