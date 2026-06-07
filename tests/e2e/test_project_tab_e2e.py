from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:8000"


def test_project_tab_dual_state(page: Page):
    """
    Weryfikuje dwustanowy widok zakładki Projekt.
    """
    page.goto(BASE_URL)

    # Inicjalizacja/logowanie
    if page.locator("#init-master").is_visible():
        page.locator("#init-master").fill("testmaster")
        page.locator("#init-pin").fill("1234")
        page.locator("button:has-text('Stwórz Skarbiec')").click()
        expect(page.locator("#init-screen")).to_be_hidden(timeout=5000)

    if page.locator("#auth-password").is_visible():
        page.locator("#auth-password").fill("1234")
        page.locator("button:has-text('Odblokuj')").click()
        expect(page.locator("#login-screen")).to_be_hidden(timeout=5000)

    if page.locator("#pin-modal").is_visible():
        page.locator("#pin-modal button", has_text="✕").click()
        expect(page.locator("#pin-modal")).to_be_hidden()

    # Kliknięcie w zakładkę Projekt
    page.locator("#tab-settings").click()

    # Weryfikacja że jesteśmy w settings
    settings_screen = page.locator("#settings-screen")
    expect(settings_screen).to_be_visible(timeout=5000)

    # Ponieważ po świeżym zalogowaniu workspace ma project_ref="",
    # powinien pojawić się formularz Credentials (STAN 1)
    state1 = page.locator("#project-state-1")
    expect(state1).to_be_visible()

    # I STAN 2 powinien być ukryty
    state2 = page.locator("#project-state-2")
    expect(state2).to_be_hidden()

    # Formularz powinien mieć pole na bazę danych (D3)
    db_input = page.locator("#proj-db")
    expect(db_input).to_be_visible()
