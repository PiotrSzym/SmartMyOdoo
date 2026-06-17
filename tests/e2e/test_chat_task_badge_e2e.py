"""E2E: T2 — badge zadania w nagłówku czatu (US-UX8-2).

Workspace z przypisanym zadaniem → nagłówek czatu pokazuje `Projekt › Zadanie`.
Workspace bez zadania → badge pokazuje „Brak zadania".

Korzysta z workspace 'default' (na żywym serwerze ma project_ref/task_ref)
oraz 'dev' (bez bindu). Wymaga żywego serwera http://127.0.0.1:8000 (PIN: 1234).

Uruchom jawnie: pytest -m e2e tests/e2e/test_chat_task_badge_e2e.py
"""

from playwright.sync_api import Page, expect

from .conftest import login_to_dashboard, select_workspace


def _wait_sidebar(page: Page) -> None:
    page.wait_for_function(
        "() => (window.AppSidebar && window.AppSidebar.workspaces || []).length > 0",
        timeout=5000,
    )


def _ws_has_task(page: Page, ws_id: str) -> bool:
    return page.evaluate(
        "(ws) => { const w=(window.AppSidebar.workspaces||[]).find(x=>x.id===ws); "
        "return !!(w && w.task_ref); }",
        ws_id,
    )


def test_chat_header_shows_task_badge_for_bound_workspace(page: Page):
    """Workspace 'default' z bindem → badge pokazuje project_name › task_name."""
    login_to_dashboard(page)
    _wait_sidebar(page)
    select_workspace(page, "default")
    page.locator("#tab-chat").click()
    expect(page.locator("#chat-screen")).to_be_visible(timeout=5000)

    badge = page.locator("#chat-task-badge")
    expect(badge).to_be_visible(timeout=5000)

    if _ws_has_task(page, "default"):
        # Badge musi pokazać aktualne project_name › task_name (czeka na re-render po danych sidebaru).
        names = page.evaluate(
            "() => { const w=(window.AppSidebar.workspaces||[]).find(x=>x.id==='default'); "
            "return [w.project_name, w.task_name]; }"
        )
        expect(badge).to_contain_text("›", timeout=5000)
        expect(badge).to_contain_text(names[0], timeout=5000)
        expect(badge).to_contain_text(names[1], timeout=5000)


def test_chat_header_shows_no_task_for_unbound_workspace(page: Page):
    """Workspace 'dev' bez bindu → badge pokazuje „Brak zadania"."""
    login_to_dashboard(page)
    _wait_sidebar(page)
    select_workspace(page, "dev")
    page.locator("#tab-chat").click()
    expect(page.locator("#chat-screen")).to_be_visible(timeout=5000)

    badge = page.locator("#chat-task-badge")
    expect(badge).to_be_visible(timeout=5000)

    if not _ws_has_task(page, "dev"):
        expect(badge).to_contain_text("Brak zadania")
