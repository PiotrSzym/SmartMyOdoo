import pytest
from unittest.mock import patch

from smartmyodoo.swarm.llm_client import OpenRouterClient


@pytest.fixture
def client():
    return OpenRouterClient(api_key="test-key", model="test-model")


def test_chat_stream_success(client):
    with patch("smartmyodoo.swarm.llm_client.litellm.completion") as mock_completion:
        # Mocking the generator returned by litellm
        mock_completion.return_value = ["chunk1", "chunk2"]

        generator = client.chat_stream([{"role": "user", "content": "hi"}])
        chunks = list(generator)

        assert len(chunks) == 2
        assert chunks == ["chunk1", "chunk2"]
        mock_completion.assert_called_once()
        _, kwargs = mock_completion.call_args
        assert kwargs["stream"] is True
        assert kwargs["api_key"] == "test-key"


def test_chat_stream_with_tools(client):
    with patch("smartmyodoo.swarm.llm_client.litellm.completion") as mock_completion:
        mock_completion.return_value = ["chunk1"]
        tools = [{"type": "function", "function": {"name": "test_tool"}}]

        generator = client.chat_stream([{"role": "user", "content": "hi"}], tools=tools)
        chunks = list(generator)

        assert len(chunks) == 1
        assert chunks == ["chunk1"]
        mock_completion.assert_called_once()
        _, kwargs = mock_completion.call_args
        assert kwargs["stream"] is True
        assert kwargs["tools"] == tools


def test_chat_stream_error_handling(client):
    with patch("smartmyodoo.swarm.llm_client.litellm.completion") as mock_completion:
        mock_completion.side_effect = Exception("API Error")

        generator = client.chat_stream([{"role": "user", "content": "hi"}])
        chunks = list(generator)

        assert len(chunks) == 1
        error_chunk = chunks[0]

        assert hasattr(error_chunk, "choices")
        assert len(error_chunk.choices) == 1
        assert hasattr(error_chunk.choices[0], "delta")
        assert "API Error" in error_chunk.choices[0].delta.content
        assert error_chunk.choices[0].delta.tool_calls is None
