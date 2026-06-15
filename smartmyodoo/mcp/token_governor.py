import os
from smartmyodoo.core.database import SessionLocal
from smartmyodoo.core.models import TokenUsage


class TokenGovernor:
    """
    Zarządca budżetu tokenów dla danej sesji Agenta.
    Zapisuje użycie do bazy danych SQLite.
    """

    def __init__(self, max_budget_usd: float = 1.0):
        self.max_budget_usd = max_budget_usd
        self.current_spend = 0.0
        self.total_tokens = 0

    def record(self, tokens: int, cost: float, model: str = "unknown") -> None:
        """Zapisuje REALNE zużycie (tokeny + koszt USD). Blokuje po przekroczeniu budżetu.

        Wywoływane przez `OpenRouterClient` po każdym wywołaniu LLM (S2.2) — wcześniej
        nigdy nie podłączone, przez co `current_spend` zawsze wynosił 0.0 (atrapa).
        """
        self.current_spend += cost
        self.total_tokens += tokens

        # Save to SQLite (best-effort)
        db = SessionLocal()
        try:
            usage_log = TokenUsage(model=model, tokens_used=tokens, cost=cost)
            db.add(usage_log)
            db.commit()
        except Exception:
            pass  # fallback to in-memory only if db fails
        finally:
            db.close()

        if self.current_spend > self.max_budget_usd:
            raise PermissionError(
                f"🚨 TOKEN GOVERNOR ALERT: Przekroczono budżet sesji! "
                f"Wydano: ${self.current_spend:.4f} z dozwolonych ${self.max_budget_usd:.4f}. "
                f"Dalsze operacje na bazie danych zostały zablokowane ze względów bezpieczeństwa."
            )

    def add_usage(
        self, tokens: int, cost_per_1k: float, model: str = "unknown"
    ) -> None:
        """Dodaje użycie tokenów licząc koszt z ceny za 1k (kompatybilność wsteczna)."""
        cost = (tokens / 1000.0) * cost_per_1k
        self.record(tokens, cost, model)

    def get_status(self) -> dict:
        return {
            "spent_usd": round(self.current_spend, 4),
            "max_budget_usd": self.max_budget_usd,
            "total_tokens": self.total_tokens,
            "can_continue": self.current_spend <= self.max_budget_usd,
        }


# Globalna instancja dla serwera (domyślnie 1.00 USD, można nadpisać zmienną środowiskową)
governor = TokenGovernor(max_budget_usd=float(os.getenv("MAX_BUDGET_USD", "1.0")))
