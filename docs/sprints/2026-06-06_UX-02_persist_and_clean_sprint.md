# 🩺 Sprint: UX-02 — Persistence & Security Cleanup (Utrwalenie stanu i czyszczenie)

> **Architekt:** /arch | **Tryb:** Sequential | **Status:** PLANNED
> **Data:** 2026-06-06 | **Bazuje na:** Zakończonym sprincie UX-01
> **Epic:** `docs/sprints/2026-06-05_EPIC-HUB_centrum_zarzadzania.md`
> **Wymaga:** ✅ UX-01 zakończone

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Aplikacja poprawnie inicjuje cykl życia po stronie UI (poprawki z UX-01 zakończone), natomiast jej stan jest wciąż ulotny (in-memory). Przeładowanie serwera backendowego skutkuje utratą skonfigurowanych "workspaces" i historii "proposals". Dodatkowo w kodzie UI wciąż znajdują się techniczne długi po starym modelu autoryzacji, a addon Odoo operuje na zhardkodowanych tokenach. Celem sprintu UX-02 jest osiągnięcie pełnej gotowości środowiska do działania bez utraty danych pomiędzy restartami ("Persistent Ready-for-Use System").

### Root Cause Analysis & Dług Techniczny

```
┌────────────────────────────────────────────────────────────┐
│  DŁUG TECHNICZNY DO USUNIĘCIA (3 Główne Obszary)           │
│                                                            │
│  🔴 Security Cleanup:                                      │
│  ├── BUG-01: Zmienna globalna `currentAuth` w index.html   │
│  │           musi zostać całkowicie wyeliminowana.         │
│  ├── BUG-02: Hardcoded token ("Bearer 1111") w             │
│  │           `custom_addons/smart_chat/controllers/main.py`│
│                                                            │
│  🟡 State Persistence:                                     │
│  ├── BUG-03: `_workspaces` jako in-memory dict w api.py    │
│  ├── BUG-04: `_proposals` jako in-memory dict w api.py     │
│                                                            │
│  🟠 Backend Refactoring:                                   │
│  ├── BUG-05: Brak modeli SQLAlchemy dla Workspaces i       │
│  │           Proposals w `core/models.py`.                 │
└────────────────────────────────────────────────────────────┘
```

### Metryka sukcesu (DoD)
1. **Pełna persystencja:** Dodanie `workspace` w UI oraz zatwierdzenie `proposal` przetrwa restart backendu (`FastAPI`).
2. **Zero Hardcoded Secrets:** Kod w `index.html` bazuje tylko na `AppStore.getState().authToken`. Odoo addon używa `os.environ.get('SMARTMYODOO_API_TOKEN')`.
3. **Migracja SQLAlchemy:** Baza SQLite faktycznie zapisuje `workspaces` oraz `proposals`. Zastosowano poprawne tworzenie tabel w locie.
4. **Testy (Green):** Testy systemowe (`test_api.py`, `test_database.py`) wykonują się bezbłędnie (ALL GREEN).

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza 1 (Security Cleanup) → BRAMKA → Faza 2 (Persistence Models) → BRAMKA → Faza 3 (API Refactoring)

#### Zasada 2: ZERO REGRESSION 🔴
Istniejące testy muszą pozostać zielone. Należy upewnić się, że zmiana pamięci z in-memory na SQLite w `api.py` nie łamie funkcjonalności UI (format zwracanych JSONów musi być zgodny).

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności

```
┌──────────────────────────────────────┐
│  FAZA 1 (Security Cleanup)           │
│  [Eliminacja currentAuth]            │
│  [Odoo Addon Env Var]                │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Zero hardcoded creds
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Persistence Models)         │
│  [Modele SQLAlchemy Workspace]       │
│  [Modele SQLAlchemy Proposal]        │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Tabele w DB
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (API Refactoring)            │
│  [Podłączenie modeli w api.py]       │
│  [Usunięcie in-memory dicts]         │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Security Cleanup

> **📁 Scope:** `smartmyodoo/ui/index.html`, `custom_addons/smart_chat/controllers/main.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | `index.html` — wyeliminuj zmienną globalną `currentAuth` | Zastąpienie wszystkich wystąpień przez `AppStore.getState().authToken` | [ ] |
| 1.2 | `main.py` (Addon) — zastąpienie `"Bearer 1111"` odczytem z `.env` | Kod pobiera token przez `os.environ.get('SMARTMYODOO_API_TOKEN', '')` | [ ] |
| 1.3 | **BRAMKA:** Credentials Audit | `grep -r "1111" custom_addons/` oraz `grep -r "currentAuth" smartmyodoo/ui/` -> puste | [ ] |

---

### Sekcja B2 — FAZA 2: Persistence Models

> **📁 Scope:** `smartmyodoo/core/models.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | `models.py` — Dodaj model `Workspace` | Pola: `id` (String PK), `name` (String), `odoo_url` (String), `created_at` (DateTime) | [ ] |
| 2.2 | `models.py` — Dodaj model `Proposal` | Pola: `id` (String PK), `workspace_id` (String), `description` (String), `status` (String), `created_at` (DateTime) | [ ] |
| 2.3 | **BRAMKA:** DB Schema | Aplikacja tworzy tabele `workspaces` i `proposals` w `smartmyodoo.db` po starcie | [ ] |

---

### Sekcja B3 — FAZA 3: API Refactoring

> **📁 Scope:** `smartmyodoo/api.py`, `smartmyodoo/core/database.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | `api.py` — iniekcja DB Sesji (`Depends(get_db)`) | Endpointy `GET /api/workspaces`, `POST /api/workspaces`, `PUT /api/workspaces/{id}` czytają/zapisują do bazy | [ ] |
| 3.2 | `api.py` — Endpointy Proposals | Endpointy obsługujące czat/proposals odczytują/zapisują do tabeli `Proposal` | [ ] |
| 3.3 | `api.py` — Usunięcie słowników in-memory | Skasowane deklaracje `_workspaces = []` i `_proposals = {}` | [ ] |
| 3.4 | **BRAMKA:** Persistence test | Dodanie workspace z poziomu UI przetrwa restart backendu | [ ] |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Akcja | Oczekiwany wynik |
|---|-------|-------|------------------|
| V1 | Unit Tests | `pytest tests/test_api.py -v` | ✅ ALL GREEN |
| V2 | Database State | Zapis nowego workspace i restart uvicorn | ✅ Workspace widoczny w UI po restarcie |
| V3 | Security Audit | Szukanie hardcoded stringów (1111, currentAuth) | ✅ Brak wycieków |
