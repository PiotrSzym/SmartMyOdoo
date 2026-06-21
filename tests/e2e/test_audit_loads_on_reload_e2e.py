"""E2E: UX-10 — audyt ładuje się po reloadzie na zakładce Aktywność (US-UX10-1/2).

Symetryczny do test_vault_loads_on_reload_e2e.py, ale dla panelu Aktywność (audyt):
gdy reload ląduje wprost na zakładce 'activity' (UX-08 — persystencja `activeTab`),
`activity.js` ładował dane TYLKO na PRZEJŚCIU activeTab → po zalogowaniu na przywróconej
zakładce panel zostawał pusty (brak retry-on-auth).

Naprawa (UX-10 T3/T4): `activity.js` subskrybuje `isAuthenticated` i wywołuje
`loadFromAPI()` gdy zakładka Aktywność jest aktywna po loginie (parytet z chat.js:25).

Strategia (network spy, jak w test_auth_ready_loading_e2e.py): wstrzykujemy
localStorage['smartmyodoo.ui'] z activeTab='activity' PRZED bootstrapem store.js,
przeładowujemy, logujemy się i sprawdzamy, że PO loginie pojawia się `GET /api/audit`
ze statusem 200 (panel SAM odpytał z tokenem), bez osieroconych 401.

BUG #2 (luka pokrycia /qa): wcześniej istniał tylko test reload-on-settings (vault);
brak symetrycznego reload-on-activity. Ten test domyka pokrycie i ma MOC DOWODOWĄ
(network event renderu JS, nie statyczny DOM).

Wymaga żywego serwera na http://127.0.0.1:8000 (PIN: 1234).
Uruchom jawnie: pytest -m e2e tests/e2e/test_audit_loads_on_reload_e2e.py
"""

import json

from playwright.sync_api import Page, expect

from .conftest import BASE_URL, login_to_dashboard

# Stan UX-08 do wstrzyknięcia: użytkownik był na Aktywności, workspace 'default'.
_PERSISTED_UI = {"workspaceId": "default", "activeTab": "activity", "lang": "pl"}


def test_audit_loads_after_login_on_restored_activity_tab(page: Page):
    """US-UX10-2: reload z activeTab='activity' → po loginie audyt sam się ładuje (200)."""
    # Spy sieciowy MUSI być podpięty zanim nastąpi login na przywróconej zakładce.
    audit_statuses: list[int] = []
    page.on(
        "response",
        lambda r: audit_statuses.append(r.status) if "/api/audit" in r.url else None,
    )

    # Pierwsza wizyta + login (init skarbca / ustalona sesja).
    login_to_dashboard(page)

    # Wstrzyknij stan UX-08 ZANIM store.js wystartuje przy następnej nawigacji.
    page.add_init_script(
        f"window.localStorage.setItem('smartmyodoo.ui', '{json.dumps(_PERSISTED_UI)}');"
    )

    # Reload — store boota z activeTab='activity', ekran logowania wraca (token w pamięci).
    page.goto(BASE_URL)

    # Od tego momentu liczą się odpowiedzi /api/audit wywołane PO loginie (retry-on-auth).
    audit_statuses.clear()

    # RELEASE-01 T3 (deterministyczne e2e, UX-10 pattern): zamiast magicznego sleepa
    # czekamy DETERMINISTYCZNIE na odpowiedź /api/audit wywołaną retry-on-auth po loginie.
    # `expect_response` zamyka okno wyścigu (login → loadFromAPI → authFetch('/api/audit'))
    # bez magicznego sleepa — kończy dokładnie gdy odpowiedź dotrze.
    with page.expect_response(lambda r: "/api/audit" in r.url, timeout=15000):
        login_to_dashboard(page)

    # Po zalogowaniu na przywróconej zakładce Aktywność — panel MUSI być widoczny.
    expect(page.locator("#activity-screen")).to_be_visible(timeout=5000)

    # MOC DOWODOWA (network event renderu JS): retry-on-auth → loadFromAPI() →
    # authFetch('/api/audit'). Marker renderu JS: nagłówek `.text-gradient` istnieje
    # TYLKO po render() (loadFromAPI→render). Timeout 12s pokrywa zimny start chromium
    # na /mnt/c (WSL2). Bez magicznego sleepa — `expect_response` wyżej już domknął /api/audit.
    expect(page.locator("#activity-screen .text-gradient")).to_be_visible(timeout=12000)

    # (1) NETWORK SPY: audyt MUSI odpytać API po loginie (z tokenem, 200).
    assert audit_statuses, (
        "Po loginie na przywróconej zakładce Aktywność /api/audit NIE zostało "
        "wywołane — audyt nie odpytał API (brak retry-on-auth → render się nie odpalił)"
    )
    assert 200 in audit_statuses, (
        f"/api/audit nie zwróciło 200 po loginie na przywróconej zakładce Aktywność "
        f"(statusy: {audit_statuses}) — audyt odpytał bez ważnego tokenu / nie ponowił"
    )
    assert 401 not in audit_statuses, (
        f"/api/audit zwróciło 401 po zalogowaniu (statusy: {audit_statuses}) "
        f"— osierocony 401 (fetch przed ustawieniem tokenu, brak retry-on-auth)"
    )
