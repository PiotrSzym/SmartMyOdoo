"""S2.2 (dowód): TokenGovernor realnie liczy koszty LLM i blokuje po przekroczeniu budżetu.

PRZED naprawą: `OpenRouterClient.chat` ignorował `response.usage`, governor.add_usage wołane
tylko w testach → `current_spend` zawsze 0.0 (atrapa kontroli kosztów).
PO naprawie: chat() raportuje realne zużycie do governora (pre-flight + record).
"""

import pytest

from smartmyodoo.swarm import llm_client as llm_mod
from smartmyodoo.mcp.token_governor import TokenGovernor


class _Usage:
    total_tokens = 1500


class _Msg:
    role = "assistant"
    content = "ok"
    tool_calls = None


class _Choice:
    message = _Msg()


class _Resp:
    choices = [_Choice()]
    usage = _Usage()


def test_governor_records_real_usage(monkeypatch):
    monkeypatch.setattr(llm_mod.litellm, "completion", lambda **kw: _Resp())
    monkeypatch.setattr(
        llm_mod.litellm, "completion_cost", lambda completion_response=None: 0.3
    )

    gov = TokenGovernor(max_budget_usd=1.0)
    client = llm_mod.OpenRouterClient(api_key="x", governor=gov)

    client.chat(messages=[{"role": "user", "content": "hi"}])

    # Koszty NIE są już 0.0 — realnie zliczone z odpowiedzi
    assert gov.current_spend == pytest.approx(0.3)
    assert gov.total_tokens == 1500


def test_governor_hard_block_when_over_budget(monkeypatch):
    monkeypatch.setattr(llm_mod.litellm, "completion", lambda **kw: _Resp())
    monkeypatch.setattr(
        llm_mod.litellm, "completion_cost", lambda completion_response=None: 0.0
    )

    gov = TokenGovernor(max_budget_usd=1.0)
    gov.current_spend = 2.0  # budżet już przekroczony
    client = llm_mod.OpenRouterClient(api_key="x", governor=gov)

    # pre-flight HARD-BLOCK: zero wywołań LLM przy wyczerpanym budżecie
    with pytest.raises(PermissionError, match="TOKEN GOVERNOR"):
        client.chat(messages=[{"role": "user", "content": "hi"}])


def test_no_governor_is_noop(monkeypatch):
    """Bez governora klient działa jak dawniej (kompatybilność)."""
    monkeypatch.setattr(llm_mod.litellm, "completion", lambda **kw: _Resp())
    client = llm_mod.OpenRouterClient(api_key="x")
    resp = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert resp is not None
