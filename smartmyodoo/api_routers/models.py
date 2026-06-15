"""K6 (KEY-01): API polityki modeli LLM — odczyt/zapis tier→model + budżet.

Zasila zakładkę „Modele" w panelu (UI-K6-change-map.md sekcja B).
SSoT polityki: smartmyodoo.swarm.model_policy.MODEL_POLICY + SKILL_TIER.
Budżet: globalny TokenGovernor (smartmyodoo.mcp.token_governor).
PUT nadpisuje politykę w pamięci procesu (runtime override; ENV pozostaje fallbackiem przy starcie).
"""

from typing import Dict, Optional, Tuple

from pydantic import BaseModel
from fastapi import APIRouter, Depends

from smartmyodoo.swarm import model_policy
from smartmyodoo.swarm.model_policy import ModelTier
from smartmyodoo.mcp.token_governor import governor
from smartmyodoo.api import require_auth

router = APIRouter(tags=["models"])


class ModelPolicyUpdate(BaseModel):
    """Częściowa aktualizacja: dowolny podzbiór tierów + opcjonalny budżet."""

    tiers: Optional[Dict[str, str]] = (
        None  # {"cheap": "...", "standard": "...", "premium": "..."}
    )
    max_budget_usd: Optional[float] = None


def _policy_payload() -> Dict:
    """Aktualny obraz polityki + budżetu (wspólny dla GET i odpowiedzi PUT)."""
    status = governor.get_status()
    return {
        "tiers": {tier.value: model_policy.MODEL_POLICY[tier] for tier in ModelTier},
        "skill_tier": {
            skill: tier.value for skill, tier in model_policy.SKILL_TIER.items()
        },
        "default_tier": model_policy.DEFAULT_TIER.value,
        "budget": {
            "max_budget_usd": status["max_budget_usd"],
            "spent_usd": status["spent_usd"],
            "can_continue": status["can_continue"],
        },
    }


@router.get("/api/models/policy")
async def get_models_policy(
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
) -> Dict:
    """Zwraca politykę modeli (tier→model), mapę skill→tier oraz stan budżetu."""
    return _policy_payload()


@router.put("/api/models/policy")
async def update_models_policy(
    update: ModelPolicyUpdate,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
) -> Dict:
    """Nadpisuje politykę w pamięci procesu. Ignoruje nieznane klucze tierów."""
    if update.tiers:
        for key, model in update.tiers.items():
            try:
                tier = ModelTier(key)
            except ValueError:
                continue  # nieznany tier — pomijamy zamiast 422
            if model:
                model_policy.MODEL_POLICY[tier] = model
    if update.max_budget_usd is not None and update.max_budget_usd > 0:
        governor.max_budget_usd = float(update.max_budget_usd)
    return _policy_payload()
