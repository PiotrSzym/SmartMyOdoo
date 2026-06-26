"""WRITE-03: naprawa pętli apply (creds przy apply + realny workspace w propozycji).

T2 (tu, unit): executor wstrzykuje REALNY workspace_id do argumentów narzędzia zapisu,
by propozycja była otagowana właściwą przestrzenią (apply trafi we właściwą instancję
Odoo, nie w domyślny „default”). T1 (creds przy apply) weryfikowany LIVE.
"""

import pytest

from smartmyodoo.swarm.executor import SkillExecutor
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.tools import TOOL_REGISTRY


class _Fn:
    def __init__(self, name, arguments):
        self.name, self.arguments = name, arguments


class _ToolCall:
    def __init__(self, name, arguments):
        self.id = "call_1"
        self.function = _Fn(name, arguments)

    def model_dump(self):
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.function.name, "arguments": self.function.arguments},
        }


class _Msg:
    def __init__(self, role="assistant", content=None, tool_calls=None):
        self.role, self.content, self.tool_calls = role, content, tool_calls


class _Resp:
    def __init__(self, message):
        self.choices = [type("C", (), {"message": message})()]


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, messages=None, tools=None):
        self.calls += 1
        if self.calls == 1:
            tc = _ToolCall(
                "odoo_update",
                '{"model_name": "crm.lead", "record_id": 1207, '
                '"values_json": "{\\"name\\": \\"X\\"}", "reason": "r"}',
            )
            return _Resp(_Msg(tool_calls=[tc]))
        return _Resp(_Msg(content="OK."))


@pytest.fixture
def skill_config():
    return SkillConfig(
        name="ODOO_CRUD",
        system_prompt="Test",
        allowed_tools=["odoo_update"],
        red_flags=[],
        recommended_model="x",
    )


@pytest.fixture
def spy_update_tool():
    original = TOOL_REGISTRY.get("odoo_update")
    seen = {}

    def _fake(**kwargs):
        seen.update(kwargs)
        return "📝 PROPOZYCJA (UPDATE) UTWORZONA. ID: testprop9"

    TOOL_REGISTRY["odoo_update"] = {
        "callable": _fake,
        "schema": {"type": "function", "function": {"name": "odoo_update", "description": ""}},
    }
    yield seen
    if original is not None:
        TOOL_REGISTRY["odoo_update"] = original


def test_write_tool_gets_real_workspace(skill_config, spy_update_tool):
    """T2: propozycja niesie realny workspace (nie domyślny 'default')."""
    ex = SkillExecutor(
        llm_client=FakeLLM(), edit_mode=True, workspace_id="myodooTest"
    )
    ex.execute(skill_config, "zmień nazwę 1207")
    assert spy_update_tool.get("workspace_id") == "myodooTest", (
        "narzędzie zapisu MUSI dostać realny workspace, by apply trafił we właściwą bazę"
    )


def test_empty_workspace_not_injected(skill_config, spy_update_tool):
    """Brak workspace (np. test jednostkowy) → nie nadpisujemy domyślnego."""
    ex = SkillExecutor(llm_client=FakeLLM(), edit_mode=True, workspace_id="")
    ex.execute(skill_config, "zmień nazwę 1207")
    # gdy workspace_id pusty — nie wstrzykujemy klucza (zostaje domyślny w narzędziu)
    assert "workspace_id" not in spy_update_tool
