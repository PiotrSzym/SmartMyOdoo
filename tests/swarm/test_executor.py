import pytest
from unittest.mock import MagicMock
from smartmyodoo.swarm.executor import SkillExecutor, RedFlagViolation
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.models import SkillName


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Mock OpenRouter chat response
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.role = "assistant"
    mock_message.content = "This is a mock response"
    mock_message.tool_calls = None
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    llm.chat.return_value = mock_response
    return llm


@pytest.fixture
def test_config():
    return SkillConfig(
        name=SkillName.ODOO_CRUD,
        system_prompt="Test Prompt",
        allowed_tools=["odoo_search", "odoo_create"],
        red_flags=["DROP TABLE"],
        recommended_model="test-model",
    )


def test_executor_returns_response(mock_llm, test_config):
    executor = SkillExecutor(llm_client=mock_llm)
    response = executor.execute(test_config, "Hello")
    assert response["response"] == "This is a mock response"
    mock_llm.chat.assert_called_once()


def test_executor_blocks_red_flag(mock_llm, test_config):
    executor = SkillExecutor(llm_client=mock_llm)
    with pytest.raises(RedFlagViolation):
        executor.execute(test_config, "Please DROP TABLE users")
    mock_llm.chat.assert_not_called()


def test_executor_propagates_human_override(mock_llm):
    config = SkillConfig(
        name=SkillName.MAGIC_FIX,
        system_prompt="Test Prompt",
        allowed_tools=[],
        red_flags=[],
        requires_human_override=True,
        recommended_model="test-model",
    )
    executor = SkillExecutor(llm_client=mock_llm)
    response = executor.execute(config, "Hello")
    assert response["requires_human_override"] is True


def test_executor_filters_shadow_mode_for_read_only(mock_llm):
    config = SkillConfig(
        name=SkillName.FINANCIAL_AUDIT,
        system_prompt="Test Prompt",
        allowed_tools=["odoo_search", "odoo_create"],
        red_flags=[],
        read_only=True,
        recommended_model="test-model",
    )
    # Provide a mock tool call response
    tool_mock_response = MagicMock()
    tool_mock_choice = MagicMock()
    tool_mock_message = MagicMock()
    tool_mock_message.role = "assistant"
    tool_mock_message.content = None
    tc = MagicMock()
    tc.function.name = "odoo_search"
    tc.function.arguments = "{}"
    tool_mock_message.tool_calls = [tc]
    tool_mock_choice.message = tool_mock_message
    tool_mock_response.choices = [tool_mock_choice]

    # second response text
    text_mock_response = MagicMock()
    text_mock_choice = MagicMock()
    text_mock_message = MagicMock()
    text_mock_message.role = "assistant"
    text_mock_message.content = "Done"
    text_mock_message.tool_calls = None
    text_mock_choice.message = text_mock_message
    text_mock_response.choices = [text_mock_choice]

    mock_llm.chat.side_effect = [tool_mock_response, text_mock_response]

    executor = SkillExecutor(llm_client=mock_llm)
    response = executor.execute(config, "Hello")
    assert "odoo_create" not in response["tools_used"]
    assert "odoo_search" in response["tools_used"]
