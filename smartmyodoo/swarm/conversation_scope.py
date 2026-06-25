"""TRUST-01 T5 (decyzja D5): pamięć ZAKRESU rozmowy między turami.

Realny bug (sesja 2026-06-25): po "ile zadań w projekcie rmo" (project_id=136,
wynik 2) pytanie follow-up "jakie opisy w zadaniach" zwracało 2920 (WSZYSTKIE
zadania), bo model GUBIŁ filtr project_id między turami.

Rozwiązanie (KISS, bez nowych endpointów): lekki tracker per (workspace, session),
który:
  1) wyłapuje ostatni `project_id` użyty w domenie zapytania Odoo (capture_domain),
  2) na kolejnej turze podpowiada modelowi, by ZACHOWAŁ ten zakres, gdy pytanie
     jest follow-upem (scope_hint).

Tracker jest in-memory (jak liczniki PII) — stan rozmowy, nie dane wrażliwe.
NIE przechowuje wartości PII, tylko techniczny identyfikator rekordu (project_id).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Słowa-sygnały follow-upu: pytanie nawiązujące do "tych samych" zadań bez
# nazwania NOWEGO projektu. Świadomie wąskie, by nie nadpisywać świeżego zakresu.
_FOLLOWUP_HINTS = (
    "opis",
    "opisy",
    "a w nich",
    "w tych",
    "tych zadań",
    "te zadania",
    "ich ",
    "szczegół",
    "więcej o nich",
    "a jakie",
)


def _extract_project_id(domain: Any) -> Optional[int]:
    """Wyłuskaj project_id z domeny Odoo (lista krotek/list), jeśli obecny.

    Obsługuje [("project_id","=",136)] oraz [["project_id","=",136]].
    """
    if not isinstance(domain, (list, tuple)):
        return None
    for clause in domain:
        if (
            isinstance(clause, (list, tuple))
            and len(clause) == 3
            and clause[0] == "project_id"
            and clause[1] in ("=", "in")
        ):
            val = clause[2]
            if isinstance(val, bool):
                return None
            if isinstance(val, int):
                return val
            if isinstance(val, (list, tuple)) and val and isinstance(val[0], int):
                return val[0]
            if isinstance(val, str) and val.isdigit():
                return int(val)
    return None


def _is_followup(message: str) -> bool:
    low = (message or "").lower()
    # Jeśli user jawnie nazywa nowy projekt po "projekt/projekcie ..." — to NIE follow-up.
    if re.search(r"\bprojek\w*\s+\w", low):
        # ...chyba że to po prostu "w zadaniach tego projektu" — ale wtedy nie ma
        # nowej NAZWY; zostawiamy heurystyce sygnałów poniżej.
        pass
    return any(h in low for h in _FOLLOWUP_HINTS)


class ConversationScope:
    """In-memory pamięć ostatniego zakresu (project_id) per (workspace, session)."""

    def __init__(self) -> None:
        # (workspace_id, session_id) -> {"project_id": int}
        self._scope: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def _key(self, workspace_id: str, session_id: str) -> Tuple[str, str]:
        return (workspace_id or "default", session_id or "")

    def capture_domain(
        self, workspace_id: str, session_id: str, domain: Any
    ) -> Optional[int]:
        """Zapamiętaj project_id z domeny zapytania (jeśli jest). Zwraca wyłuskany id."""
        pid = _extract_project_id(domain)
        if pid is not None:
            self._scope[self._key(workspace_id, session_id)] = {"project_id": pid}
        return pid

    def get_project_id(
        self, workspace_id: str, session_id: str
    ) -> Optional[int]:
        entry = self._scope.get(self._key(workspace_id, session_id))
        return entry.get("project_id") if entry else None

    def clear(self, workspace_id: str, session_id: str) -> None:
        self._scope.pop(self._key(workspace_id, session_id), None)

    def scope_hint(
        self, workspace_id: str, session_id: str, message: str
    ) -> Optional[str]:
        """Podpowiedź systemowa dla modelu, gdy bieżące pytanie jest follow-upem.

        Zwraca None, gdy brak zapamiętanego zakresu lub pytanie nie jest follow-upem
        — wtedy nie narzucamy filtra (np. user pyta o zupełnie inny projekt).
        """
        pid = self.get_project_id(workspace_id, session_id)
        if pid is None or not _is_followup(message):
            return None
        return (
            f"[KONTEKST ROZMOWY] Poprzednie pytanie dotyczyło projektu o "
            f"project_id={pid}. To pytanie jest jego kontynuacją — przy zapytaniach o "
            f"zadania ZACHOWAJ filtr domeny [(\"project_id\", \"=\", {pid})], "
            f"chyba że użytkownik wyraźnie wskaże inny projekt."
        )

    def inject_hint(
        self,
        workspace_id: str,
        session_id: str,
        message: str,
        messages: List[dict],
    ) -> List[dict]:
        """Wstaw scope_hint jako dodatkową wiadomość systemową (jeśli dotyczy).

        Bezpieczny dla istniejącej listy `messages` — zwraca tę samą listę.
        """
        hint = self.scope_hint(workspace_id, session_id, message)
        if hint:
            # Po głównym prompcie systemowym (indeks 0), przed historią/userem.
            insert_at = 1 if messages and messages[0].get("role") == "system" else 0
            messages.insert(insert_at, {"role": "system", "content": hint})
        return messages
