import pytest
from unittest.mock import MagicMock

from smartmyodoo.swarm.executor import SkillExecutor
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.tools import TOOL_REGISTRY


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    return llm


@pytest.fixture
def skill_config():
    # Make sure we use a real tool so Pydantic validation passes
    return SkillConfig(
        name="ODOO_DEVELOPER",
        system_prompt="Test",
        allowed_tools=["odoo_search"],
        red_flags=["hack", "destroy"],
        recommended_model="claude-3-haiku-20240307",
    )


@pytest.mark.asyncio
async def test_execute_stream_red_flag(skill_config):
    executor = SkillExecutor()
    generator = executor.execute_stream(skill_config, "I want to hack the system")
    chunks = [chunk async for chunk in generator]

    assert len(chunks) == 1
    assert chunks[0]["type"] == "error"
    assert "Red flag triggered" in chunks[0]["content"]


@pytest.mark.asyncio
async def test_execute_stream_success(mock_llm, skill_config):
    executor = SkillExecutor(llm_client=mock_llm)

    # Mocking stream generator
    class MockDelta:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls

    class MockChoice:
        def __init__(self, delta):
            self.delta = delta

    class MockChunk:
        def __init__(self, choices):
            self.choices = choices

    def mock_chat_stream(*args, **kwargs):
        yield MockChunk([MockChoice(MockDelta(content="Hello "))])
        yield MockChunk([MockChoice(MockDelta(content="World!"))])

    mock_llm.chat_stream = mock_chat_stream

    generator = executor.execute_stream(skill_config, "Hello")
    chunks = [chunk async for chunk in generator]

    assert len(chunks) == 3  # token, token, done
    assert chunks[0] == {"type": "token", "content": "Hello "}
    assert chunks[1] == {"type": "token", "content": "World!"}
    assert chunks[2] == {"type": "done"}


@pytest.mark.asyncio
async def test_execute_stream_tool_calls(mock_llm, skill_config):
    executor = SkillExecutor(llm_client=mock_llm)

    # Setup mock tool
    TOOL_REGISTRY["odoo_search"] = {
        "callable": lambda **kwargs: "Tool Success",
        "schema": {
            "type": "function",
            "function": {"name": "odoo_search", "description": ""},
        },
    }

    class MockToolCallFunction:
        def __init__(self, name=None, arguments=None):
            self.name = name
            self.arguments = arguments

    class MockToolCall:
        def __init__(self, index=0, id=None, name=None, arguments=None):
            self.index = index
            self.id = id
            self.function = MockToolCallFunction(name, arguments)

    class MockDelta:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls

    class MockChoice:
        def __init__(self, delta):
            self.delta = delta

    class MockChunk:
        def __init__(self, choices):
            self.choices = choices

    state = {"called": False}

    def mock_chat_stream(*args, **kwargs):
        if not state["called"]:
            state["called"] = True
            yield MockChunk(
                [
                    MockChoice(
                        MockDelta(
                            tool_calls=[
                                MockToolCall(
                                    id="1", name="odoo_search", arguments='{"k"'
                                )
                            ]
                        )
                    )
                ]
            )
            yield MockChunk(
                [
                    MockChoice(
                        MockDelta(tool_calls=[MockToolCall(arguments='ey":"value"}')])
                    )
                ]
            )
        else:
            yield MockChunk([MockChoice(MockDelta(content="Done tools"))])

    mock_llm.chat_stream = mock_chat_stream

    generator = executor.execute_stream(skill_config, "Use tool")
    chunks = [chunk async for chunk in generator]

    # Expected chunks:
    # 1. log: Wywoływanie narzędzia...
    # 2. token: Done tools
    # 3. done
    types = [c["type"] for c in chunks]
    assert "log" in types
    assert "token" in types
    assert "done" in types
