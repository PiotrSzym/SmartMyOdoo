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
