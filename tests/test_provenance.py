"""TRUST-01 T6 (decyzja D4 / 0G): stopka provenance odpowiedzi czatu.

Cel (US-T6): odpowiedź pokazuje źródło — „Odoo {wersja} · {N} rekordów ·
{k} zamaskowanych" — by konsultant mógł zaufać/zweryfikować. Bez logowania
wartości (tylko liczniki).
"""

from smartmyodoo.swarm.provenance import (
    build_provenance_footer,
    append_provenance,
    ProvenanceAccumulator,
)


def test_footer_full():
    f = build_provenance_footer(odoo_version=19, n_records=2, k_masked=1)
    assert "Odoo 19" in f
    assert "2 rekordów" in f
    assert "1 zamaskowanych" in f


def test_footer_empty_when_nothing_known():
    assert build_provenance_footer() == ""
    assert build_provenance_footer(odoo_version="unknown") == ""


def test_footer_skips_unknown_version():
    f = build_provenance_footer(n_records=5, k_masked=0)
    assert "Odoo" not in f
    assert "5 rekordów" in f
    assert "0 zamaskowanych" in f


def test_append_provenance_idempotent():
    reply = "Masz 2 zadania w projekcie."
    footer = build_provenance_footer(odoo_version=19, n_records=2, k_masked=1)
    once = append_provenance(reply, footer)
    twice = append_provenance(once, footer)
    assert footer in once
    assert once == twice  # nie dubluje stopki


def test_append_provenance_noop_on_empty_footer():
    assert append_provenance("odpowiedź", "") == "odpowiedź"


class _FakePii:
    """Imituje PiiMiddleware.counters (workspace -> {entity_type: count})."""

    def __init__(self, counters):
        self.counters = counters


def test_accumulator_masked_delta_counts_only_this_turn():
    pii = _FakePii({"ws": {"PERSON": 3}})
    acc = ProvenanceAccumulator(pii=pii, workspace_id="ws")
    # baseline = 3; podczas tury dochodzi 1 maska PERSON i 2 LOCATION
    pii.counters["ws"]["PERSON"] = 4
    pii.counters["ws"]["LOCATION"] = 2
    assert acc.masked_delta() == 3  # (4+2) - 3


def test_accumulator_records_max_count():
    acc = ProvenanceAccumulator(workspace_id="ws")
    acc.record_count(2)
    acc.record_count(10)
    acc.record_count(None)
    assert acc.n_records == 10


def test_accumulator_footer_includes_version_and_masked():
    pii = _FakePii({"ws": {"PERSON": 0}})
    acc = ProvenanceAccumulator(pii=pii, workspace_id="ws")
    acc.set_version(19)
    acc.record_count(2)
    pii.counters["ws"]["PERSON"] = 1
    footer = acc.footer()
    assert "Odoo 19" in footer
    assert "2 rekordów" in footer
    assert "1 zamaskowanych" in footer


def test_accumulator_no_footer_without_data():
    acc = ProvenanceAccumulator(workspace_id="ws")
    # nie dotknęliśmy Odoo (czysta rozmowa) → brak stopki
    assert acc.footer() == ""


def test_footer_does_not_leak_pii_values():
    # Stopka to WYŁĄCZNIE liczby — żadnych wartości (0G).
    pii = _FakePii({"ws": {"PERSON": 0}})
    acc = ProvenanceAccumulator(pii=pii, workspace_id="ws")
    acc.set_version(19)
    acc.record_count(2)
    pii.counters["ws"]["PERSON"] = 1
    footer = acc.footer()
    # tylko cyfry/etykiety, brak np. nazwisk
    assert "Henk" not in footer and "Molenkamp" not in footer


# ── Integracja: executor dokleja stopkę gdy tura odpytała Odoo (T6 end-to-end) ──


def test_executor_appends_provenance_footer_after_odoo_query():
    import json as _json
    from unittest.mock import MagicMock

    from smartmyodoo.swarm.executor import SkillExecutor
    from smartmyodoo.swarm.skills.skill_config import SkillConfig
    from smartmyodoo.swarm.models import SkillName

    cfg = SkillConfig(
        name=SkillName.ODOO_CRUD,
        system_prompt="Test Prompt",
        allowed_tools=["odoo_search"],
        red_flags=[],
        read_only=True,
        recommended_model="test-model",
    )

    # Tura 1: model wywołuje odoo_search; Tura 2: odpowiedź tekstowa.
    tool_resp = MagicMock()
    tc = MagicMock()
    tc.function.name = "odoo_search"
    tc.function.arguments = "{}"
    tc.id = "call_1"
    tm = MagicMock()
    tm.role = "assistant"
    tm.content = None
    tm.tool_calls = [tc]
    tool_resp.choices = [MagicMock(message=tm)]

    text_resp = MagicMock()
    txt = MagicMock()
    txt.role = "assistant"
    txt.content = "W projekcie RMO są 2 zadania."
    txt.tool_calls = None
    text_resp.choices = [MagicMock(message=txt)]

    llm = MagicMock()
    llm.chat.side_effect = [tool_resp, text_resp]

    executor = SkillExecutor(llm_client=llm)
    # Narzędzie zwraca count=2 i wersję Odoo 19 (jak po T3+T6 w mcp/server).
    executor._invoke_tool = MagicMock(  # type: ignore[method-assign]
        return_value=(_json.dumps({"records": [], "count": 2, "odoo_version": 19}), True, False)
    )

    result = executor.execute(cfg, "ile zadań w RMO")
    reply = result["response"]
    assert "2 zadania" in reply or "RMO" in reply
    # Stopka provenance doklejona:
    assert "źródło:" in reply
    assert "Odoo 19" in reply
    assert "2 rekordów" in reply
    assert result["provenance"]


def test_executor_no_footer_for_pure_chat():
    from unittest.mock import MagicMock

    from smartmyodoo.swarm.executor import SkillExecutor
    from smartmyodoo.swarm.skills.skill_config import SkillConfig
    from smartmyodoo.swarm.models import SkillName

    cfg = SkillConfig(
        name=SkillName.ODOO_CRUD,
        system_prompt="Test Prompt",
        allowed_tools=[],
        red_flags=[],
        recommended_model="test-model",
    )
    resp = MagicMock()
    m = MagicMock()
    m.role = "assistant"
    m.content = "Cześć! W czym pomóc?"
    m.tool_calls = None
    resp.choices = [MagicMock(message=m)]
    llm = MagicMock()
    llm.chat.return_value = resp

    executor = SkillExecutor(llm_client=llm)
    result = executor.execute(cfg, "cześć")
    # Bez odpytania Odoo → brak stopki (czysta rozmowa).
    assert "źródło:" not in result["response"]
    assert result["provenance"] == ""
