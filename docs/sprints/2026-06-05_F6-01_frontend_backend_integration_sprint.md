# 🚀 Sprint: F6-01 Frontend-Backend Smart Chat Integration

> **Architekt:** /arch | **Tryb:** Sequential
> **Status:** DONE
> **Data:** 2026-06-05 | **Bazuje na:** Faza 6 Implementation Plan

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Ożywienie wydmuszki frontendowej modułu `smart_chat` (OWL) poprzez podłączenie jej do silnika decyzyjnego FastAPI. Realizacja wzorca Proxy (Odoo Controller jako pośrednik), z zachowaniem pełnego kontekstu użytkownika i ominięciem blokad CORS.

### Metryka sukcesu (DoD)
Wpisanie wiadomości w oknie czatu po stronie Odoo powoduje przesłanie poprawnego payloadu JSON przez Odoo Proxy do FastAPI i zwrócenie odpowiedzi Agenta w interfejsie użytkownika.

### ⚖️ ZASADY SPRINTU — Podsumowanie dla Użytkownika

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Fazy muszą być realizowane ściśle jedna po drugiej. Nie modyfikujemy Frontendu OWL, dopóki Backend FastAPI nie będzie stabilny. Nie ruszamy Proxy w Odoo, dopóki backend nie potrafi przyjąć struktury JSON.

#### Zasada 2: STRICT JSON CONTRACT 🟠
Pełna zgodność typowania (Pydantic po stronie FastAPI) i nazw kluczy z ustanowioną niżej Listą Pól (API Contract). Odchylenia od tych nazw natychmiast wyrzucą 422 Unprocessable Entity.

#### Zasada 3: SAFE CORS 🔴
Żadnych bezpośrednich zapytań HTTP (`fetch`, `XMLHttpRequest`) do portu 8000 z przeglądarki użytkownika. Używamy wyłącznie `this.rpc('/smart_chat/send')`.

---

## 📡 API Contract (Lista Pól do Połączenia)

### 1. Request: Frontend (OWL) -> Odoo Proxy -> FastAPI
```json
{
  "message": "string",       // Treść wpisana w inpucie przez usera
  "user_id": "int",          // ID zalogowanego usera (odczytywane z sesji przez Odoo Proxy)
  "active_model": "string",  // Model, na którym user obecnie przebywa np. "res.partner"
  "active_id": "int",        // ID obecnego rekordu w Odoo
  "session_id": "string"     // Identyfikator sesji czatu
}
```

### 2. Response: FastAPI -> Odoo Proxy -> Frontend (OWL)
```json
{
  "reply": "string",         // Tekst do wyświetlenia w chmurce agenta
  "action_type": "string",   // Typ akcji: "CHAT" (zwykła odp.) lub "SHADOW_PROPOSAL"
  "proposal_data": {         // (Opcjonalnie) Jeśli padnie propozycja w tle
    "proposal_id": "string",
    "text": "string",
    "model": "string",
    "method": "string",
    "args": []
  }
}
```

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────┐
│  FAZA 1 (FastAPI Backend)            │
│  [API Endpoint + Pydantic]           │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Test curl - HTTP 200
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Odoo Proxy Controller)      │
│  [Proxy /smart_chat/send]            │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: RPC Odoo Log Test
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (Frontend OWL Widget)        │
│  [Input Event & Render]              │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: FastAPI Backend Endpoint

> **📁 Scope:** `c:\od_zera_do_ai\SmartMyOdoo\smartmyodoo\`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Utworzenie modeli Pydantic | Klasy `ChatRequest` i `ChatResponse` zgodne z kontraktem. | [x] |
| 1.2 | Endpoint `POST /api/chat` w API | Deklaracja routingu w FastAPI, parsowanie Requesta. | [x] |
| 1.3 | Podpięcie pod `Dispatcher` | Przekazanie `message` do logiki silnika AgentSwarm. | [x] |
| 1.4 | **BRAMKA:** Weryfikacja API | ✅ `curl -X POST /api/chat` zwraca kod 200 | [x] |

---

### Sekcja B2 — FAZA 2: Odoo Proxy Controller

> **📁 Scope:** `c:\od_zera_do_ai\SmartMyOdoo\custom_addons\smart_chat\controllers\`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Utworzenie pakietu `controllers` | Dodano pliki `main.py` oraz `__init__.py`. | [x] |
| 2.2 | Inicjalizacja `@http.route` | Typ `json`, autoryzacja `user`. | [x] |
| 2.3 | Ekstrakcja `user_id` z Odoo | Pomyślne czytanie `request.env.user.id`. | [x] |
| 2.4 | HTTP Forwarding (Proxy) | Wysłanie `requests.post` pod adres FastAPI i obsługa błędów. | [x] |
| 2.5 | **BRAMKA:** Logika Proxy | ✅ Odoo przyjmuje call RPC i loguje sukces zapytania. | [x] |

---

### Sekcja B3 — FAZA 3: Frontend OWL Widget

> **📁 Scope:** `c:\od_zera_do_ai\SmartMyOdoo\custom_addons\smart_chat\static\src\components\`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Bindings na pliku `.xml` | Dopisane `t-on-keydown`, `t-ref` oraz guzik (opcjonalny). | [x] |
| 3.2 | Przechwycenie klawiatury | Metoda w JavaScript reaguje wyłącznie na `ev.key === "Enter"`. | [x] |
| 3.3 | Aktualizacja Stanu (UI) | Dopisanie wypowiedzi usera do `state.messages` od razu po wpisaniu. | [x] |
| 3.4 | Wywołanie `this.rpc()` | Skompletowanie JSONa i wysyłka asynchronicznie do Odoo. | [x] |
| 3.5 | **BRAMKA:** Pełny Cykl (E2E) | ✅ Odpowiedź wygenerowana przez FastAPI widoczna w chmurce Odoo. | [x] |

---

## ✅ Sekcja E — Finalna Weryfikacja

> Wykonuje użytkownik po zakończeniu wszystkich faz.

| # | Check (Core Pillars) | Akcja | Oczekiwany wynik |
|---|----------------------|---------|------------------|
| V1 | Linting Codebase | `pre-commit run --all-files` | ✅ Wszystkie checki przechodzą bez błędów. |
| V2 | Rozmowa E2E | Odpalenie Odoo, napisanie w dymku czatu np. "Cześć" | ✅ Otrzymanie odpowiedzi od agenta FastAPI. |
