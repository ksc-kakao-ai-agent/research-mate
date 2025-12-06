from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import api_router  # 통합 라우터

app = FastAPI()

# CORS 반드시 먼저 설정
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "AI Paper Backend Running!"}

# 라우터 등록 (여기서 prefix="/api/v1"이면 여기에 맞춰야 함)
app.include_router(api_router)
