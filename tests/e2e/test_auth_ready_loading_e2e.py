"""E2E: UX-10 — auth-ready loading (US-UX10-1, US-UX10-3).

Reprodukuje i weryfikuje, że po zalogowaniu panele danych (vault/secrets, audyt)
SAME się ładują — bez ręcznego klikania w zakładkę i bez osieroconych 401.

Root-cause: `project.js` (vault) i `activity.js` (audyt) NIE subskrybowały
`isAuthenticated`, więc fetch wystrzelony przed loginem (401) nie był ponawiany.
Naprawa (UX-10 T2/T3): retry-on-auth (parytet ze sidebar.js:18 / chat.js:25).

Strategia: monitorujemy odpowiedzi sieciowe `/api/secrets` i `/api/audit` i sprawdzamy,
że PO zalogowaniu pojawia się odpowiedź 200 (panel sam odpytał z tokenem), oraz że
żadne `/api/secrets`/`/api/audit` nie zostaje z osieroconym 401 (bez następującego 200).

Wymaga żywego serwera na http://127.0.0.1:8000 (PIN: 1234).
Uruchom jawnie: pytest -m e2e tests/e2e/test_auth_ready_loading_e2e.py
"""

from playwright.sync_api import Page, expect

from .conftest import login_to_dashboard


def test_secrets_load_after_login_without_manual_click(page: Page):
    """US-UX10-1: po loginie wejście na Skarbiec → vault renderuje, bez osieroconego 401.

    Kontrakt: po wejściu na Skarbiec panel SAM się populuje (któryś `#project-state-*`
    widoczny), a jeśli odpyta `/api/secrets`, to z tokenem → 200 (nigdy osierocone 401).
    Izolacja: ścieżka renderu zależy od stanu workspace (STAN 1/2 woła /api/secrets,
    STAN 3 = projekt już związany — woła zadania); dlatego 200 sprawdzamy warunkowo,
    a niezmiennikiem jest: render + ZERO 401.
    """
    login_to_dashboard(page)

    # Zbieramy statusy odpowiedzi dla /api/secrets od momentu, gdy jesteśmy zalogowani.
    secrets_statuses: list[int] = []
    page.on(
        "response",
        lambda r: (
            secrets_statuses.append(r.status) if "/api/secrets" in r.url else None
        ),
    )

    # Wejście na zakładkę Skarbiec/Projekt — vault musi sam się wyrenderować (z tokenem).
    page.locator("#tab-settings").click()
    expect(page.locator("#settings-screen")).to_be_visible(timeout=5000)

    # MOC DOWODOWA (UX-10 /qa fix BUG #1b): asercja na MARKER RENDERU JS, nie statyczny DOM.
    # `!hidden` było wydmuszką (state-1 startuje z `block`, bez `hidden`). Klasa `flex`
    # pojawia się WYŁĄCZNIE przez showState() (project.js:45) — dowód renderu JS.
    # Timeout 12s (nie 8s): pierwszy e2e w przebiegu odpala zimny start chromium+serwera
    # na /mnt/c (WSL2) — render JS bywa wolniejszy niż 8s przy cold-startcie (flake /qa UX-10).
    page.wait_for_function(
        "() => [1,2,3].some(n => {"
        "  const el = document.getElementById('project-state-' + n);"
        "  return el && el.classList.contains('flex');"
        "})",
        timeout=12000,
    )
    page.wait_for_timeout(500)  # domknij ewentualne /api/secrets

    rendered_states = page.evaluate(
        "() => [1,2,3].filter(n => {"
        "  const el = document.getElementById('project-state-' + n);"
        "  return el && el.classList.contains('flex');"
        "})"
    )
    assert rendered_states, (
        "Żaden #project-state-* nie ma klasy `flex` — renderProjectTab()/showState() "
        "nie odpalił (statyczny `block` NIE liczy się jako render)"
    )

    # Niezmiennik: gdy vault odpytał sekrety, to z tokenem (200), nigdy osierocone 401.
    assert 401 not in secrets_statuses, (
        f"/api/secrets zwróciło 401 po zalogowaniu (statusy: {secrets_statuses}) "
        f"— osierocony 401 (brak retry-on-auth)"
    )
    if secrets_statuses:  # jeśli ścieżka renderu wołała sekrety — musi być 200
        assert 200 in secrets_statuses, (
            f"/api/secrets nie zwróciło 200 (statusy: {secrets_statuses}) "
            f"— vault odpytał bez ważnego tokenu"
        )


def test_audit_loads_after_login_on_activity_tab(page: Page):
    """US-UX10-1: po loginie wejście na Aktywność → /api/audit odpowiada 200."""
    login_to_dashboard(page)

    audit_statuses: list[int] = []
    page.on(
        "response",
        lambda r: audit_statuses.append(r.status) if "/api/audit" in r.url else None,
    )

    page.locator("#tab-activity").click()
    expect(page.locator("#activity-screen")).to_be_visible(timeout=5000)
    page.wait_for_timeout(1500)

    assert 200 in audit_statuses, (
        f"/api/audit nie odpowiedziało 200 po wejściu na Aktywność "
        f"(statusy: {audit_statuses})"
    )
    assert 401 not in audit_statuses, (
        f"/api/audit zwróciło 401 po zalogowaniu (statusy: {audit_statuses})"
    )
