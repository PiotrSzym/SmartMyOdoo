import pytest
import httpx
from unittest.mock import patch, MagicMock
from smartmyodoo.http_client import SmartMyOdooClient


def test_client_login_success():
    client = SmartMyOdooClient(base_url="http://test")
    with patch.object(client._client, "post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "role": "admin"}
        mock_post.return_value = mock_response

        result = client.login("my_secret_pin")
        assert result["success"] is True
        assert result["role"] == "admin"
        assert client._token == "my_secret_pin"


def test_client_login_failure():
    client = SmartMyOdooClient(base_url="http://test")
    with patch.object(client._client, "post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid credentials"}
        mock_post.return_value = mock_response

        result = client.login("wrong_pin")
        assert result["success"] is False
        assert client._token is None


def test_client_chat_success():
    client = SmartMyOdooClient(base_url="http://test")
    client._token = "valid_pin"
    with patch.object(client._client, "post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "reply": "Witaj!",
            "action_type": "CHAT",
            "category": "H",
            "persona": "H",
            "model": "meta-llama/llama-3.1-8b-instruct",
            "selected_skills": [],
        }
        mock_post.return_value = mock_response

        result = client.chat("Hej", workspace_id="ws1", session_id="ses1")
        assert result["reply"] == "Witaj!"
        assert result["action_type"] == "CHAT"


def test_client_list_sessions():
    client = SmartMyOdooClient(base_url="http://test")
    client._token = "valid_pin"
    with patch.object(client._client, "get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "session_id": "ses1",
                "preview": "Hello",
                "message_count": 2,
                "last_activity": "2026-06-08T10:00:00",
            }
        ]
        mock_get.return_value = mock_response

        sessions = client.list_sessions("ws1", limit=5)
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "ses1"


def test_client_list_sessions_unauthorized():
    client = SmartMyOdooClient(base_url="http://test")
    client._token = "invalid_pin"
    with patch.object(client._client, "get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid credentials"}
        mock_get.return_value = mock_response

        sessions = client.list_sessions("ws1", limit=5)
        assert sessions == []


def test_client_get_skills():
    client = SmartMyOdooClient(base_url="http://test")
    client._token = "valid_pin"
    with patch.object(client._client, "get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "ODOO_DEVELOPER", "name": "Developer"}
        ]
        mock_get.return_value = mock_response

        skills = client.get_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "Developer"


def test_client_http_error():
    client = SmartMyOdooClient(base_url="http://test")
    client._token = "valid_pin"
    with patch.object(client._client, "post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            client.chat("Hej", workspace_id="ws1", session_id="ses1")


def test_client_connection_error():
    client = SmartMyOdooClient(base_url="http://test")
    with patch.object(client._client, "post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(httpx.ConnectError):
            client.login("pin")


def test_client_timeout_graceful():
    client = SmartMyOdooClient(base_url="http://test")
    client._token = "valid_pin"
    with patch.object(client._client, "post") as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            client.chat("Hej", workspace_id="ws1", session_id="ses1")
