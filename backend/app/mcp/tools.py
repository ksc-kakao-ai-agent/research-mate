"""
MCP 툴 정의
backend/mcp/tools.py
"""

from fastmcp import FastMCP
from typing import Literal
import json
from datetime import datetime

# MCP 전용 Agent import
from .mcp_agents import (
    MCPSearchAgent,
    MCPSelectionAgent,
    MCPPaperDescriptionAgent
)

# FastMCP 인스턴스 생성
mcp = FastMCP("paper-recommender")


@mcp.tool()
def recommend_papers(
    interest: str,
    level: Literal["beginner", "intermediate", "advanced"]
) -> str:
    """
    사용자의 관심 분야와 난이도에 맞는 최신 학술 논문 3편을 추천합니다.
    arXiv에서 논문을 검색하고, AI가 관련성과 난이도를 평가하여 최적의 논문을 선정합니다.
    각 논문에 대해 사용자 수준에 맞는 쉬운 설명을 제공합니다.
    
    Args:
        interest: 관심 연구 분야 키워드 (예: multi-agent, RAG, Computer Vision, NLP, Reinforcement Learning, LLM fine-tuning)
        level: 사용자의 논문 이해 수준
            - beginner: 초보자 (입문자용 기초 논문, 쉬운 설명)
            - intermediate: 중급자 (핵심 개념을 다루는 논문, 표준 설명)
            - advanced: 고급자 (최신 연구 및 심화 논문, 전문적 설명)
    
    Returns:
        추천 논문 3편의 정보와 각 논문에 대한 맞춤 설명을 JSON 형식으로 반환
        {
            "recommendations": [논문 목록],
            "total_count": 3,
            "interest": "검색한 관심 분야",
            "level": "선택한 난이도",
            "generated_at": "생성 시각"
        }
    """
    
    try:
        print(f"논문 추천 시작 - 관심 분야: {interest}, 난이도: {level}")
        
        # 1단계: 논문 검색
        search_agent = MCPSearchAgent()
        print("1단계: 논문 검색 중...")
        candidate_papers = search_agent.search(interest, max_results=20)
        
        if not candidate_papers:
            return json.dumps({
                "error": "검색 결과가 없습니다. 다른 키워드로 시도해주세요.",
                "interest": interest,
                "level": level
            }, ensure_ascii=False)
        
        print(f"검색 완료: {len(candidate_papers)}편")
        
        # 2단계: 논문 선정 (하이브리드 점수 계산)
        selection_agent = MCPSelectionAgent()
        print("2단계: 최적 논문 선정 중...")
        selected_papers = selection_agent.select_papers(
            candidate_papers,
            interest,
            level,
            top_n=3
        )
        
        if not selected_papers:
            return json.dumps({
                "error": "적합한 논문을 찾지 못했습니다. 다른 키워드로 시도해주세요.",
                "interest": interest,
                "level": level
            }, ensure_ascii=False)
        
        print(f"선정 완료: {len(selected_papers)}편")
        
        # 3단계: 난이도별 설명 생성
        description_agent = MCPPaperDescriptionAgent()
        print("3단계: 논문 설명 생성 중...")
        recommendations = []
        
        for idx, paper in enumerate(selected_papers, 1):
            print(f"  {idx}/{len(selected_papers)} 설명 생성 중...")
            described_paper = description_agent.describe(paper, level)
            recommendations.append(described_paper)
        
        print("모든 설명 생성 완료!")
        
        # 최종 결과
        result = {
            "recommendations": recommendations,
            "total_count": len(recommendations),
            "interest": interest,
            "level": level,
            "generated_at": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        # 에러 발생 시 에러 메시지 반환
        error_result = {
            "error": f"논문 추천 중 오류가 발생했습니다: {str(e)}",
            "interest": interest,
            "level": level,
            "generated_at": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)


# 추가 툴: 논문 재추천 (다른 논문을 원할 때)
@mcp.tool()
def get_more_papers(
    interest: str,
    level: Literal["beginner", "intermediate", "advanced"],
    exclude_arxiv_ids: str = ""
) -> str:
    """
    이미 추천받은 논문을 제외하고 새로운 논문을 추천합니다.
    
    Args:
        interest: 관심 연구 분야
        level: 난이도 수준
        exclude_arxiv_ids: 제외할 arXiv ID들 (쉼표로 구분, 예: "2005.11401,2004.04906")
    
    Returns:
        새로운 추천 논문 3편
    """
    try:
        # 제외할 ID 리스트 파싱
        excluded_ids = [id.strip() for id in exclude_arxiv_ids.split(",") if id.strip()]
        
        search_agent = MCPSearchAgent()
        candidate_papers = search_agent.search(interest, max_results=30)
        
        # 이미 추천받은 논문 제외
        filtered_papers = [
            p for p in candidate_papers
            if p.get("arxiv_id") not in excluded_ids
        ]
        
        if not filtered_papers:
            return json.dumps({
                "error": "추가 논문을 찾지 못했습니다.",
                "interest": interest,
                "level": level
            }, ensure_ascii=False)
        
        # 선정 및 설명 생성
        selection_agent = MCPSelectionAgent()
        selected_papers = selection_agent.select_papers(
            filtered_papers,
            interest,
            level,
            top_n=3
        )
        
        description_agent = MCPPaperDescriptionAgent()
        recommendations = [
            description_agent.describe(paper, level)
            for paper in selected_papers
        ]
        
        result = {
            "recommendations": recommendations,
            "total_count": len(recommendations),
            "interest": interest,
            "level": level,
            "excluded_count": len(excluded_ids),
            "generated_at": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "error": f"추가 논문 추천 중 오류가 발생했습니다: {str(e)}",
            "interest": interest,
            "level": level
        }
        return json.dumps(error_result, ensure_ascii=False)