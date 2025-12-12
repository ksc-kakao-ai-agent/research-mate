from fastapi import APIRouter

from app.routers.auth_router import router as auth_router
from app.routers.recommendation_router import router as recommendation_router
from app.routers.paper_detail_router import router as paper_detail_router
from app.routers.chatbot_router import router as chatbot_router
from app.routers.advice_router import router as advice_router
from app.routers.user_router import router as user_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/api/v1")
api_router.include_router(recommendation_router, prefix="/api/v1")
api_router.include_router(paper_detail_router, prefix="/api/v1")
api_router.include_router(chatbot_router, prefix="/api/v1")
api_router.include_router(advice_router, prefix="/api/v1")
api_router.include_router(user_router, prefix="/api/v1")