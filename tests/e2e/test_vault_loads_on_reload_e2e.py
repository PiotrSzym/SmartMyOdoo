"""E2E: UX-10 — vault renderuje po reloadzie na zakładce Skarbiec (US-UX10-2).

Reprodukuje interakcję z UX-08 (persystencja `activeTab` w localStorage):
gdy reload ląduje wprost na zakładce 'settings' (Skarbiec), render vault odpalał się
TYLKO na PRZEJŚCIU activeTab → po zalogowaniu panel zostawał pusty (żaden
`#project-state-*` nie był widoczny).

Naprawa (UX-10 T2/T4): `project.js` przy retry-on-auth sprawdza `activeTab==='settings'`
i renderuje przywróconą zakładkę mimo braku zdarzenia przejścia.

Strategia: wstrzykujemy localStorage['smartmyodoo.ui'] z activeTab='settings' PRZED
bootstrapem store.js (add_init_script biegnie przed skryptami strony), przeładowujemy,
logujemy się i sprawdzamy, że vault wyrenderował jeden ze stanów (STAN 1/2/3 widoczny).

Wymaga żywego serwera na http://127.0.0.1:8000 (PIN: 1234).
Uruchom jawnie: pytest -m e2e tests/e2e/test_vault_loads_on_reload_e2e.py
"""

import json

from playwright.sync_api import Page, expect

from .conftest import BASE_URL, login_to_dashboard

# Stan UX-08 do wstrzyknięcia: użytkownik był na Skarbcu, workspace 'default'.
_PERSISTED_UI = {"workspaceId": "default", "activeTab": "settings", "lang": "pl"}


def test_vault_renders_after_login_on_restored_settings_tab(page: Page):
    """US-UX10-2: reload z activeTab='settings' → po loginie vault się renderuje.

    MOC DOWODOWA (UX-10 /qa fix BUG #1): poprzednia asercja `!hidden` była wydmuszką —
    `#project-state-1` startuje w statycznym HTML z `class="glass-card p-6 block"` (BEZ
    `hidden`), więc `!hidden` był spełniony zanim JS cokolwiek wyrenderował. Test
    przechodził NAWET z wyłączonym retry-on-auth.

    Naprawiona asercja sprawdza EFEKT RENDERU JS, nie statyczny DOM, na DWÓCH niezależnych
    osiach (wzorzec z test_auth_ready_loading_e2e.py):
      (1) NETWORK SPY: po loginie vault SAM odpytuje `GET /api/secrets` (status 200,
          zero osieroconych 401) — dowód, że retry-on-auth odpalił renderProjectTab().
      (2) MARKER RENDERU: `showState()` (project.js:45) dokłada klasę `flex` aktywnemu
          stanowi i usuwa statyczne `block` — `flex` istnieje TYLKO po renderze JS.
    """
    # Spy sieciowy MUSI być podpięty zanim nastąpi login na przywróconej zakładce.
    secrets_statuses: list[int] = []
    page.on(
        "response",
        lambda r: (
            secrets_statuses.append(r.status) if "/api/secrets" in r.url else None
        ),
    )

    # Pierwsza wizyta + login, by mieć utworzony skarbiec (init) i ustaloną sesję.
    login_to_dashboard(page)

    # Wstrzyknij stan UX-08 ZANIM store.js wystartuje przy następnej nawigacji.
    page.add_init_script(
        f"window.localStorage.setItem('smartmyodoo.ui', '{json.dumps(_PERSISTED_UI)}');"
    )

    # Reload — store boota z activeTab='settings', ekran logowania wraca (token w pamięci).
    page.goto(BASE_URL)

    # Od tego momentu liczą się odpowiedzi /api/secrets wywołane PO loginie (retry-on-auth).
    secrets_statuses.clear()
    login_to_dashboard(page)

    # Po zalogowaniu na przywróconej zakładce Skarbiec — vault MUSI się wyrenderować.
    # Świeży login bez creds Odoo → STAN 1 (formularz credentials) jest stanem widocznym.
    expect(page.locator("#settings-screen")).to_be_visible(timeout=5000)

    # (2) MARKER RENDERU: czekaj aż któryś #project-state-* dostanie klasę `flex` od showState().
    #     Statyczny HTML ma `block` (state-1) lub `flex-col` (state-2/3), ale NIGDY `flex` —
    #     ta klasa pojawia się WYŁĄCZNIE przez renderProjectTab()→showState() (render JS).
    # Timeout 12s (nie 8s): gdy ten test sortuje się jako pierwszy w przebiegu e2e,
    # zimny start chromium+serwera na /mnt/c (WSL2) bywa wolniejszy niż 8s (flake /qa UX-10).
    page.wait_for_function(
        "() => [1,2,3].some(n => {"
        "  const el = document.getElementById('project-state-' + n);"
        "  return el && el.classList.contains('flex');"
        "})",
        timeout=12000,
    )

    rendered_states = page.evaluate(
        "() => [1,2,3].filter(n => {"
        "  const el = document.getElementById('project-state-' + n);"
        "  return el && el.classList.contains('flex');"
        "})"
    )
    assert rendered_states, (
        "Żaden #project-state-* nie ma klasy `flex` po loginie na przywróconej "
        "zakładce Skarbiec — renderProjectTab()/showState() NIE odpalił (brak "
        "retry-on-auth dla przywróconej activeTab). Statyczny `block` NIE liczy się "
        "jako render."
    )

    # (1) NETWORK SPY: retry-on-auth → renderProjectTab() → authFetch('/api/secrets').
    #     Vault MUSI odpytać sekrety SAM po loginie (z tokenem) — to dowód, że fetch
    #     odpalił render, a nie statyczny DOM.
    assert secrets_statuses, (
        "Po loginie na przywróconej zakładce Skarbiec /api/secrets NIE zostało "
        "wywołane — vault nie odpytał sejfu (brak retry-on-auth → render się nie odpalił)"
    )
    assert 401 not in secrets_statuses, (
        f"/api/secrets zwróciło 401 po zalogowaniu (statusy: {secrets_statuses}) "
        f"— osierocony 401 (fetch przed ustawieniem tokenu, brak retry-on-auth)"
    )
    assert 200 in secrets_statuses, (
        f"/api/secrets nie zwróciło 200 po zalogowaniu (statusy: {secrets_statuses}) "
        f"— vault odpytał bez ważnego tokenu"
    )
