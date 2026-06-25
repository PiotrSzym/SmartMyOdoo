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

import ast
import re
from typing import Any, Dict, Optional, Tuple

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


# TRUST-02 T2 (D2): sygnały, że user ŚWIADOMIE chce wyjść poza aktywny projekt
# (szukanie globalne). Wtedy NIE narzucamy filtra project_id.
_GLOBAL_HINTS = (
    "wszystk",
    "globaln",
    "w całej bazie",
    "we wszystkich projekt",
    "w systemie",
    "każd",
    "dowoln",
)


def _names_other_project(message: str) -> bool:
    """Czy user jawnie wskazuje (inny) projekt po słowie 'projekt/projekcie <coś>'."""
    return bool(re.search(r"\bprojek\w*\s+\S", (message or "").lower()))


def _is_task_query(tool_name: str, args: dict, message: str) -> bool:
    """Czy to wywołanie szukające ZADAŃ (project.task)."""
    model = str(args.get("model", "")).lower()
    if "project.task" in model:
        return True
    if "task" in (tool_name or "").lower():
        return True
    # brak jawnego modelu, ale pytanie wprost o zadania
    return model == "" and "zadan" in (message or "").lower()


class ConversationScope:
    """In-memory pamięć ostatniego zakresu (project_id) per (workspace, session)."""

    def __init__(self) -> None:
        # (workspace_id, session_id) -> {"project_id": int}
        self._scope: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # TRUST-03 T2 (Entity Memory): ostatnio POKAZANE rekordy per (ws, sess)
        # — lista {id, model, title}. Kotwica do disambiguacji nazw (price list↔cennik).
        self._records: Dict[Tuple[str, str], list] = {}

    def _key(self, workspace_id: str, session_id: str) -> Tuple[str, str]:
        return (workspace_id or "default", session_id or "")

    def capture_domain(
        self, workspace_id: str, session_id: str, domain: Any
    ) -> Optional[int]:
        """Zapamiętaj project_id z domeny zapytania (jeśli jest). Zwraca wyłuskany id.

        TRUST-03 T2: zmiana projektu → RESET pamięci pokazanych rekordów (US-T2b)."""
        pid = _extract_project_id(domain)
        if pid is not None:
            key = self._key(workspace_id, session_id)
            prev = self._scope.get(key, {}).get("project_id")
            if prev is not None and prev != pid:
                self._records.pop(key, None)  # inny projekt → kotwica nieaktualna
            self._scope[key] = {"project_id": pid}
        return pid

    def capture_records(
        self, workspace_id: str, session_id: str, model: str, records: Any
    ) -> int:
        """TRUST-03 T2: zapamiętaj pokazane rekordy (id+tytuł) dla danego modelu.

        Tytuły pochodzą z JUŻ zanonimizowanego wyniku narzędzia (bezpieczne dla LLM).
        Dedup po (model, id); trzymamy ostatnie 8. Zwraca liczbę dodanych/odświeżonych."""
        if not model or not isinstance(records, list):
            return 0
        key = self._key(workspace_id, session_id)
        bucket = self._records.setdefault(key, [])
        added = 0
        for r in records:
            if not isinstance(r, dict):
                continue
            rid = r.get("id")
            if rid is None:
                continue
            title = r.get("name") or r.get("display_name") or r.get("complete_name") or ""
            entry = {"id": rid, "model": str(model), "title": str(title)[:120]}
            bucket[:] = [
                e for e in bucket if not (e["id"] == rid and e["model"] == entry["model"])
            ]
            bucket.append(entry)
            added += 1
        if len(bucket) > 8:
            del bucket[:-8]
        return added

    def context_block(
        self, workspace_id: str, session_id: str
    ) -> Optional[str]:
        """TRUST-03 T2: kompaktowy blok 'aktywny kontekst' (projekt + pokazane rekordy)
        + reguła disambiguacji. None, gdy nie ma czego zakotwiczyć."""
        key = self._key(workspace_id, session_id)
        pid = self.get_project_id(workspace_id, session_id)
        records = self._records.get(key, [])
        if pid is None and not records:
            return None
        parts = ["[AKTYWNY KONTEKST ROZMOWY]"]
        if pid is not None:
            parts.append(f"Aktywny projekt: project_id={pid}.")
        if records:
            items = "; ".join(
                f'{e["model"]} id={e["id"]} „{e["title"]}"' for e in records[-8:]
            )
            parts.append(f"Ostatnio pokazane rekordy: {items}.")
            parts.append(
                "Gdy użytkownik odwołuje się nazwą pasującą do któregoś z powyższych "
                "rekordów, traktuj to jako odwołanie do TEGO rekordu (model+id), NIE do "
                "modelu Odoo o tej samej nazwie (np. „price list” = pokazane zadanie "
                "project.task, a nie model product.pricelist/cennik)."
            )
        return " ".join(parts)

    def get_project_id(
        self, workspace_id: str, session_id: str
    ) -> Optional[int]:
        entry = self._scope.get(self._key(workspace_id, session_id))
        return entry.get("project_id") if entry else None

    def clear(self, workspace_id: str, session_id: str) -> None:
        self._scope.pop(self._key(workspace_id, session_id), None)
        self._records.pop(self._key(workspace_id, session_id), None)

    # TRUST-03 T4: usunięto scope_hint/inject_hint (plaster TRUST-01 T5) — zastąpione
    # nadzbiorem `context_block` (T2) + deterministycznym `enforce_scope` (T2).

    def enforce_scope(
        self,
        workspace_id: str,
        session_id: str,
        tool_name: str,
        args: Any,
        message: str,
    ) -> bool:
        """TRUST-02 T2 (D2): DETERMINISTYCZNIE dokleja `project_id` aktywnego zakresu
        do domeny zapytania o zadania — nie polegając na dyscyplinie modelu.

        Mutuje `args["domain"]` IN-PLACE. Zwraca True, gdy doklejono filtr.
        Furtki (NIE narzuca): brak zapamiętanego project_id; to nie szukanie zadań;
        domena już ma project_id; user prosi o „wszystkie/globalnie" lub nazywa
        inny projekt. Działa też, gdy `domain` jest stringiem (składnia Pythona).
        """
        pid = self.get_project_id(workspace_id, session_id)
        if pid is None or not isinstance(args, dict):
            return False
        if not isinstance(tool_name, str) or "search" not in tool_name:
            return False
        if not _is_task_query(tool_name, args, message):
            return False
        low = (message or "").lower()
        if any(h in low for h in _GLOBAL_HINTS) or _names_other_project(low):
            return False

        domain = args.get("domain")
        was_str = isinstance(domain, str)
        parsed: Any = domain
        if was_str:
            try:
                parsed = ast.literal_eval(domain)
            except Exception:
                return False
        if parsed is None:
            parsed = []
        if not isinstance(parsed, (list, tuple)):
            return False
        if _extract_project_id(parsed) is not None:
            return False  # user/model już zawęził projekt — nie ruszamy

        new_domain = list(parsed) + [("project_id", "=", pid)]
        args["domain"] = str(new_domain) if was_str else new_domain
        return True
