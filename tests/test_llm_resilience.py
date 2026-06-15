"""K5 (KEY-01): odporność LLM — retry, fallback na zapasowy model, degradacja przy budżecie."""

from smartmyodoo.swarm import llm_client as llm_mod
from smartmyodoo.swarm.model_policy import (
    effective_model,
    resolve_model,
    ModelTier,
    MODEL_POLICY,
)


class _Resp:
    choices: list = []
    usage = None


def test_retry_succeeds_after_transient_error(monkeypatch):
    calls = {"n": 0}

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("503 transient")
        return _Resp()

    monkeypatch.setattr(llm_mod.litellm, "completion", flaky)
    client = llm_mod.OpenRouterClient(api_key="x", num_retries=2)
    resp = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert resp is not None and calls["n"] == 2  # 1 fail + 1 retry OK


def test_fallback_model_used_when_primary_fails(monkeypatch):
    seen = []

    def by_model(**kw):
        seen.append(kw["model"])
        if kw["model"] == "primary/x":
            raise RuntimeError("primary down")
        return _Resp()

    monkeypatch.setattr(llm_mod.litellm, "completion", by_model)
    client = llm_mod.OpenRouterClient(
        api_key="x", model="primary/x", fallback_model="fallback/y", num_retries=1
    )
    resp = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert resp is not None
    assert (
        "primary/x" in seen and "fallback/y" in seen
    )  # próbował primary, potem fallback


def test_all_attempts_fail_returns_none(monkeypatch):
    def always_fail(**kw):
        raise RuntimeError("down")

    monkeypatch.setattr(llm_mod.litellm, "completion", always_fail)
    client = llm_mod.OpenRouterClient(api_key="x", fallback_model="f/y", num_retries=1)
    assert client.chat(messages=[{"role": "user", "content": "hi"}]) is None


class _Gov:
    def __init__(self, maxb, spent):
        self._s = {"max_budget_usd": maxb, "spent_usd": spent}

    def get_status(self):
        return self._s


def test_budget_degradation():
    # budżet prawie wyczerpany → PREMIUM degraduje do STANDARD
    low = _Gov(1.0, 0.95)
    assert (
        effective_model("SECURITY_AUDIT", governor=low)
        == MODEL_POLICY[ModelTier.STANDARD]
    )
    # budżet zdrowy → PREMIUM zostaje
    ok = _Gov(1.0, 0.0)
    assert (
        effective_model("SECURITY_AUDIT", governor=ok)
        == MODEL_POLICY[ModelTier.PREMIUM]
    )
    # bez governora = jak resolve_model
    assert effective_model("SECURITY_AUDIT") == resolve_model("SECURITY_AUDIT")
