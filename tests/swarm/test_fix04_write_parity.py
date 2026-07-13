"""FIX-04 T1 (A-1): parytet polityk zapisu między execute a execute_stream.

DOWÓD DRIFTU: przed fixem pętla `execute_stream` NIE ma read-mode guardu ani
workspace-injection (executor.py:820-849) — te testy są CZERWONE. Po wpięciu
wspólnego `_pre_tool_policy` w OBIE pętle stają się zielone.

Wzorzec spy-tool: tests/test_write_02.py:133-151.
"""

import pytest

from smartmyodoo.swarm.executor import (
    SkillExecutor,
    READ_MODE_BLOCK_MSG,
    WORKSPACE_SCOPED_TOOLS,
)
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.tools import TOOL_REGISTRY
from smartmyodoo.swarm.sandbox import WRITE_TOOLS

_UPDATE_ARGS = (
    '{"model_name": "crm.lead", "record_id": 1207, '
    '"values_json": "{\\"name\\": \\"Traktory 200\\"}", "reason": "zmiana nazwy"}'
)


# ── Fake LLM (non-stream): tura1 = tool_call odoo_update, tura2 = tekst ──
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


class SyncFakeLLM:
    """Tura 1: żąda odoo_update. Tura 2: kończy tekstem."""

    def __init__(self):
        self.calls = 0

    def chat(self, messages=None, tools=None):
        self.calls += 1
        if self.calls == 1:
            return _Resp(_Msg(tool_calls=[_ToolCall("odoo_update", _UPDATE_ARGS)]))
        return _Resp(_Msg(content="OK."))


# ── Fake LLM (stream): odwzorowuje chat_stream chunk-delta (jak test_executor_stream) ──
class _SFn:
    def __init__(self, name=None, arguments=None):
        self.name = name
        self.arguments = arguments


class _STC:
    def __init__(self, index=0, id=None, name=None, arguments=None):
        self.index = index
        self.id = id
        self.function = _SFn(name, arguments)


class _SDelta:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _SChoice:
    def __init__(self, delta):
        self.delta = delta


class _SChunk:
    def __init__(self, choices):
        self.choices = choices


class StreamFakeLLM:
    """Tura 1: strumień tool_call odoo_update. Tura 2: strumień tekstu."""

    def __init__(self):
        self._done = False

    def chat_stream(self, messages=None, tools=None):
        if not self._done:
            self._done = True
            yield _SChunk(
                [_SChoice(_SDelta(tool_calls=[_STC(id="call_1", name="odoo_update")]))]
            )
            yield _SChunk(
                [_SChoice(_SDelta(tool_calls=[_STC(arguments=_UPDATE_ARGS)]))]
            )
        else:
            yield _SChunk([_SChoice(_SDelta(content="OK."))])


class RaisingStreamLLM:
    """chat_stream wybucha PRZY WYWOŁANIU wyjątkiem niosącym „sekret" w treści (np. błąd
    401 klienta LLM) — trafia w try/except wokół `chat_stream()` (executor.py:755)."""

    _SECRET = "SEKRET-LLM-KEY-sk-DO-NOT-LEAK-9999"

    def chat_stream(self, messages=None, tools=None):
        raise RuntimeError(f"Error code: 401 - {self._SECRET}")


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
    state = {"called": False, "kwargs": None}

    def _fake(**kwargs):
        state["called"] = True
        state["kwargs"] = kwargs
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


async def _drain(agen):
    return [c async for c in agen]


# ── Unit: _pre_tool_policy (SSoT polityki) ──
def test_pre_tool_policy_read_mode_blocks_write():
    ex = SkillExecutor(edit_mode=False, workspace_id="ws-real")
    args = {"model_name": "crm.lead"}
    msg = ex._pre_tool_policy("odoo_update", args)
    assert msg == READ_MODE_BLOCK_MSG  # 🟢 read → zapis zablokowany
    # injection nadal działa (workspace_id wstrzyknięty niezależnie od guardu)
    assert args["workspace_id"] == "ws-real"


def test_pre_tool_policy_edit_mode_allows_and_injects():
    ex = SkillExecutor(edit_mode=True, workspace_id="ws-real")
    args = {"model_name": "crm.lead"}
    assert ex._pre_tool_policy("odoo_update", args) is None  # 🔴 → brak blokady
    assert args["workspace_id"] == "ws-real"


def test_pre_tool_policy_fail_closed_default():
    """Fail-closed: bez jawnego edit_mode (default False) zapis jest blokowany."""
    ex = SkillExecutor(workspace_id="ws-real")  # edit_mode nie podany
    assert ex._pre_tool_policy("odoo_update", {}) == READ_MODE_BLOCK_MSG


def test_pre_tool_policy_read_tool_no_guard_but_scoped():
    """search_history: injection TAK, guard NIE (to nie WRITE_TOOL)."""
    assert "search_history" in WORKSPACE_SCOPED_TOOLS
    assert "search_history" not in WRITE_TOOLS
    ex = SkillExecutor(edit_mode=False, workspace_id="ws-real")
    args = {"query": "traktory"}
    assert ex._pre_tool_policy("search_history", args) is None  # brak guardu
    assert args["workspace_id"] == "ws-real"  # ale workspace wstrzyknięty


# ── Parytet: read-mode (🟢) blokuje zapis w OBU ścieżkach ──
def test_sync_read_mode_blocks_write(skill_config, spy_update_tool):
    ex = SkillExecutor(llm_client=SyncFakeLLM(), edit_mode=False, workspace_id="ws-real")
    ex.execute(skill_config, "zmień nazwę szansy 1207")
    assert spy_update_tool["called"] is False, "🟢 sync: narzędzie zapisu NIE może się wykonać"
    assert ex.last_proposal is None


@pytest.mark.asyncio
async def test_stream_read_mode_blocks_write(skill_config, spy_update_tool):
    """DRIFT PROOF: przed fixem stream NIE ma guardu → tool się wykonuje (RED)."""
    ex = SkillExecutor(
        llm_client=StreamFakeLLM(), edit_mode=False, workspace_id="ws-real"
    )
    await _drain(ex.execute_stream(skill_config, "zmień nazwę szansy 1207"))
    assert spy_update_tool["called"] is False, "🟢 stream: narzędzie zapisu NIE może się wykonać"


# ── Parytet: edit-mode (🔴) wykonuje zapis + wstrzykuje realny workspace ──
def test_sync_edit_mode_executes_and_injects_workspace(skill_config, spy_update_tool):
    ex = SkillExecutor(llm_client=SyncFakeLLM(), edit_mode=True, workspace_id="ws-real")
    ex.execute(skill_config, "zmień nazwę szansy 1207")
    assert spy_update_tool["called"] is True
    assert spy_update_tool["kwargs"].get("workspace_id") == "ws-real"


@pytest.mark.asyncio
async def test_stream_edit_mode_executes_and_injects_workspace(skill_config, spy_update_tool):
    """DRIFT PROOF: przed fixem stream nie wstrzykuje workspace → propozycja jako 'default' (RED)."""
    ex = SkillExecutor(
        llm_client=StreamFakeLLM(), edit_mode=True, workspace_id="ws-real"
    )
    await _drain(ex.execute_stream(skill_config, "zmień nazwę szansy 1207"))
    assert spy_update_tool["called"] is True, "🔴 stream: narzędzie zapisu MA się wykonać"
    assert spy_update_tool["kwargs"].get("workspace_id") == "ws-real", (
        "🔴 stream: workspace_id MUSI być wstrzyknięty (parytet z execute)"
    )


# ── S-1 (/sec): błąd streamu LLM nie może echować str(e) do klienta WS ──
@pytest.mark.asyncio
async def test_stream_llm_error_does_not_leak_exception_content(skill_config):
    """FIX-04 S-1 (A-4): wyjątek chat_stream → chunk błędu zawiera TYLKO typ, nie treść.
    chat.py forwarduje chunki verbatim, więc sanityzacja musi być w executorze."""
    ex = SkillExecutor(
        llm_client=RaisingStreamLLM(), edit_mode=False, workspace_id="ws-real"
    )
    chunks = await _drain(ex.execute_stream(skill_config, "cokolwiek"))
    errors = [c for c in chunks if c.get("type") == "error"]
    assert errors, "oczekiwano chunku błędu"
    content = errors[-1]["content"]
    assert RaisingStreamLLM._SECRET not in content, "sekret NIE może przeciec do klienta WS"
    assert content == "Błąd LLM: RuntimeError"
