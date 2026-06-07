---
sprint_id: "F7-01"
workspace: "SmartMyOdoo"
status: "PLANNING"
created: 2026-06-07
closed: null
goal: "Dwustanowy widok zakładki Projekt — Credentials → Task Picker → Dual Time Tracking (Nominalny + Rzeczywisty) z integracją XML-RPC do Odoo Timesheets"
prefix: "F7"
complexity: 6
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
tags: ["time-tracking", "task-picker", "odoo-connector", "credentials", "vault", "xml-rpc", "timesheet", "dual-time", "project-tab"]
arch_decisions:
  D1_dual_time: "DWIE ŚCIEŻKI CZASU — nominalny (ręczny, pod wybrane zadanie) + rzeczywisty (automatyczny, pod zadanie domyślne [SmartMyOdoo] Pula czasu roboczego)"
  D2_credentials_flow: "VAULT-FIRST — credentials wpisywane w zakładce Projekt, zapisywane w Smart Vault pod kluczem ODOO_PROJECT_{workspace_id}"
  D3_db_field: "DODANO — pole 'Nazwa bazy danych' w formularzu (backend już obsługiwał pole `db` w schemacie Vaulta)"
  D4_task_picker_source: "ODOO ONLY — project.task via XML-RPC (search_read); Jira/Linear → Faza 8+"
  D5_default_task: "AUTO-CREATE — jeśli brak task_ref, system tworzy project.task o nazwie '[SmartMyOdoo] Pula czasu roboczego'"
  D6_no_project_no_auto: "BRAK PROJEKTU = BRAK AUTOMATYCZNEGO LOGOWANIA — czas rzeczywisty wymaga project_ref"
  D7_ui_state_machine: "TWO-STATE UI — Stan 1: Formularz Credentials | Stan 2: Task Picker + Active Task Banner"
depends_on: ["F6-02"]
---

# 🚀 Sprint: F7-01 Zakładka Projekt — Dual Time Tracking & Task Picker

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-07 | **Bazuje na:** Roadmap Faza 7.3 (Auto-Timesheets) + Ustalenia z sesji architektonicznej

---

## 📋 Sekcja A — Business Discovery & Problem Definition

### Problem 1: Brak pola "Nazwa bazy danych" w formularzu Projekt
Model Vaulta (`SecretCreateRequest`) obsługuje pole `db`, ale formularz UI nie zawiera inputa na nazwę bazy. Połączenie XML-RPC z Odoo wymaga trzech elementów: URL + DB + Login/Password.

### Problem 2: Zakładka "Ustawienia" nie odzwierciedla workflow
Obecna zakładka to formularz konfiguracyjny, który jest zawsze widoczny. Po podłączeniu do Odoo użytkownik powinien widzieć dostępne zadania, a nie znowu formularz.

### Problem 3: Brak automatycznego Time Trackingu
Roadmap (Faza 3, US 4.1+4.3) deklaruje Auto-Timesheets, ale realny connector XML-RPC do `account.analytic.line` (Odoo Timesheet) nie istnieje. Nie ma też logiki "zadania domyślnego".

### Problem 4: Brak rozróżnienia czas nominalny vs rzeczywisty
Odoo pozwala na wpisywanie godzin nominalnych (estymowanych) per zadanie. SmartMyOdoo potrzebuje dwóch torów: czas wpisany ręcznie (nominalny) + czas zmierzony automatycznie (rzeczywisty).

### Problem 5: Schema DB rozjeżdża się z modelem
Tabela `workspaces` w bazie SQLite nie posiada kolumny `project_ref`, choć model SQLAlchemy ją deklaruje. Powoduje `OperationalError: no such column: workspaces.project_ref` przy każdym restarcie.

---

## 🏛️ Sekcja A.1 — Decyzje Architektoniczne (ROZSTRZYGNIĘTE)

| # | Decyzja | Rozwiązanie | Uzasadnienie |
|---|---------|-------------|--------------|
| D1 | Ile typów czasu? | **Dwa: Nominalny + Rzeczywisty** | Nominalny = ręcznie wpisany pod wybrane zadanie; Rzeczywisty = automatyczny pod zadanie domyślne |
| D2 | Gdzie credentials? | **Smart Vault** | Spójne z istniejącą architekturą; klucz `ODOO_PROJECT_{ws_id}` |
| D3 | Brakujące pole UI | **Dodać "Nazwa bazy danych"** | Backend (`schemas.py:34`) już ma pole `db`, UI nie miał inputa |
| D4 | Źródło zadań | **Tylko Odoo** | XML-RPC `project.task.search_read`; Jira/Linear → Faza 8+ |
| D5 | Zadanie domyślne | **Auto-create** | `[SmartMyOdoo] Pula czasu roboczego` tworzony automatycznie |
| D6 | Brak projektu | **Brak auto-logowania** | Jawna polityka — nie logujemy czasu bez wskazanego projektu |
| D7 | UI State Machine | **Two-State** | Stan 1: Credentials → Stan 2: Task Picker + Active Task Banner |

---

## ✅ Metryka sukcesu (DoD)

### Functional
1. Zakładka "Projekt" w stanie 1 (brak credentials): formularz z polami URL, DB, Login, Hasło, ID Projektu.
2. Po podaniu credentials i kliknięciu "Połącz": zapis do Vault + automatyczne przejście do stanu 2.
3. Stan 2: Banner "Aktywne Zadanie" na górze + lista zadań z Odoo poniżej.
4. Kliknięcie zadania z listy → ustawia je jako `task_ref` → banner się aktualizuje.
5. API endpoint `POST /api/workspaces/{id}/timesheets` loguje czas do Odoo (`account.analytic.line`).
6. Jeśli `task_ref` jest puste, auto-tworzy zadanie domyślne w Odoo.
7. Migracja Alembic dodaje brakujące kolumny do tabeli `workspaces`.

### Quality Gates
8. `python -m pytest tests/ -v` → ALL GREEN.
9. `ruff check smartmyodoo/` → 0 errors.
10. Sprint zamknięty w YAML frontmatter.

---

## ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza N+1 nie startuje dopóki bramka Fazy N nie jest zielona. Migracja DB musi być gotowa zanim backend zacznie pisać endpointy, które bazują na nowych kolumnach.

#### Zasada 2: TDD / VALIDATION 🟠
Każdy endpoint API musi mieć test weryfikujący (unit lub E2E). Connector XML-RPC testowany przez mockowanie `xmlrpc.client`.

#### Zasada 3: SCOPE ISOLATION 🔴
Zmiany dotyczą wyłącznie plików w scope każdej fazy. Brak zmian w `swarm/`, `mcp/` ani `vault/vault.py`.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────────────────────┐
│  FAZA 1: Migracja DB + Fix Schema                    │
│  [1.1] Alembic migration: add project_ref columns    │
│  [1.2] Weryfikacja: restart serwera bez crashu       │
└──────────────┬───────────────────────────────────────┘
               │ ✅ BRAMKA: `python -m smartmyodoo.api` startuje bez OperationalError
               ▼
┌──────────────────────────────────────────────────────┐
│  FAZA 2: Backend — Odoo Connector & API              │
│  [2.1] odoo_connector.py (XML-RPC client)            │
│  [2.2] API: POST /workspaces/{id}/connect            │
│  [2.3] API: GET /workspaces/{id}/tasks               │
│  [2.4] API: POST /workspaces/{id}/timesheets         │
│  [2.5] Logika auto-create default task               │
└──────────────┬───────────────────────────────────────┘
               │ ✅ BRAMKA: `pytest tests/ -v` (backend tests GREEN)
               ▼
┌──────────────────────────────────────────────────────┐
│  FAZA 3: Frontend — Two-State Project Tab            │
│  [3.1] Stan 1: Formularz z polem DB                  │
│  [3.2] Stan 2: Active Task Banner + Task List        │
│  [3.3] Logika przełączania stanów w JS               │
│  [3.4] Integracja z endpointami z Fazy 2             │
└──────────────┬───────────────────────────────────────┘
               │ ✅ BRAMKA: E2E test (Playwright) — formularz → lista → wybór zadania
               ▼
┌──────────────────────────────────────────────────────┐
│  FAZA 4: Finalna Weryfikacja & Dokumentacja          │
│  [4.1] Testy E2E pełnego flow                        │
│  [4.2] Aktualizacja roadmap.md                       │
│  [4.3] Zamknięcie sprintu                            │
└──────────────────────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Migracja Bazy Danych

> **📁 Scope:** `smartmyodoo/core/models.py`, `migrations/`, `alembic.ini`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Wygenerowanie i uruchomienie migracji Alembic dodającej kolumny `project_ref`, `project_name`, `task_ref`, `task_name` do tabeli `workspaces` | Migracja przechodzi bez błędu na istniejącej bazie `smartmyodoo.db` | [ ] |
| 1.2 | **BRAMKA:** `python -m smartmyodoo.api` startuje i `GET /api/workspaces` zwraca 200 | ✅ Brak `OperationalError` | [ ] |

---

### Sekcja B2 — FAZA 2: Backend — Odoo Connector & Time Tracking API

> **📁 Scope:** `smartmyodoo/core/odoo_connector.py` [NEW], `smartmyodoo/api.py`, `tests/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Nowy moduł `core/odoo_connector.py`: klasa `OdooProjectConnector` — `connect()`, `list_tasks()`, `create_task()`, `log_timesheet()` via XML-RPC | Klasa z type-hints, obsługa błędów | [ ] |
| 2.2 | API: `POST /api/workspaces/{ws_id}/connect` — walidacja credentials (test XML-RPC `version`) + zapis do Vault pod kluczem `ODOO_PROJECT_{ws_id}` | Zwraca 200 przy poprawnych danych, 401 przy złych | [ ] |
| 2.3 | API: `GET /api/workspaces/{ws_id}/tasks` — pobiera `project.task` z Odoo na bazie `project_ref` | Lista JSON z id, name, stage_id, user_id | [ ] |
| 2.4 | API: `POST /api/workspaces/{ws_id}/timesheets` — body: `{task_id, hours, description, is_nominal}` → tworzy `account.analytic.line` w Odoo | Zwraca 201 z ID wpisu | [ ] |
| 2.5 | Logika auto-create: jeśli `task_id` nie podano → `create` w Odoo z nazwą `[SmartMyOdoo] Pula czasu roboczego` pod `project_ref`, cache ID w bazie | Test z mockowanym XML-RPC | [ ] |
| 2.6 | **BRAMKA:** `pytest tests/ -v` → backend tests GREEN | ✅ Nowe testy dla connectora i endpointów | [ ] |

---

### Sekcja B3 — FAZA 3: Frontend — Dwustanowy Widok Projektu

> **📁 Scope:** `smartmyodoo/ui/index.html`, `smartmyodoo/ui/js/components/project.js` [NEW]

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | **Stan 1 (Credentials):** Formularz z polami: URL Odoo, Nazwa Bazy Danych, Login, Hasło/API Key, ID Projektu. Przycisk "🔌 Połącz" wywołuje `POST /connect` | Formularz renderuje się poprawnie, pola walidowane | [ ] |
| 3.2 | **Stan 2 (Task Picker):** Po połączeniu formularz znika. Banner "Aktywne Zadanie" (zielony) na górze z nazwą wybranego taska lub komunikat "Brak zadania — czas trafi do domyślnego". Lista zadań z Odoo poniżej (karty klikalne) | Kliknięcie karty → `PUT /api/workspaces/{id}/task_bind` → banner się aktualizuje | [ ] |
| 3.3 | Logika przełączania stanów: sprawdzenie czy w Vault istnieje klucz `ODOO_PROJECT_{ws_id}` (API `GET /api/secrets`) → jeśli tak → Stan 2 | Automatyczne rozpoznanie stanu po załadowaniu zakładki | [ ] |
| 3.4 | Ikona ⚙️ "Zmień dane" w Stanie 2: kliknięcie przywraca formularz credentials (Stan 1) z wypełnionymi polami | Pozwala edytować bez kasowania połączenia | [ ] |
| 3.5 | **BRAMKA:** Test E2E (Playwright) — otwarcie zakładki Projekt → wypełnienie → lista zadań → klik na zadanie → banner aktualizowany | ✅ Test przechodzi | [ ] |

---

### Sekcja B4 — FAZA 4: Finalna Weryfikacja & Dokumentacja

> **📁 Scope:** `docs/`, `tests/e2e/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 4.1 | Pełny E2E test: logowanie → otwarcie projektu → credentials → lista zadań → log czasu nominalnego → weryfikacja | Playwright test GREEN | [ ] |
| 4.2 | Aktualizacja `docs/blueprint/tom2-architektura/roadmap.md` — oznaczenie F7-01 jako Done | Roadmap zsynchronizowany | [ ] |
| 4.3 | Zamknięcie sprintu: `status: DONE`, `closed: <data>` w frontmatter | Sprint formalnie zamknięty | [ ] |

---

## 📦 Sekcja C — Zależności

### Nowe pliki (utworzone w tym sprincie)
| Plik | Cel |
|------|-----|
| `smartmyodoo/core/odoo_connector.py` | XML-RPC connector do Odoo (project.task, account.analytic.line) |
| `smartmyodoo/ui/js/components/project.js` | Komponent JS dla dwustanowej zakładki Projekt |
| `tests/test_odoo_connector.py` | Testy jednostkowe connectora (mockowany XML-RPC) |
| `tests/e2e/test_project_tab_e2e.py` | Test E2E dla pełnego flow zakładki Projekt |
| `migrations/versions/xxx_add_workspace_project_columns.py` | Migracja Alembic |

### Istniejące moduły re-użyte
| Moduł | Użycie |
|-------|--------|
| `vault/vault.py` | Zapis/odczyt credentials projektu Odoo |
| `vault/schemas.py` | `SecretCreateRequest` z polem `db` |
| `core/models.py` | Model `Workspace` z polami `project_ref`, `task_ref` |
| `core/database.py` | SQLAlchemy engine + `SessionLocal` |
| `ui/js/store.js` | Store z `activeTab` i `workspaceId` |

### Brak nowych pakietów Python
Wszystko opiera się na stdlib (`xmlrpc.client`) i istniejących zależnościach (SQLAlchemy, FastAPI, Pydantic).

---

## ❓ Otwarte Kwestie (rozstrzygnięte)

| # | Kwestia | Decyzja |
|---|---------|---------|
| Q1 | Trigger rejestracji czasu | Dwa tory: nominalny (ręcznie) + rzeczywisty (automatycznie) |
| Q2 | Credentials | Smart Vault, klucz `ODOO_PROJECT_{ws_id}` |
| Q3 | Baza danych w formularzu | Dodajemy pole "Nazwa bazy danych" |
| Q4 | Brak projektu | Brak automatycznego logowania czasu |
| Q5 | Zadanie domyślne | Auto-create `[SmartMyOdoo] Pula czasu roboczego` |

---

## 🏁 CLOSE CHECKLIST (Bramka Zamykająca)
- [ ] FAZA 1: Migracja DB przechodzi, serwer startuje bez błędów.
- [ ] FAZA 2: Connector XML-RPC działa, endpointy API zwracają poprawne odpowiedzi.
- [ ] FAZA 3: UI dwustanowy — credentials → lista zadań → banner aktywnego zadania.
- [ ] FAZA 4: E2E test pełnego flow przechodzi.
- [ ] `python -m pytest tests/ -v` → ALL GREEN.
- [ ] `ruff check smartmyodoo/` → 0 errors.
- [ ] Sprint zamknięty w YAML frontmatter (`status: DONE`, `closed: <data>`).
