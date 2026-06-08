import httpx
from typing import Dict, Any, List, Optional


class SmartMyOdooClient:
    """Thin HTTP client — jedyny interfejs CLI do backendu."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None
        self._client = httpx.Client(base_url=self.base_url, timeout=60.0)

    @property
    def headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def login(self, password: str) -> Dict[str, Any]:
        """POST /api/auth → {success: bool, role: str}"""
        resp = self._client.post(
            "/api/auth",
            json={"password": password},
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code == 401:
            return {"success": False, "role": None}
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            self._token = password
        return data

    def chat(
        self,
        message: str,
        workspace_id: str,
        session_id: str,
        selected_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """POST /api/chat → ChatResponse"""
        payload = {
            "message": message,
            "user_id": 1,
            "session_id": session_id,
            "workspace_id": workspace_id,
        }
        if selected_skills is not None:
            payload["selected_skills"] = selected_skills

        resp = self._client.post("/api/chat", json=payload, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    async def chat_stream(
        self,
        message: str,
        workspace_id: str,
        session_id: str,
        selected_skills: Optional[List[str]] = None,
    ):
        """Websocket endpoint stream -> yields JSON dicts"""
        import websockets
        import json

        ws_url = (
            self.base_url.replace("http://", "ws://").replace("https://", "wss://")
            + "/api/chat/stream"
        )

        payload: Dict[str, Any] = {
            "message": message,
            "workspace_id": workspace_id,
            "session_id": session_id,
            "password": self._token or "",
        }
        if selected_skills is not None:
            payload["selected_skills"] = selected_skills

        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps(payload))
            while True:
                try:
                    response_str = await ws.recv()
                    yield json.loads(response_str)
                except websockets.exceptions.ConnectionClosed:
                    break

    def list_sessions(self, workspace_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """GET /api/chat/sessions → lista sesji"""
        params = {"workspace_id": workspace_id, "limit": limit}
        resp = self._client.get(
            "/api/chat/sessions", params=params, headers=self.headers
        )
        if resp.status_code == 401:
            return []
        resp.raise_for_status()
        return resp.json()

    def get_skills(self) -> List[Dict[str, Any]]:
        """GET /api/skills → lista dostępnych skilli"""
        resp = self._client.get("/api/skills", headers=self.headers)
        resp.raise_for_status()
        return resp.json()
