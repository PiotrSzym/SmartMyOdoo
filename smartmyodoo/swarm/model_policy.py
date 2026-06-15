"""K4 (KEY-01): polityka wyboru modelu LLM per skill, z poziomami kosztów.

Tani model robi proste rzeczy (klasyfikacja, audyt-history), drogi tylko trudne
(architektura, audyt finansowy/security). Konfigurowalne przez ENV; docelowo z UI (K6).
"""

import os
from enum import Enum
from typing import Optional


class ModelTier(str, Enum):
    CHEAP = "cheap"  # proste: klasyfikacja intencji, krótkie odpowiedzi
    STANDARD = "standard"  # typowy dev/CRUD
    PREMIUM = "premium"  # architektura, trudny debug/audyt, długi kontekst


# Tier → model (ENV-override: MODEL_TIER_CHEAP/STANDARD/PREMIUM)
MODEL_POLICY = {
    ModelTier.CHEAP: os.environ.get(
        "MODEL_TIER_CHEAP", "openrouter/meta-llama/llama-3.1-8b-instruct"
    ),
    ModelTier.STANDARD: os.environ.get(
        "MODEL_TIER_STANDARD", "openrouter/anthropic/claude-3.5-haiku"
    ),
    ModelTier.PREMIUM: os.environ.get(
        "MODEL_TIER_PREMIUM", "openrouter/anthropic/claude-3.5-sonnet"
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
