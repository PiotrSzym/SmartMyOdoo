# 🚀 Sprint: HUB-S1 — Chat UI na SmartMyOdoo Hub

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-05 | **Bazuje na:** EPIC-HUB Centrum Zarządzania
> **Epic:** `docs/sprints/2026-06-05_EPIC-HUB_centrum_zarzadzania.md`

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Dodanie zakładki "Czat" do istniejącego interfejsu SmartMyOdoo Hub (`localhost:8000`),
z pełnym interfejsem konwersacyjnym (lista wiadomości, input, wysyłanie).
Po zakończeniu tego Sprintu użytkownik **zobaczy prawdziwy UI czatu** na swojej stronie
i będzie mógł wysyłać wiadomości do backendu.

### Metryka sukcesu (DoD)
1. Wejście na `http://localhost:8000` → po zalogowaniu widoczna zakładka **"Czat"**
2. Kliknięcie zakładki → pełnoekranowy panel rozmowy z inputem
3. Wpisanie tekstu + Enter → wiadomość pojawia się w bąbelku "user"
4. Odpowiedź z `/api/chat` pojawia się w bąbelku "agent" z animacją "Agent myśli..."

### ⚖️ ZASADY SPRINTU — Podsumowanie

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Faza 1 (Store + HTML) → BRAMKA → Faza 2 (Chat Component JS) → BRAMKA → Faza 3 (API Hookup + Polish).
Nie kodujemy logiki JS, dopóki szkielet HTML i Store nie są gotowe.

#### Zasada 2: TDD FIRST 🟠
Każda Faza kończy się manualnym testem weryfikacyjnym (BRAMKA) przed przejściem do kolejnej.
Kod musi przejść walidację wizualną (strona się ładuje bez błędów w konsoli).

#### Zasada 3: SCOPE ISOLATION 🔴
Sprint dotyka **WYŁĄCZNIE** plików w `smartmyodoo/ui/`.
Żadnych zmian w `api.py`, `swarm/`, `mcp/`, `custom_addons/`.

---

## 📡 API Contract (Istniejący — bez zmian)

### Request: Chat UI → FastAPI
```json
{
  "message": "string",
  "user_id": 1,
  "active_model": null,
  "active_id": null,
  "session_id": "hub-{timestamp}"
}
```

### Response: FastAPI → Chat UI
```json
{
  "reply": "string",
  "action_type": "CHAT",
  "proposal_data": null
}
```

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────┐
│  FAZA 1 (Fundament HTML + Store)     │
│  [Tab "Czat" + div chat-screen]      │
│  [Store: activeTab='chat']           │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Zakładka widoczna,
               │           przełączanie działa
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Chat Component JS)         │
│  [ChatPanel class + render]          │
│  [Message list + input + send]       │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Wiadomości renderują
               │           się w bąbelkach
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (API Hookup + Design)       │
│  [POST /api/chat + animacja]         │
│  [Premium styling + scroll]          │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Fundament HTML + Store

> **📁 Scope:** `smartmyodoo/ui/index.html`, `smartmyodoo/ui/js/store.js`, `smartmyodoo/ui/js/components/canvas.js`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Dodać przycisk "Czat" do `#tab-bar` w `index.html` | Nowy `<button id="tab-chat">` widoczny obok Skarbca i Ustawień | [ ] |
| 1.2 | Dodać `<div id="chat-screen">` w `#main-canvas` | Pusty div z klasą ukrytą, pomiędzy vault-screen a settings-screen | [ ] |
| 1.3 | Zmienić domyślny `activeTab` w Store z `'dashboard'` na `'vault'` | Fix buga: Store ustawia tab, który nie istnieje w DOM | [ ] |
| 1.4 | Rozszerzyć `Canvas.updateTabs()` o obsługę `'chat'` | Przełączanie zakładki pokazuje/ukrywa `#chat-screen` | [ ] |
| 1.5 | Dodać `<script src="js/components/chat.js" defer>` | Import nowego komponentu w `<head>` | [ ] |
| 1.6 | **BRAMKA:** Weryfikacja wizualna | ✅ Trzy zakładki widoczne. Klikanie przełącza treść. Brak błędów w konsoli. | [ ] |

---

### Sekcja B2 — FAZA 2: Chat Component (Vanilla JS)

> **📁 Scope:** `smartmyodoo/ui/js/components/chat.js` [NEW]

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Klasa `ChatPanel` z konstruktorem | Odczyt `#chat-screen`, inicjalizacja `this.messages = []` | [ ] |
| 2.2 | Metoda `render()` — layout czatu | Div z listą wiadomości (scrollowalny) + input bar na dole | [ ] |
| 2.3 | Obsługa Enter i kliknięcia Send | `addMessage('user', text)` → re-render → clear input | [ ] |
| 2.4 | Renderowanie bąbelków (user/agent) | Bąbelki z awatarem, timestampem, różnymi kolorami (user=indigo, agent=purple) | [ ] |
| 2.5 | Auto-scroll do najnowszej wiadomości | `scrollTop = scrollHeight` po każdym renderze | [ ] |
| 2.6 | **BRAMKA:** Test ręczny | ✅ Wpisanie tekstu → bąbelek user'a pojawia się. Brak odpowiedzi agenta (jeszcze). | [ ] |

---

### Sekcja B3 — FAZA 3: API Hookup + Premium Design

> **📁 Scope:** `smartmyodoo/ui/js/components/chat.js`, `smartmyodoo/ui/index.html` (CSS)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Metoda `sendToAPI(message)` — POST `/api/chat` | Fetch z JSON body (zgodnym z kontraktem), obsługa błędów | [ ] |
| 3.2 | Animacja "Agent myśli..." | Pulsujący bąbelek z trzema kropkami podczas oczekiwania na response | [ ] |
| 3.3 | Wyświetlenie odpowiedzi agenta | Usunięcie "myśli...", dodanie bąbelka z `response.reply` | [ ] |
| 3.4 | Header czatu z info o przestrzeni | Nagłówek: "Czat z Agentem • Przestrzeń: {workspaceId}" | [ ] |
| 3.5 | Reakcja na zmianę workspace | Subskrypcja `AppStore` → wyczyszczenie historii czatu przy zmianie przestrzeni | [ ] |
| 3.6 | Premium CSS: glassmorphism, gradient, glow | Bąbelki z efektem szkła, glow na inputcie, gradient na headerze | [ ] |
| 3.7 | **BRAMKA:** Test E2E | ✅ Wpisanie "napisz kod" → "Agent myśli..." → odpowiedź z backendu widoczna w bąbelku | [ ] |

---

## ✅ Sekcja E — Finalna Weryfikacja

> Wykonuje użytkownik lub `/qa` po zakończeniu wszystkich faz.

| # | Check (Core Pillars) | Akcja | Oczekiwany wynik |
|---|----------------------|-------|------------------|
| V1 | Visual Check | Wejście na `localhost:8000`, login, kliknięcie "Czat" | ✅ Panel czatu widoczny z inputem i historią |
| V2 | Wysłanie wiadomości | Wpisanie "cześć" + Enter | ✅ Bąbelek user'a + animacja + odpowiedź agenta |
| V3 | Zmiana przestrzeni | Kliknięcie "Dev Env" na pasku bocznym | ✅ Historia czatu czyści się, header aktualizuje |
| V4 | Konsola przeglądarki | DevTools → Console | ✅ Zero błędów JS |
| V5 | Backend Mock | `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message":"test","user_id":1,"session_id":"s1"}'` | ✅ HTTP 200 + JSON z kluczem `reply` |
