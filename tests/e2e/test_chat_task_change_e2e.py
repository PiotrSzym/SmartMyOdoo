"""E2E: T3 — zmiana zadania z nagłówka czatu (US-UX8-3).

„Zmień" przy badge → wspólny Task Picker → wybór → PUT /task_bind → badge odświeżony.
Reużywa wyekstrahowanego pickera (taskPicker.js), wspólnego z zakładką Projekt.

Wymaga żywego serwera http://127.0.0.1:8000 (PIN: 1234) z workspace 'default'
mającym przypisany projekt Odoo (project_ref) i działającym połączeniem Odoo.

Uruchom jawnie: pytest -m e2e tests/e2e/test_chat_task_change_e2e.py
"""

import pytest
from playwright.sync_api import Page, expect

from .conftest import login_to_dashboard, select_workspace


def test_change_task_from_chat_badge(page: Page):
    """Otwiera picker z czatu, wybiera zadanie, weryfikuje zapis bindu i odświeżenie badge."""
    login_to_dashboard(page)
    page.wait_for_function(
        "() => (window.AppSidebar && window.AppSidebar.workspaces || []).length > 0",
        timeout=5000,
    )
    select_workspace(page, "default")

    has_project = page.evaluate(
        "() => { const w=(window.AppSidebar.workspaces||[]).find(x=>x.id==='default'); "
        "return !!(w && w.project_ref); }"
    )
    if not has_project:
        pytest.skip(
            "Workspace 'default' nie ma przypisanego projektu — pomijam zmianę zadania."
        )

    page.locator("#tab-chat").click()
    expect(page.locator("#chat-screen")).to_be_visible(timeout=5000)

    # Klik „Zmień" przy badge → otwiera wspólny Task Picker (overlay).
    expect(page.locator("#chat-task-change-btn")).to_be_visible(timeout=5000)
    page.locator("#chat-task-change-btn").click()

    overlay = page.locator("#task-picker-overlay")
    expect(overlay).to_be_visible(timeout=5000)

    # Lista zadań ładowana z Odoo — czekamy aż pojawi się klikalny przycisk zadania.
    first_task = page.locator("#task-picker-list button[data-task-id]").first
    try:
        expect(first_task).to_be_visible(timeout=15000)
    except AssertionError:
        pytest.skip("Brak zadań z Odoo (połączenie/dane) — pomijam wybór.")

    chosen_task_id = first_task.get_attribute("data-task-id")
    first_task.click()

    # Po wyborze: PUT /task_bind → sidebar przeładowany → workspace ma nowe task_ref.
    page.wait_for_function(
        "(tid) => { const w=(window.AppSidebar.workspaces||[]).find(x=>x.id==='default'); "
        "return !!(w && String(w.task_ref) === String(tid)); }",
        arg=chosen_task_id,
        timeout=10000,
    )

    # Overlay zamknięty, badge odświeżony (zawiera separator projekt › zadanie).
    expect(overlay).to_be_hidden(timeout=5000)
    badge = page.locator("#chat-task-badge")
    expect(badge).to_contain_text("›", timeout=5000)
