"""ERR-01: klasyfikacja błędów Odoo na KONKRETNE, actionable komunikaty.

Problem (zgłoszenie usera): narzędzia Odoo łapały każdy wyjątek i zwracały generyczne
„Wystąpił błąd… Szczegóły w logach systemowych”. Prawdziwa przyczyna („Błąd autoryzacji”,
„Odoo nieosiągalne”, „Brak uprawnień do modelu”) zostawała TYLKO w logu → model jej nie
widział → ZGADYWAŁ przyczyny (konfabulacja). Tu mapujemy typ wyjątku na komunikat, który
mówi PRAWDĘ i podpowiada następny krok — spójne z motywem TRUST (prawda także o awariach).
"""

from __future__ import annotations

import socket
import xmlrpc.client

# OdooFieldError żyje w odoo_client; import lokalny w funkcji, by uniknąć cyklu.


def classify_odoo_error(exc: Exception, *, workspace_id: str | None = None) -> str:
    """Zmapuj wyjątek z warstwy Odoo na konkretny komunikat dla użytkownika/modelu.

    Zwraca gotowy string „❌ …” z przyczyną i sugestią działania. NIE ujawnia sekretów
    (tylko nazwa przestrzeni i kategoria błędu)."""
    ws = f" (przestrzeń „{workspace_id}”)" if workspace_id else ""
    msg = str(exc) or ""
    low = msg.lower()

    # 1. Brak konfiguracji (creds nie wstrzyknięte / niekompletne) — ValueError z connect()
    if isinstance(exc, ValueError) and "brak konfiguracji" in low:
        return (
            f"❌ Brak konfiguracji Odoo{ws}. Poświadczenia nie zostały wczytane ze "
            "Skarbca — sprawdź, czy ta przestrzeń ma kompletny wpis Odoo (URL, baza, "
            "login, hasło/klucz API)."
        )

    # 2. Błąd autoryzacji — PermissionError z connect() (authenticate→False)
    if isinstance(exc, PermissionError) or "błąd autoryzacji" in low or "authenticate" in low:
        return (
            f"❌ Błąd autoryzacji do Odoo{ws}. Najczęstsze przyczyny: (a) środowisko "
            "staging odoo.sh WYBUDZA SIĘ z uśpienia — spróbuj ponownie za chwilę; "
            "(b) poświadczenia API wygasły/są błędne — odśwież je w Skarbcu."
        )

    # 3. Pole nie istnieje w tej wersji modelu — OdooFieldError (ma już konkretny komunikat)
    try:
        from smartmyodoo.mcp.odoo_client import OdooFieldError

        if isinstance(exc, OdooFieldError):
            return f"❌ {msg}"
    except Exception:  # noqa: BLE001 — import nieistotny przy braku modułu
        pass

    # 4. Timeout — instancja nie odpowiada (często staging w trakcie wybudzania)
    if isinstance(exc, (socket.timeout, TimeoutError)) or "timed out" in low or "timeout" in low:
        return (
            f"❌ Odoo nie odpowiada (timeout){ws}. Instancja staging mogła się wybudzać "
            "lub jest przeciążona — spróbuj ponownie za chwilę."
        )

    # 5. Błąd serwera Odoo (XML-RPC Fault) — uprawnienia / walidacja / brak modelu
    if isinstance(exc, xmlrpc.client.Fault):
        fault = (getattr(exc, "faultString", "") or msg)
        fl = fault.lower()
        first = fault.strip().splitlines()[-1].strip() if fault.strip() else ""
        if "accesserror" in fl or "access denied" in fl or "not allowed" in fl or "ir.rule" in fl:
            return (
                f"❌ Brak uprawnień w Odoo{ws} (AccessError) — użytkownik API nie ma "
                "praw do tego modelu/operacji. Sprawdź grupy dostępu i Record Rules."
            )
        if "validationerror" in fl or "usererror" in fl:
            return f"❌ Odoo odrzucił operację (walidacja): {first[:200]}"
        if "doesn't exist" in fl or "does not exist" in fl or "keyerror" in fl:
            return f"❌ Odoo: model lub pole nie istnieje — {first[:200]}"
        return f"❌ Odoo zgłosił błąd: {first[:200]}"

    # 6. Sieć / nieosiągalny serwer (zła wartość URL, DNS, odmowa połączenia)
    if isinstance(exc, (ConnectionError, xmlrpc.client.ProtocolError, socket.gaierror, OSError)):
        return (
            f"❌ Odoo nieosiągalne{ws} (problem sieci/URL). Sprawdź adres instancji "
            "w Skarbcu i połączenie z internetem."
        )

    # 7. Fallback — nieznany błąd: pokaż TYP + skrót, bez „szczegóły w logach”
    return (
        f"❌ Nieoczekiwany błąd Odoo{ws}: {type(exc).__name__}: {msg[:160]}"
        if msg
        else f"❌ Nieoczekiwany błąd Odoo{ws}: {type(exc).__name__}."
    )
