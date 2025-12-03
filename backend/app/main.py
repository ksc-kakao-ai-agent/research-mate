from fastapi import FastAPI
from app.routers import api_router  # 통합 라우터 import

app = FastAPI()

@app.get("/")
def root():
    return {"message": "AI Paper Backend Running!"}

app.include_router(api_router)