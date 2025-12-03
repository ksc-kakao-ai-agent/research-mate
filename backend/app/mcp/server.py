"""
MCP 서버 (FastAPI 통합)
backend/app/mcp/server.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .tools import mcp

# FastAPI 앱 생성
app = FastAPI(
    title="Paper Recommender MCP Server",
    description="학술 논문 추천 MCP 서버",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 헬스 체크
@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "Paper Recommender MCP Server",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# ===== 로컬 테스트용 엔드포인트 (선택사항) =====
class RecommendRequest(BaseModel):
    interest: str
    level: str = "intermediate"

@app.post("/test/recommend")
async def test_recommend(request: RecommendRequest):
    """논문 추천 테스트 (로컬 디버깅용)"""
    from .mcp_agents import MCPSearchAgent, MCPSelectionAgent, MCPPaperDescriptionAgent
    
    try:
        search_agent = MCPSearchAgent()
        papers = search_agent.search(request.interest, max_results=20)
        
        selection_agent = MCPSelectionAgent()
        selected = selection_agent.select_papers(
            papers, 
            request.interest, 
            request.level, 
            top_n=3
        )
        
        description_agent = MCPPaperDescriptionAgent()
        results = [description_agent.describe(p, request.level) for p in selected]
        
        return {
            "success": True,
            "total_found": len(papers),
            "recommendations": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ===== MCP SSE 엔드포인트 추가 =====
# FastMCP를 SSE transport로 FastAPI에 연결
#mcp_sse = mcp.sse()  # SSE 핸들러 생성
#app.add_api_route("/sse", mcp_sse, methods=["GET", "POST"])