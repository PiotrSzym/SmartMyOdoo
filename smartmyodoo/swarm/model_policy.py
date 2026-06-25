"""K4 (KEY-01): polityka wyboru modelu LLM per skill, z poziomami kosztów.

Tani model robi proste rzeczy (klasyfikacja, audyt-history), drogi tylko trudne
(architektura, audyt finansowy/security). Konfigurowalne przez ENV; docelowo z UI (K6).
"""

import os
from enum import Enum
from typing import Any, Optional


class ModelTier(str, Enum):
    CHEAP = "cheap"  # proste: klasyfikacja intencji, krótkie odpowiedzi
    STANDARD = "standard"  # typowy dev/CRUD
    PREMIUM = "premium"  # architektura, trudny debug/audyt, długi kontekst


# Tier → model (ENV-override: MODEL_TIER_CHEAP/STANDARD/PREMIUM)
# TRUST-01 T4 (2026-06-25): odświeżenie modeli. Slugi zweryfikowane na OpenRouter
# (anthropic/claude-haiku-4.5, …/claude-sonnet-4.6, …/claude-opus-4.8). PREMIUM
# rozdzielony od STANDARD — audyt finansowy/security idzie mocniejszym Opusem.
MODEL_POLICY = {
    ModelTier.CHEAP: os.environ.get(
        # Dispatcher (klasyfikacja intencji) + audit-history. Decyzja usera 2026-06-25:
        # haiku-4.5 OUT — był zbyt słaby (gubił rekordy CRM, KONFABULOWAŁ „problem z
        # połączeniem" zamiast przyznać błąd). CHEAP = sonnet-4.6, jak STANDARD — żaden
        # tier nie używa już haiku. Wyższy koszt, ale wiarygodne zapytania o Odoo.
        "MODEL_TIER_CHEAP",
        "openrouter/anthropic/claude-sonnet-4.6",
    ),
    ModelTier.STANDARD: os.environ.get(
        # Domyślny model interaktywnego czatu/CRUD. sonnet-4.6 ($3/$15, 1M kontekstu)
        # — aktualna generacja, celniejszy przy polach/wersjach Odoo niż 4.5.
        "MODEL_TIER_STANDARD",
        "openrouter/anthropic/claude-sonnet-4.6",
    ),
    ModelTier.PREMIUM: os.environ.get(
        # Audyt finansowy/security, architektura, magic-fix. opus-4.8 ($5/$25, 1M) —
        # realnie mocniejszy niż STANDARD (wcześniej PREMIUM==STANDARD, bug TRUST-01 #5).
        "MODEL_TIER_PREMIUM",
        "openrouter/anthropic/claude-opus-4.8",
    ),
}

# Skill/funkcja → wymagany poziom (klucze = wartości SkillName + funkcje specjalne)
SKILL_TIER = {
    "classify_intent": ModelTier.CHEAP,  # Dispatcher zawsze tani
    "ODOO_AUDIT_HISTORY": ModelTier.CHEAP,
    "ODOO_BUSINESS_ANALYST": ModelTier.STANDARD,
    "ODOO_DEVELOPER": ModelTier.STANDARD,
    "ODOO_CRUD": ModelTier.STANDARD,
    "ODOO_ETL_MANAGER": ModelTier.STANDARD,
    "ODOO_API_EXPERT": ModelTier.STANDARD,
    "ODOO_DEVOPS_GITHUB": ModelTier.STANDARD,
    "ODOO_SH_LOGS": ModelTier.STANDARD,
    "FINANCIAL_AUDIT": ModelTier.PREMIUM,
    "SECURITY_AUDIT": ModelTier.PREMIUM,
    "MAGIC_FIX": ModelTier.PREMIUM,
    "software_architecture": ModelTier.PREMIUM,
}

DEFAULT_TIER = ModelTier.STANDARD


def resolve_model(
    skill: Optional[str] = None,
    tier_override: Optional[ModelTier] = None,
    model_override: Optional[str] = None,
) -> str:
    """Zwraca ID modelu dla danego skilla.

    Priorytet: model_override (jawny wybór) > tier_override > tier ze SKILL_TIER > DEFAULT.
    """
    if model_override:
        return model_override
    tier = tier_override or SKILL_TIER.get(skill or "", DEFAULT_TIER)
    return MODEL_POLICY[tier]


_DOWNGRADE = {
    ModelTier.PREMIUM: ModelTier.STANDARD,
    ModelTier.STANDARD: ModelTier.CHEAP,
}


def effective_model(
    skill: Optional[str] = None,
    governor: Optional[Any] = None,
    low_ratio: float = 0.15,
    tier_override: Optional[ModelTier] = None,
    model_override: Optional[str] = None,
) -> str:
    """K5: jak resolve_model, ale przy NISKIM budżecie degraduje tier o jeden poziom
    (graceful degradation — tańszy model zamiast twardej blokady)."""
    if model_override:
        return model_override
    tier = tier_override or SKILL_TIER.get(skill or "", DEFAULT_TIER)
    if governor is not None:
        try:
            st = governor.get_status()
            maxb = float(st.get("max_budget_usd", 0) or 0)
            spent = float(st.get("spent_usd", 0) or 0)
            if maxb > 0 and (maxb - spent) / maxb <= low_ratio and tier in _DOWNGRADE:
                tier = _DOWNGRADE[tier]
        except Exception:
            pass
    return MODEL_POLICY[tier]
