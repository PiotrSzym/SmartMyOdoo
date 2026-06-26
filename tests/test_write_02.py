"""WRITE-02: tryb edycji świadomy + prawda o zapisie (anty-konfabulacja).

Pokrywa:
- T1: ChatRequest.edit_mode (kontrakt).
- T2: read-mode write-guard — w 🟢 write-tool NIE jest wołany, model dostaje prośbę o 🔴.
- T3: WRITE_REPORT_RULE w prompcie + jednoznaczne zwroty narzędzi (server.py).
- T4: w 🔴 propozycja jest przechwycona (proposal_id) → karta w czacie.
"""

import pytest

from smartmyodoo.swarm.executor import (
    SkillExecutor,
    build_system_prompt,
    WRITE_REPORT_RULE,
    READ_MODE_BLOCK_MSG,
)
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.tools import TOOL_REGISTRY
from smartmyodoo.swarm.models import ChatRequest


# ── Fake LLM: tura 1 = tool_call odoo_update, tura 2 = zwykła odpowiedź ──
class _Fn:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, name, arguments):
        self.id = "call_1"
        self.function = _Fn(name, arguments)

    def model_dump(self):
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.function.name,
                "arguments": self.function.arguments,
            },
        }


class _Msg:
    def __init__(self, role="assistant", content=None, tool_calls=None):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls


class _Choice:
    def __init__(self, message):
        self.message = message


class _Resp:
    def __init__(self, message):
        self.choices = [_Choice(message)]


class FakeLLM:
    """Tura 1: żąda odoo_update. Tura 2: kończy tekstem."""

    def __init__(self):
        self.calls = 0

    def chat(self, messages=None, tools=None):
        self.calls += 1
        if self.calls == 1:
            tc = _ToolCall(
                "odoo_update",
                '{"model_name": "crm.lead", "record_id": 1207, '
                '"values_json": "{\\"name\\": \\"Traktory 200\\"}", '
                '"reason": "zmiana nazwy"}',
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
    """Podmień odoo_update na szpiega (zero realnego Odoo). Przywróć po teście."""
    original = TOOL_REGISTRY.get("odoo_update")
    state = {"called": False}

    def _fake(**kwargs):
        state["called"] = True
        return "📝 PROPOZYCJA (UPDATE) UTWORZONA — NIE wykonano. ID: testprop9"

    TOOL_REGISTRY["odoo_update"] = {
        "callable": _fake,
        "schema": {
            "type": "function",
            "function": {"name": "odoo_update", "description": ""},
        },
    }
    yield state
    if original is not None:
        TOOL_REGISTRY["odoo_update"] = original


# ── T1 ──
def test_chatrequest_has_edit_mode_default_false():
    req = ChatRequest(message="x", user_id=1, session_id="s")
    assert req.edit_mode is False
    assert ChatRequest(
        message="x", user_id=1, session_id="s", edit_mode=True
    ).edit_mode is True


# ── T3: prompt + reguła ──
def test_write_report_rule_in_system_prompt():
    prompt = build_system_prompt("Bazowy prompt skilla")
    assert WRITE_REPORT_RULE.strip()[:20] in prompt
    low = prompt.lower()
    assert "propozycj" in low and "nie pisz" in low  # anty-„gotowe”


# ── T2: read-mode (🟢) blokuje zapis, NIE woła narzędzia ──
def test_read_mode_blocks_write_and_does_not_call_tool(skill_config, spy_update_tool):
    ex = SkillExecutor(llm_client=FakeLLM(), edit_mode=False)
    result = ex.execute(skill_config, "zmień nazwę szansy 1207 na Traktory 200")
    assert spy_update_tool["called"] is False, "narzędzie zapisu nie powinno się wykonać w 🟢"
    assert ex.last_proposal is None, "w 🟢 nie powstaje propozycja"
    # model dostał komunikat o trybie odczytu (do relacji userowi)
    assert "TRYB ODCZYTU" in READ_MODE_BLOCK_MSG


# ── T4: edit-mode (🔴) wykonuje write i przechwytuje propozycję ──
def test_edit_mode_captures_proposal(skill_config, spy_update_tool):
    ex = SkillExecutor(llm_client=FakeLLM(), edit_mode=True)
    result = ex.execute(skill_config, "zmień nazwę szansy 1207 na Traktory 200")
    assert spy_update_tool["called"] is True, "w 🔴 narzędzie zapisu MA się wykonać"
    assert result["proposal"] is not None
    assert result["proposal"]["proposal_id"] == "testprop9"
    assert result["proposal"]["model"] == "crm.lead"
    assert result["proposal"]["method"] == "update"
    assert result["proposal"]["values"] == {"name": "Traktory 200"}
