import pytest
from unittest.mock import MagicMock
from smartmyodoo.swarm.executor import SkillExecutor, RedFlagViolation
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.models import SkillName

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.generate.return_value = "This is a mock response"
    return llm

@pytest.fixture
def test_config():
    return SkillConfig(
        name=SkillName.ODOO_CRUD,
        system_prompt="Test Prompt",
        allowed_tools=["xmlrpc", "shadow_mode"],
        red_flags=["DROP TABLE"],
        recommended_model="test-model"
    )

def test_executor_returns_response(mock_llm, test_config):
    executor = SkillExecutor(llm_client=mock_llm)
    response = executor.execute(test_config, "Hello")
    assert response["response"] == "This is a mock response"
    mock_llm.generate.assert_called_once()

def test_executor_blocks_red_flag(mock_llm, test_config):
    executor = SkillExecutor(llm_client=mock_llm)
    with pytest.raises(RedFlagViolation):
        executor.execute(test_config, "Please DROP TABLE users")
    mock_llm.generate.assert_not_called()

def test_executor_propagates_human_override(mock_llm):
    config = SkillConfig(
        name=SkillName.MAGIC_FIX,
        system_prompt="Test Prompt",
        allowed_tools=[],
        red_flags=[],
        requires_human_override=True,
        recommended_model="test-model"
    )
    executor = SkillExecutor(llm_client=mock_llm)
    response = executor.execute(config, "Hello")
    assert response["requires_human_override"] is True

def test_executor_filters_shadow_mode_for_read_only(mock_llm):
    config = SkillConfig(
        name=SkillName.FINANCIAL_AUDIT,
        system_prompt="Test Prompt",
        allowed_tools=["xmlrpc_read", "shadow_mode"],
        red_flags=[],
        read_only=True,
        recommended_model="test-model"
    )
    executor = SkillExecutor(llm_client=mock_llm)
    response = executor.execute(config, "Hello")
    assert "shadow_mode" not in response["tools_used"]
    assert "xmlrpc_read" in response["tools_used"]
