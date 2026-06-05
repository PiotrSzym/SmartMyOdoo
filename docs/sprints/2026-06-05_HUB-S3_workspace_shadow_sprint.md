# 🚀 Sprint: HUB-S3 — Workspace Context + Shadow Mode UI

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-05 | **Bazuje na:** EPIC-HUB Centrum Zarządzania
> **Epic:** `docs/sprints/2026-06-05_EPIC-HUB_centrum_zarzadzania.md`
> **Wymaga:** ✅ HUB-S1 + ✅ HUB-S2 zakończone

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Czat wie, do jakiego Odoo się podłączyć (na podstawie wybranej Przestrzeni Roboczej).
Agent tworzy propozycje w trybie Shadow Mode, które użytkownik zatwierdza/odrzuca
bezpośrednio z panelu czatu. Przycisk "+ Nowa Przestrzeń" zaczyna działać.

### Metryka sukcesu (DoD)
1. Wybranie przestrzeni "Production" → Czat wyświetla nagłówek "Przestrzeń: Production"
2. Agent generuje propozycję → karta z przyciskami ✅ Approve / ❌ Reject pojawia się w czacie
3. Kliknięcie Approve → propozycja zmienia status na "approved" w backendzie
4. Przycisk "+ Nowa Przestrzeń" otwiera modal z formularzem i zapisuje nową przestrzeń

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza 1 (Backend API proposals) → BRAMKA → Faza 2 (Frontend Proposal Cards) → BRAMKA → Faza 3 (Workspace CRUD).

#### Zasada 2: TDD FIRST 🟠
Nowe endpointy `/api/proposals` wymagają testów w `test_api.py` PRZED implementacją frontendu.

#### Zasada 3: SCOPE ISOLATION 🔴
Backend: `smartmyodoo/api.py`, `smartmyodoo/mcp/shadow_mode.py`.
Frontend: `smartmyodoo/ui/js/components/chat.js`, `smartmyodoo/ui/js/components/sidebar.js`.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności

```
┌──────────────────────────────────────┐
│  FAZA 1 (Backend: Proposals API)     │
│  [GET /api/proposals]                │
│  [POST /api/proposals/{id}/approve]  │
│  [POST /api/proposals/{id}/reject]   │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: pytest green +
               │           curl proposals API
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Frontend: Proposal Cards)   │
│  [Shadow Mode karty w czacie]        │
│  [Approve/Reject buttons]            │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Visual test — karta
               │           z przyciskami renderuje się
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (Workspace CRUD)             │
│  [Modal "Nowa Przestrzeń"]           │
│  [Workspace API + Sidebar refresh]   │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Backend Proposals API

> **📁 Scope:** `smartmyodoo/api.py`, `tests/test_api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | `GET /api/proposals?workspace_id=X` | Zwraca listę propozycji Shadow Mode dla workspace | [x] |
| 1.2 | `POST /api/proposals/{id}/approve` | Zmienia status propozycji na "approved" | [x] |
| 1.3 | `POST /api/proposals/{id}/reject` | Zmienia status propozycji na "rejected" | [x] |
| 1.4 | `/api/chat` generuje propozycje | Jeśli Dispatcher → kategoria B (DBA): automatyczna propozycja Shadow | [x] |
| 1.5 | Testy pytest | Nowe testy: `test_proposals_crud`, `test_chat_generates_proposal` | [x] |
| 1.6 | **BRAMKA:** pytest + curl | ✅ `pytest tests/ -v` → GREEN. `curl GET /api/proposals` → lista JSON | [x] |

---

### Sekcja B2 — FAZA 2: Frontend Proposal Cards

> **📁 Scope:** `smartmyodoo/ui/js/components/chat.js`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Rozpoznanie `action_type === "SHADOW_PROPOSAL"` w response | Odrębny rendering dla propozycji vs. zwykłego czatu | [x] |
| 2.2 | Karta propozycji: model, metoda, wartości, powód | Glass-card z ikonami i tabelą zmian | [x] |
| 2.3 | Przyciski ✅ Approve / ❌ Reject | `fetch POST /api/proposals/{id}/approve` z animacją sukcesu | [x] |
| 2.4 | Stan karty po zatwierdzeniu | Zmiana koloru na zielony/czerwony + zablokowanie przycisków | [x] |
| 2.5 | **BRAMKA:** Visual test | ✅ Karta propozycji wyświetla się z dwoma przyciskami. Kliknięcie zmienia stan. | [x] |

---

### Sekcja B3 — FAZA 3: Workspace CRUD

> **📁 Scope:** `smartmyodoo/ui/js/components/sidebar.js`, `smartmyodoo/api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | `GET /api/workspaces` — lista przestrzeni z backendu | Zamiast hardcoded tablicy w sidebar.js | [x] |
| 3.2 | `POST /api/workspaces` — tworzenie nowej przestrzeni | JSON: `{"id": "string", "name": "string"}` | [x] |
| 3.3 | Modal "Nowa Przestrzeń" na kliknięcie przycisku "+" | Formularz z polami: ID, Nazwa, URL Odoo | [x] |
| 3.4 | Sidebar ładuje workspace z API zamiast z hardcoded tablicy | `fetch('/api/workspaces')` w konstruktorze Sidebar | [x] |
| 3.5 | **BRAMKA:** Full CRUD | ✅ Dodanie nowej przestrzeni → pojawia się na liście → sekrety filtrują się do niej | [x] |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Akcja | Oczekiwany wynik |
|---|-------|-------|------------------|
| V1 | Unit Tests | `pytest tests/ -v` | ✅ ALL GREEN |
| V2 | Proposals Flow | Czat → wygenerowana propozycja → Approve | ✅ Status "approved" w backendzie |
| V3 | Workspace Switch | Kliknięcie innej przestrzeni | ✅ Header czatu aktualizuje się, sekrety przeładowują |
| V4 | Nowa Przestrzeń | Kliknięcie "+" → formularz → zapis | ✅ Nowa pozycja na liście sidebara |
| V5 | Konsola | DevTools → Console | ✅ Zero błędów JS |
