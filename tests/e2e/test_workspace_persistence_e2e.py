"""E2E: BUG-1 — persystencja aktywnego workspace (US-UX8-1).

Reprodukuje i weryfikuje, że aktywny workspace jest zachowany:
  (a) po nawigacji między zakładkami (chat -> Projekt/settings -> chat),
  (b) po odświeżeniu strony (reload).

Root-cause BUG-1: `Store` trzymał stan tylko in-memory; reload tworzy nową
instancję z `workspaceId='default'`. Naprawa: persystencja w localStorage.

Wymaga żywego serwera na http://127.0.0.1:8000 (PIN: 1234).
Uruchom jawnie: pytest -m e2e tests/e2e/test_workspace_persistence_e2e.py
"""

from playwright.sync_api import Page, expect

from .conftest import login_to_dashboard, select_workspace

# Workspace inny niż 'default' — użyty do wykazania utraty/zachowania stanu.
TARGET_WS = "dev"


def _active_workspace(page: Page) -> str:
    return page.evaluate("() => window.AppStore.getState().workspaceId")


def test_workspace_persists_across_tab_navigation(page: Page):
    """(a) Nawigacja: chat -> Projekt -> chat NIE może gubić workspace."""
    login_to_dashboard(page)
    select_workspace(page, TARGET_WS)
    assert _active_workspace(page) == TARGET_WS

    # Nawigacja: do zakładki Projekt (settings) i z powrotem do Czatu
    page.locator("#tab-settings").click()
    expect(page.locator("#settings-screen")).to_be_visible(timeout=5000)
    page.locator("#tab-chat").click()
    expect(page.locator("#chat-screen")).to_be_visible(timeout=5000)

    assert (
        _active_workspace(page) == TARGET_WS
    ), "Workspace zgubiony przy nawigacji między zakładkami"


def test_workspace_persists_across_reload(page: Page):
    """(b) Reload: po odświeżeniu strony workspace musi zostać zachowany (BUG-1)."""
    login_to_dashboard(page)
    select_workspace(page, TARGET_WS)
    assert _active_workspace(page) == TARGET_WS

    # Odśwież stronę i przejdź ponownie przez logowanie (PIN nie jest persystowany — Sekcja D)
    login_to_dashboard(page)

    assert (
        _active_workspace(page) == TARGET_WS
    ), "Workspace zresetowany do 'default' po reloadzie (BUG-1: brak persystencji stanu)"
