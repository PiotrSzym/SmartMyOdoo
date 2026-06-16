import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from smartmyodoo.api import app

client = TestClient(app)


def test_websocket_stream_invalid_auth():
    with patch("smartmyodoo.api_routers.chat.get_auth_key") as mock_auth:
        mock_auth.return_value = (None, None)

        with client.websocket_connect("/api/chat/stream") as websocket:
            websocket.send_json({"message": "Hello", "password": "wrongpassword"})
            data = websocket.receive_json()

            assert data["type"] == "error"
            assert "Invalid credentials" in data["content"]


def test_websocket_stream_no_llm_key():
    with patch("smartmyodoo.api_routers.chat.get_auth_key") as mock_auth, patch(
        "smartmyodoo.api_routers.chat.vault.load_vault"
    ) as mock_vault, patch.dict("os.environ", {}, clear=True):
        mock_auth.return_value = (b"testkey", "admin")
        mock_vault.return_value = {}  # No OPENROUTER_KEY

        with client.websocket_connect("/api/chat/stream") as websocket:
            websocket.send_json({"message": "Hello", "password": "goodpassword"})
            data = websocket.receive_json()

            assert data["type"] == "error"
            assert "Brak klucza OPENROUTER_KEY" in data["content"]


@pytest.mark.asyncio
async def test_websocket_stream_success():
    with patch("smartmyodoo.api_routers.chat.get_auth_key") as mock_auth, patch(
        "smartmyodoo.api_routers.chat.vault.load_vault"
    ) as mock_vault, patch.dict(
        "os.environ", {"OPENROUTER_KEY": "test_llm_key"}
    ), patch("smartmyodoo.swarm.executor.SkillExecutor.execute_stream") as mock_exec:
        mock_auth.return_value = (b"testkey", "admin")
        mock_vault.return_value = {"OPENROUTER_KEY": {"api_key": "test_llm_key"}}

        # Async generator mock
        async def mock_generator(*args, **kwargs):
            yield {"type": "log", "content": "Start"}
            yield {"type": "token", "content": "Hello"}
            yield {"type": "done"}

        mock_exec.side_effect = mock_generator

        with client.websocket_connect("/api/chat/stream") as websocket:
            websocket.send_json({"message": "Hello", "password": "goodpassword"})

            # Receive 1
            data1 = websocket.receive_json()
            assert data1["type"] == "log"

            # Receive 2
            data2 = websocket.receive_json()
            assert data2["type"] == "token"
            assert data2["content"] == "Hello"

            # Receive 3
            data3 = websocket.receive_json()
            assert data3["type"] == "done"
