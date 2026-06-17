"""Oznacza testy w tests/e2e/ markerem `e2e`.

Testy e2e (Playwright) wymagają żywego serwera + chromium i używają sync API Playwright,
które trzyma własną pętlę zdarzeń. Bez izolacji psuły kolejne testy async w pełnym przebiegu
(`RuntimeError: Runner.run() cannot be called from a running event loop`).
Domyślnie wykluczone przez `addopts = "-m 'not e2e'"`. Uruchom jawnie: `pytest -m e2e`.
"""

import pathlib

import pytest

_E2E_DIR = pathlib.Path(__file__).parent.resolve()

BASE_URL = "http://127.0.0.1:8000"
PIN = "1234"


def login_to_dashboard(page, *, pin: str = PIN):
    """Wspólny, odporny na timing helper logowania (UX-08 E2E).

    Czeka jawnie na pojawienie się ekranów (init/login), zamyka modal zmiany PIN-u
    (admin) i potwierdza dashboard. Współdzielony przez testy persystencji/badge/zmiany
    zadania (DRY) — eliminuje wyścig „is_visible() zanim ekran się wyrenderuje".
    """
    from playwright.sync_api import expect

    page.goto(BASE_URL)
    # Poczekaj aż window.onload zdecyduje o ekranie startowym (init lub login).
    page.wait_for_function(
        "() => { const i=document.getElementById('init-screen');"
        " const l=document.getElementById('login-screen');"
        " const d=document.getElementById('dashboard-screen');"
        " return (i && !i.classList.contains('hidden')) ||"
        "        (l && !l.classList.contains('hidden')) ||"
        "        (d && !d.classList.contains('hidden')); }",
        timeout=10000,
    )

    if page.locator("#init-master").is_visible():
        page.locator("#init-master").fill("testmaster")
        page.locator("#init-pin").fill(pin)
        page.locator("button:has-text('Stwórz Skarbiec')").click()
        expect(page.locator("#init-screen")).to_be_hidden(timeout=5000)

    if page.locator("#auth-password").is_visible():
        page.locator("#auth-password").fill(pin)
        page.locator("button:has-text('Odblokuj')").click()
        expect(page.locator("#login-screen")).to_be_hidden(timeout=10000)

    # Modal zmiany PIN-u (admin) pojawia się asynchronicznie po loginie — zamknij gdy jest.
    try:
        page.locator("#pin-modal button", has_text="✕").click(timeout=2000)
        expect(page.locator("#pin-modal")).to_be_hidden(timeout=3000)
    except Exception:
        pass

    expect(page.locator("#dashboard-screen")).to_be_visible(timeout=10000)


def select_workspace(page, ws_id: str):
    """Klika workspace w sidebarze i potwierdza zapis w stanie."""
    from playwright.sync_api import expect

    btn = page.locator(f'.ws-item[data-ws-id="{ws_id}"] button').first
    expect(btn).to_be_visible(timeout=5000)
    btn.click()
    page.wait_for_function(
        "(ws) => window.AppStore.getState().workspaceId === ws", arg=ws_id, timeout=5000
    )


def pytest_collection_modifyitems(config, items):
    # Hook jest wołany sesyjnie (items = WSZYSTKIE testy) — oznacz tylko te z tego katalogu.
    for item in items:
        try:
            item_path = pathlib.Path(str(item.fspath)).resolve()
        except Exception:
            continue
        if _E2E_DIR == item_path.parent or _E2E_DIR in item_path.parents:
            item.add_marker(pytest.mark.e2e)
