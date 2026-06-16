"""FIX-02 / S3.2: dowód parytetu polityk między execute a execute_stream.

Niezmiennik bezpieczeństwa: dla tych samych (skill_config, message, phase_restrictions)
obie ścieżki podejmują IDENTYCZNĄ decyzję polityki (red flag, allowed_tools/schemas).
Różni się tylko prezentacja (raise vs yield error). Po S3.2 polityka jest w jednym helperze.
"""

import inspect

import pytest

from smartmyodoo.swarm.executor import SkillExecutor, RedFlagViolation
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.models import SkillName


def _config(**overrides):
    base = dict(
        name=SkillName.ODOO_CRUD,
        system_prompt="Test Prompt",
        allowed_tools=["odoo_search", "odoo_create"],
        red_flags=["DROP TABLE"],
        recommended_model="test-model",
    )
    base.update(overrides)
    return SkillConfig(**base)


async def _drain(agen):
    out = []
    async for item in agen:
        out.append(item)
    return out


@pytest.mark.asyncio
async def test_red_flag_parity_sync_vs_stream():
    """Ten sam red flag → execute rzuca, execute_stream yielduje error z tym samym tekstem."""
    cfg = _config()
    ex = SkillExecutor(llm_client=None)
    msg = "Please DROP TABLE users"

    # ścieżka sync: wyjątek
    with pytest.raises(RedFlagViolation) as exc:
        ex.execute(cfg, msg)
    sync_text = str(exc.value)

    # ścieżka stream: pierwszy event to error z identyczną treścią
    chunks = await _drain(ex.execute_stream(cfg, msg))
    assert chunks[0]["type"] == "error"
    assert chunks[0]["content"] == sync_text
    assert "DROP TABLE" in sync_text


def test_prepare_tools_read_only_removes_create():
    """Wspólny helper: read_only zdejmuje odoo_create (jedno źródło dla obu ścieżek)."""
    ex = SkillExecutor(llm_client=None)
    allowed, schemas = ex._prepare_tools(_config(read_only=True), None)
    assert "odoo_create" not in allowed
    assert "odoo_search" in allowed

    allowed2, _ = ex._prepare_tools(_config(read_only=False), None)
    assert "odoo_create" in allowed2


def test_prepare_tools_phase_restrictions():
    """phase_restrictions zawęża zbiór narzędzi — wspólnie dla obu ścieżek."""
    ex = SkillExecutor(llm_client=None)
    allowed, _ = ex._prepare_tools(_config(read_only=False), ["odoo_search"])
    assert allowed == ["odoo_search"]


def test_both_paths_call_shared_helpers_no_duplicate_policy():
    """Single-source: reguła red-flag/tool-filter NIE jest powielona w execute/execute_stream.

    Po S3.2 obie metody wołają _first_red_flag/_prepare_tools/_build_initial_messages,
    a nie zawierają drugiej kopii pętli `re.search(flag...)` ani `remove("odoo_create")`.
    """
    for name in ("execute", "execute_stream"):
        src = inspect.getsource(getattr(SkillExecutor, name))
        assert (
            "self._first_red_flag(" in src
        ), f"{name} nie używa wspólnego detektora red-flag"
        assert (
            "self._prepare_tools(" in src
        ), f"{name} nie używa wspólnego filtra narzędzi"
        assert (
            "self._build_initial_messages(" in src
        ), f"{name} nie używa wspólnego buildera"
        # brak zduplikowanej polityki inline
        assert (
            'remove("odoo_create")' not in src
        ), f"{name} ma zduplikowany filtr read_only"
        assert "re.search(flag" not in src, f"{name} ma zduplikowaną pętlę red-flag"
