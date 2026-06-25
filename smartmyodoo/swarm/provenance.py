"""TRUST-01 T6 (decyzja D4 / 0G): provenance odpowiedzi czatu.

Stopka „źródła": Odoo {wersja} · {N} rekordów · {k} zamaskowanych. Daje
konsultantowi możliwość ZWERYFIKOWANIA odpowiedzi (skąd dane, ile, ile maski).

BEZPIECZEŃSTWO (0G): stopka pokazuje WYŁĄCZNIE liczniki — nigdy wartości
sekretów ani pełnych danych PII. To czysta funkcja prezentacji.
"""

from __future__ import annotations

from typing import Any, Optional


def build_provenance_footer(
    odoo_version: Optional[Any] = None,
    n_records: Optional[int] = None,
    k_masked: Optional[int] = None,
) -> str:
    """Złóż stopkę provenance z dostępnych metryk (pomija nieznane segmenty).

    Zwraca "" gdy NIC nie wiadomo (brak odpytania Odoo / brak danych) — żeby nie
    doklejać pustej, mylącej stopki do czysto konwersacyjnych odpowiedzi.
    """
    parts = []
    if odoo_version not in (None, "", "unknown"):
        parts.append(f"Odoo {odoo_version}")
    if n_records is not None:
        parts.append(f"{n_records} rekordów")
    if k_masked is not None:
        parts.append(f"{k_masked} zamaskowanych")
    if not parts:
        return ""
    return "— źródło: " + " · ".join(parts)


def append_provenance(reply: str, footer: str) -> str:
    """Doklej stopkę do odpowiedzi (idempotentnie — nie dubluje)."""
    if not footer:
        return reply
    if footer in (reply or ""):
        return reply
    sep = "\n\n" if reply and not reply.endswith("\n") else ""
    return f"{reply}{sep}{footer}"


class ProvenanceAccumulator:
    """Zbiera metryki provenance w trakcie obsługi jednej tury czatu.

    - record() — z każdego wyniku narzędzia Odoo bierze 'count' (PRAWDZIWA liczba
      dopasowań, nie rozmiar strony — patrz mcp/server.py search_count).
    - masked_delta() — przyrost liczników PII w danym workspace (ile tokenów maski
      powstało podczas tej tury). Czyta tylko LICZNIKI (nie wartości).
    """

    def __init__(self, pii: Optional[Any] = None, workspace_id: str = "default"):
        self.pii = pii
        self.workspace_id = workspace_id
        self.n_records: Optional[int] = None
        self.odoo_version: Optional[Any] = None
        self._masked_baseline = self._current_masked_total()

    def _current_masked_total(self) -> int:
        if not self.pii:
            return 0
        counters = getattr(self.pii, "counters", {}) or {}
        ws = counters.get(self.workspace_id, {}) or {}
        try:
            return sum(int(v) for v in ws.values())
        except Exception:
            return 0

    def record_count(self, count: Optional[int]) -> None:
        """Zapamiętaj liczbę rekordów z wyniku narzędzia (bierze MAX widzianą)."""
        if isinstance(count, int):
            self.n_records = count if self.n_records is None else max(self.n_records, count)

    def set_version(self, version: Optional[Any]) -> None:
        if version not in (None, "", "unknown"):
            self.odoo_version = version

    def masked_delta(self) -> int:
        """Ile masek przybyło od początku tury (≥0)."""
        return max(0, self._current_masked_total() - self._masked_baseline)

    def footer(self) -> str:
        """Zbuduj stopkę — tylko gdy w ogóle dotknęliśmy danych Odoo (n_records znane)."""
        if self.n_records is None and self.odoo_version is None:
            return ""
        return build_provenance_footer(
            odoo_version=self.odoo_version,
            n_records=self.n_records,
            k_masked=self.masked_delta(),
        )
