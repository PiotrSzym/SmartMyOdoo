"""K4 (KEY-01): routing modeli per skill z poziomami kosztów (tani↔drogi)."""

from smartmyodoo.swarm.model_policy import (
    ModelTier,
    MODEL_POLICY,
    resolve_model,
)


def test_cheap_for_classification_and_audit_history():
    assert resolve_model("classify_intent") == MODEL_POLICY[ModelTier.CHEAP]
    assert resolve_model("ODOO_AUDIT_HISTORY") == MODEL_POLICY[ModelTier.CHEAP]


def test_premium_for_hard_tasks():
    assert resolve_model("SECURITY_AUDIT") == MODEL_POLICY[ModelTier.PREMIUM]
    assert resolve_model("FINANCIAL_AUDIT") == MODEL_POLICY[ModelTier.PREMIUM]
    assert resolve_model("software_architecture") == MODEL_POLICY[ModelTier.PREMIUM]


def test_standard_default():
    assert resolve_model("ODOO_DEVELOPER") == MODEL_POLICY[ModelTier.STANDARD]
    assert resolve_model(None) == MODEL_POLICY[ModelTier.STANDARD]  # nieznany → default
    assert resolve_model("cokolwiek_nieznane") == MODEL_POLICY[ModelTier.STANDARD]


def test_overrides():
    # jawny model wygrywa
    assert resolve_model("SECURITY_AUDIT", model_override="x/custom") == "x/custom"
    # tier override wygrywa nad mapą skilla
    assert (
        resolve_model("SECURITY_AUDIT", tier_override=ModelTier.CHEAP)
        == MODEL_POLICY[ModelTier.CHEAP]
    )


def test_dispatcher_uses_tiered_model():
    from smartmyodoo.swarm.dispatcher import Dispatcher

    d = Dispatcher()  # fallback heurystyczny
    # "bezpieczeństwo" → SECURITY_AUDIT → PREMIUM
    sec = d.classify_intent("zrób audyt bezpieczeństwa i PII")
    assert sec.recommended_model == MODEL_POLICY[ModelTier.PREMIUM]
    # "napisz kod" → ODOO_DEVELOPER → STANDARD
    dev = d.classify_intent("napisz funkcję w module")
    assert dev.recommended_model == MODEL_POLICY[ModelTier.STANDARD]


# FIX (2026-06-16): claude-3.5-sonnet wycofany na OpenRouter (404). Guard przed powrotem.
def test_premium_model_not_deprecated():
    from smartmyodoo.swarm.model_policy import MODEL_POLICY, ModelTier

    prem = MODEL_POLICY[ModelTier.PREMIUM]
    assert prem.endswith("claude-3.5-sonnet") is False, "PREMIUM = wycofany model (404)"
    assert "sonnet" in prem or "opus" in prem  # nadal model premium


# TRUST-01 T4 (2026-06-25): PREMIUM musi być MOCNIEJSZY niż STANDARD (bug #5: były równe).
def test_premium_distinct_from_standard():
    from smartmyodoo.swarm.model_policy import MODEL_POLICY, ModelTier

    assert (
        MODEL_POLICY[ModelTier.PREMIUM] != MODEL_POLICY[ModelTier.STANDARD]
    ), "PREMIUM == STANDARD — audyt finansowy/security dostaje ten sam model co CRUD"
    # realny tier premium = Opus; standard = Sonnet
    assert "opus" in MODEL_POLICY[ModelTier.PREMIUM]
    assert "sonnet" in MODEL_POLICY[ModelTier.STANDARD]


# TRUST-01 T4 + decyzja usera 2026-06-25: aktualna generacja; haiku WYWALONE.
def test_models_are_current_generation():
    from smartmyodoo.swarm.model_policy import MODEL_POLICY, ModelTier

    assert MODEL_POLICY[ModelTier.CHEAP].endswith("claude-sonnet-4.6")  # haiku out
    assert MODEL_POLICY[ModelTier.STANDARD].endswith("claude-sonnet-4.6")
    assert MODEL_POLICY[ModelTier.PREMIUM].endswith("claude-opus-4.8")


def test_no_tier_uses_haiku():
    """Decyzja usera 2026-06-25: haiku gubił rekordy CRM i konfabulował awarie — OUT."""
    from smartmyodoo.swarm.model_policy import MODEL_POLICY

    for tier, model in MODEL_POLICY.items():
        assert "haiku" not in model.lower(), f"{tier} nadal używa haiku: {model}"


def test_chat_uses_fallback_model():
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1] / "smartmyodoo" / "api_routers" / "chat.py"
    ).read_text(encoding="utf-8")
    assert "fallback_model=MODEL_POLICY[ModelTier.STANDARD]" in src
