"""S2.3 (dowód): sandbox FAKTYCZNIE izoluje — fail-closed + redirect narzędzi na scratchpad.

PRZED naprawą: gdy klon się nie udał, executor i tak wykonywał write na produkcji (fail-open);
nazwa scratchpada była ignorowana (narzędzia szły na oryginalną bazę) — sandbox był dekoracyjny.
PO naprawie: brak izolacji → BLOKADA zapisu; udana izolacja → ODOO_DB przekierowane na scratchpad.
"""

import os

from smartmyodoo.swarm.executor import SkillExecutor
from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.tools import TOOL_REGISTRY


# ── Minimalne obiekty odpowiedzi LLM (tool-call w 1. iteracji, finał w 2.) ──
class _Fn:
    def __init__(self, name, args):
        self.name = name
        self.arguments = args


class _TC:
    def __init__(self, id, name, args):
        self.id = id
        self.function = _Fn(name, args)

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
    def __init__(self, content=None, tool_calls=None):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls


class _Resp:
    def __init__(self, msg):
        self.choices = [type("C", (), {"message": msg})()]


class TwoStepLLM:
    """1. wywołanie → tool_call odoo_create; 2. → odpowiedź finalna."""

    def __init__(self, args):
        self.calls = 0
        self.args = args

    def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            return _Resp(_Msg(tool_calls=[_TC("c1", "odoo_create", self.args)]))
        return _Resp(_Msg(content="gotowe"))


class FakeSandbox:
    def __init__(self, scratchpad, enabled=True):
        self.enabled = enabled
        self._scratch = scratchpad
        self.exited = None

    def is_write_tool(self, name):
        return name in {"odoo_create", "odoo_update", "odoo_delete"}

    def enter_sandbox(self, original_db):
        return self._scratch

    def exit_sandbox(self, success=True):
        self.exited = success


def _skill():
    return SkillConfig(
        name=SkillName.ODOO_DEVELOPER,
        system_prompt="Asystent.",
        allowed_tools=["odoo_create"],
        red_flags=[],
        recommended_model="claude-3-5-sonnet",
    )


_ARGS = '{"model_name": "res.partner", "values_json": "{}", "reason": "test"}'


def test_failclosed_blocks_write_when_clone_fails(monkeypatch):
    monkeypatch.setenv("ODOO_DB", "prod_db")
    called = {"n": 0}

    def spy(**kwargs):
        called["n"] += 1
        return "NIE POWINNO SIĘ WYKONAĆ"

    monkeypatch.setitem(TOOL_REGISTRY["odoo_create"], "callable", spy)

    sandbox = FakeSandbox(scratchpad=None, enabled=True)  # klon się NIE udał
    ex = SkillExecutor(llm_client=TwoStepLLM(_ARGS), sandbox=sandbox)
    ex.execute(_skill(), "utwórz partnera")

    # narzędzie write NIE zostało wykonane na produkcji
    assert called["n"] == 0
    # ODOO_DB nie zostało zmienione (brak redirectu)
    assert os.environ["ODOO_DB"] == "prod_db"


def test_redirects_db_to_scratchpad(monkeypatch):
    monkeypatch.setenv("ODOO_DB", "prod_db")
    seen_db = {}

    def spy(**kwargs):
        seen_db["at_call"] = os.environ.get("ODOO_DB")
        return "ok"

    monkeypatch.setitem(TOOL_REGISTRY["odoo_create"], "callable", spy)

    sandbox = FakeSandbox(scratchpad="prod_db_agent_scratchpad", enabled=True)
    ex = SkillExecutor(llm_client=TwoStepLLM(_ARGS), sandbox=sandbox)
    ex.execute(_skill(), "utwórz partnera")

    # podczas wykonania narzędzia baza była przekierowana na scratchpad
    assert seen_db["at_call"] == "prod_db_agent_scratchpad"
    # po zakończeniu — przywrócona oryginalna baza
    assert os.environ["ODOO_DB"] == "prod_db"
