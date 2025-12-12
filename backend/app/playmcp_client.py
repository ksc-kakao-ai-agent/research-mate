import httpx
from typing import Dict, Any
import os
from typing import Optional, List


class PlayMCPClient:
    def __init__(self):
        self.base_url = "https://playmcp.kakao.com/mcp"
        self.access_token = os.getenv("PLAYMCP_ACCESS_TOKEN")  # 환경변수에서 토큰 가져오기
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "accept": "application/json, text/event-stream"
        }
        self.session_id = None
        self.request_id = 0
    
    async def _make_request(self, method: str, params: Dict[str, Any]) -> Dict:
        """MCP 프로토콜 요청"""
        self.request_id += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        
        headers = self.headers.copy()
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            # 세션 ID 저장 (initialize 응답에서)
            if method == "initialize" and "Mcp-Session-Id" in response.headers:
                self.session_id = response.headers["Mcp-Session-Id"]
            
            return response.json()
    
    async def initialize(self) -> Dict:
        """MCP 서버 초기화"""
        params = {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "sampling": {},
                "elicitation": {},
                "roots": {"listChanged": True}
            },
            "clientInfo": {
                "name": "paper-recommendation-app",
                "version": "1.0.0"
            }
        }
        return await self._make_request("initialize", params)
    
    async def send_kakao_message(self, message: str) -> Dict:
        """카카오톡 나와의 채팅방에 메시지 전송"""
        # 세션이 없으면 초기화
        if not self.session_id:
            await self.initialize()
        
        params = {
            "name": "KakaotalkChat-MemoChat",
            "arguments": {
                "message": message
            }
        }
        return await self._make_request("tools/call", params)

    async def create_calendar_event(
        self,
        title: str,
        start_at: str,
        end_at: str,
        all_day: bool = False,
        description: Optional[str] = None,
        location_name: Optional[str] = None,
        location_address: Optional[str] = None,
        recurrence: Optional[str] = None,
        reminders: Optional[List[int]] = None,
        color: Optional[str] = None
    ) -> Dict:
        """
        톡캘린더에 일정 생성
        
        Args:
            title: 일정 제목 (최대 50자)
            start_at: 시작 시각 (YYYY-MM-DDThh:mm:ss 형식, 5분 단위)
            end_at: 종료 시각 (YYYY-MM-DDThh:mm:ss 형식, 5분 단위)
            all_day: 하루종일 여부
            description: 추가 설명 (최대 5000자)
            location_name: 장소 이름 (최대 100자)
            location_address: 도로명 주소
            recurrence: 반복 주기 (RFC 5545 형식)
            reminders: 알림 시간 목록 (분 단위, 최대 2개)
            color: 표시 색상 (BLUE, RED, GREEN 등)
        """
        if not self.session_id:
            await self.initialize()
        
        # 필수 파라미터 구성
        arguments = {
            "title": title,
            "time": {
                "startAt": start_at,
                "endAt": end_at,
                "allDay": all_day
            }
        }
        
        # 선택적 파라미터 추가
        if description:
            arguments["description"] = description
        
        if location_name:
            arguments["location"] = {"name": location_name}
            if location_address:
                arguments["location"]["address"] = location_address
        
        if recurrence:
            arguments["recurrence"] = recurrence
        
        if reminders:
            arguments["reminders"] = reminders
        
        if color:
            arguments["color"] = color
        
        params = {
            "name": "KakaotalkCal-CreateEvent",
            "arguments": arguments
        }
        
        return await self._make_request("tools/call", params)




# 싱글톤 인스턴스
playmcp_client = PlayMCPClient()