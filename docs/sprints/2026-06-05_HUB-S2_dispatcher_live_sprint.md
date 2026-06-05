# 🚀 Sprint: HUB-S2 — Dispatcher Live (Backend Mózgu)

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-05 | **Bazuje na:** EPIC-HUB Centrum Zarządzania
> **Epic:** `docs/sprints/2026-06-05_EPIC-HUB_centrum_zarzadzania.md`
> **Wymaga:** ✅ HUB-S1 (Chat UI) zakończony

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Podmiana hardcoded mocka w `/api/chat` na prawdziwy Swarm Dispatcher.
Po tym Sprincie agent zaczyna **klasyfikować intencje** i odpowiadać kontekstem
(kategoria, persona, zalecany model), a opcjonalnie — odpowiedzią z LLM.

### Metryka sukcesu (DoD)
1. POST `/api/chat` z treścią "napisz kod migracji" → odpowiedź z `category: "A"`, `persona: "Developer"`
2. POST `/api/chat` z treścią "sprawdź tabelę partnerów" → `category: "B"`, `persona: "Database Administrator"`
3. Jeśli klucz OpenRouter istnieje w Skarbcu → odpowiedź generowana przez LLM

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza 1 (Dispatcher hookup) → BRAMKA (pytest green) → Faza 2 (LLM Client) → BRAMKA → Faza 3 (Response enrichment).

#### Zasada 2: TDD FIRST 🟠
Test `test_dispatcher.py` musi pozostać ZIELONY po każdej zmianie. Nowe testy na integrację `api.py ↔ dispatcher`.

#### Zasada 3: SCOPE ISOLATION 🔴
Dotykamy **WYŁĄCZNIE**: `smartmyodoo/api.py`, `smartmyodoo/swarm/`, `tests/`.
Bez zmian w `ui/`, `mcp/`, `custom_addons/`.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności

```
┌──────────────────────────────────────┐
│  FAZA 1 (Dispatcher → api.py)        │
│  [Import + Singleton + classify]     │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: pytest green +
               │           curl zwraca category
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (LLM Client Factory)        │
│  [OpenRouter HTTP + Vault inject]    │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Fallback bez klucza
               │           działa. Z kluczem → LLM.
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (Response Enrichment)        │
│  [ChatResponse rozszerzone pola]     │
│  [Frontend renderuje kategorię]      │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Dispatcher Hookup

> **📁 Scope:** `smartmyodoo/api.py`, `smartmyodoo/swarm/dispatcher.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Import `Dispatcher` w `api.py` | `from smartmyodoo.swarm.dispatcher import Dispatcher` | [x] |
| 1.2 | Inicjalizacja singletona `dispatcher = Dispatcher()` | Jedna instancja na poziomie modułu | [x] |
| 1.3 | Podmiana mocka w `handle_chat()` | `dispatcher.classify_intent(req.message)` zamiast hardcode | [x] |
| 1.4 | Budowa `reply` z wyniku Dispatchera | Format: `"[Persona] odpowiedź: category={X}"` (tymczasowy) | [x] |
| 1.5 | **BRAMKA:** pytest + curl | ✅ `pytest tests/ -v` → GREEN. `curl POST /api/chat` → `category` w response | [x] |

---

### Sekcja B2 — FAZA 2: LLM Client Factory

> **📁 Scope:** `smartmyodoo/swarm/llm_client.py` [NEW], `smartmyodoo/api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Plik `llm_client.py` z klasą `OpenRouterClient` | Metoda `chat(prompt) -> str` wysyłająca POST do OpenRouter | [x] |
| 2.2 | Fallback: jeśli brak klucza API → `Dispatcher(llm_client=None)` | Heurystyki działają bez internetu | [x] |
| 2.3 | Wstrzyknięcie klucza ze Skarbca (opcjonalne) | Odczyt z ENV `OPENROUTER_KEY` przy starcie serwera | [x] |
| 2.4 | Test: mock LLM client | `test_dispatcher.py` z zamockowanym `llm_client.chat()` → JSON category | [x] |
| 2.5 | **BRAMKA:** Dual-mode test | ✅ Bez klucza: fallback heurystyczny. Z kluczem: pełna klasyfikacja LLM. | [x] |

---

### Sekcja B3 — FAZA 3: Response Enrichment

> **📁 Scope:** `smartmyodoo/swarm/models.py`, `smartmyodoo/api.py`, `smartmyodoo/ui/js/components/chat.js`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Rozszerzyć `ChatResponse` o `category`, `persona`, `model` | Pydantic: nowe opcjonalne pola | [x] |
| 3.2 | `api.py` wypełnia nowe pola z `DispatchResult` | Mapowanie: `result.category.value` → `response.category` | [x] |
| 3.3 | Frontend: badge z kategorią i personą nad bąbelkiem agenta | Kolorowy tag: `[🏗 Architect]` lub `[💻 Developer]` | [x] |
| 3.4 | **BRAMKA:** Visual + API | ✅ Bąbelek z tagiem persony. API zwraca pełny JSON z 6 polami. | [x] |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|------------------|
| V1 | Unit Tests | `pytest tests/ -v` | ✅ ALL GREEN |
| V2 | Klasyfikacja A | `curl -X POST ... -d '{"message":"napisz kod","user_id":1,"session_id":"s"}'` | ✅ `category: "A"` |
| V3 | Klasyfikacja B | `curl ... -d '{"message":"pokaż tabelę klientów",...}'` | ✅ `category: "B"` |
| V4 | Klasyfikacja H | `curl ... -d '{"message":"cześć co słychać",...}'` | ✅ `category: "H"` |
| V5 | UI Render | Wejście na Hub → Czat → wysyłka | ✅ Tag persony widoczny nad bąbelkiem |
