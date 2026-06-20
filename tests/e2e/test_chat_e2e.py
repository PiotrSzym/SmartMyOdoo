from playwright.sync_api import Page, expect

# Adres lokalnego serwera z uruchomioną aplikacją (wymaga włączonego backendu)
BASE_URL = "http://127.0.0.1:8000"


def test_chat_layout_and_interaction(page: Page):
    """
    Weryfikuje układ zakładki Czat oraz podstawową interakcję wysyłania wiadomości
    do prawdziwego backendu.
    """
    # 1. Załadowanie strony
    page.goto(BASE_URL)

    # 1.5. Logowanie lub Inicjalizacja (jeśli wymagane)
    if page.locator("#init-master").is_visible():
        page.locator("#init-master").fill("testmaster")
        page.locator("#init-pin").fill("1234")
        page.locator("button:has-text('Stwórz Skarbiec')").click()
        expect(page.locator("#init-screen")).to_be_hidden(timeout=5000)

    if page.locator("#auth-password").is_visible():
        page.locator("#auth-password").fill("1234")
        page.locator("button:has-text('Odblokuj')").click()
        expect(page.locator("#login-screen")).to_be_hidden(timeout=5000)

    # Zamknij modal zmiany PINu, jeśli się pojawi (np. gdy logujemy się jako admin)
    if page.locator("#pin-modal").is_visible():
        page.locator("#pin-modal button", has_text="✕").click()
        expect(page.locator("#pin-modal")).to_be_hidden()

    # Przejście do zakładki Czat
    page.locator("#tab-chat").click()

    # 2. Weryfikacja, że główny ekran czatu jest widoczny
    chat_screen = page.locator("#chat-screen")
    expect(chat_screen).to_be_visible(timeout=5000)

    # 3. Weryfikacja zmiany układu: sidebar (sesje) powinien być widoczny na końcu
    sidebar = chat_screen.locator(".w-64.border-l")
    expect(sidebar).to_be_visible()

    # Sprawdzamy, czy input dla chatu jest dostępny
    chat_input = page.locator("#chat-input")
    expect(chat_input).to_be_visible()

    # 4. Wyślij wiadomość "Cześć"
    chat_input.fill("Cześć, test E2E")

    # Kliknięcie przycisku wysyłania (zakładając, że ma id #chat-send lub to enter)
    page.keyboard.press("Enter")

    # 5. Oczekiwanie na bąbelek z odpowiedzią Agenta.
    # Czekamy aż zniknie wskaźnik ładowania.
    # Timeout 25s (nie 10s): to realne wywołanie LLM (LiteLLM→OpenRouter) — round-trip
    # ~5s + cold-start chromium/serwera na /mnt/c (WSL2). 10s bywało za ciasne (flake /qa).
    expect(page.locator("text='Agent myśli...'")).to_be_hidden(timeout=25000)

    # Używamy selektora pasującego do renderowania z chat.js (klasa dla dymków AI)
    agent_message = page.locator(
        "#chat-messages-list .justify-start .backdrop-blur-sm"
    ).last

    # Oczekujemy, że pojawi się odpowiedź
    expect(agent_message).to_be_visible(timeout=5000)

    # Treść zależy od Persony, ale powinno się pojawić jakiekolwiek echo lub template z backendu
    text = agent_message.inner_text()
    assert len(text) > 5
    assert "Agent myśli..." not in text
