import os

class TokenGovernor:
    """
    Zarządca budżetu tokenów dla danej sesji Agenta.
    Zabezpiecza przed wpadnięciem agenta w nieskończoną pętlę i nabiciem wysokiego rachunku.
    """
    def __init__(self, max_budget_usd: float = 1.0):
        self.max_budget_usd = max_budget_usd
        self.current_spend = 0.0
        self.total_tokens = 0
        
    def add_usage(self, tokens: int, cost_per_1k: float) -> None:
        """Dodaje użycie tokenów i aktualizuje koszt. Blokuje jeśli przekroczono budżet."""
        cost = (tokens / 1000.0) * cost_per_1k
        self.current_spend += cost
        self.total_tokens += tokens
        
        if self.current_spend > self.max_budget_usd:
            raise PermissionError(
                f"🚨 TOKEN GOVERNOR ALERT: Przekroczono budżet sesji! "
                f"Wydano: ${self.current_spend:.4f} z dozwolonych ${self.max_budget_usd:.4f}. "
                f"Dalsze operacje na bazie danych zostały zablokowane ze względów bezpieczeństwa."
            )

    def get_status(self) -> dict:
        return {
            "spent_usd": round(self.current_spend, 4),
            "max_budget_usd": self.max_budget_usd,
            "total_tokens": self.total_tokens,
            "can_continue": self.current_spend <= self.max_budget_usd
        }

# Globalna instancja dla serwera (domyślnie 1.00 USD, można nadpisać zmienną środowiskową)
governor = TokenGovernor(max_budget_usd=float(os.getenv("MAX_BUDGET_USD", "1.0")))
