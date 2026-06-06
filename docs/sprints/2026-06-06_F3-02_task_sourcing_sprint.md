---
sprint_id: "F3-02"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-06
closed: null
goal: "Użytkownik wybiera Projekt→Zadanie w UI. System pobiera opis (User Story) i loguje czas (Timesheet) do Odoo."
prefix: "F3"
complexity: 5
roadmap_ref: "roadmap.md → EPIC-3"
epic_ref: "EPIC-F3-TASK"
tags: ["task-sourcing", "odoo-project", "timesheet", "xml-rpc", "tdd"]
---

# 🚀 Sprint: F3-02 MVP Task Picker (Projekt → Zadanie → Timesheet)

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-06

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Mózg musi mieć kontekst biznesowy (User Story). Użytkownik w UI wybiera Projekt i Zadanie z Odoo, system pobiera `description` i przekazuje je do Dispatchera. Na koniec sesji loguje czas w Odoo (Timesheet).

### User Stories
| ID | As a... | I want... | So that... |
|----|---------|-----------|------------|
| US-F3-02-1 | Konsultant | wybrać Projekt i Zadanie z listy | agent wie nad czym pracuję |
| US-F3-02-2 | System | pobrać opis zadania (description) | Dispatcher ma kontekst do routingu |
| US-F3-02-3 | Konsultant | automatycznie zalogować czas | nie muszę ręcznie wpisywać Timesheetów |

### Metryka sukcesu (DoD)
`pytest tests/swarm/test_task_sourcing.py -v` → ALL PASSED (min. 3 testy + 1 error handling)

### ⚖️ ZASADY SPRINTU
- 🔴 **TDD OBOWIĄZKOWY:** Każda metoda dotykająca `odoo_client` (zewnętrzna baza!) musi mieć test z mockiem.
- 🔴 **SCOPE:** `smartmyodoo/swarm/task_sourcing.py` (NEW) + `tests/swarm/test_task_sourcing.py` (NEW)

---

## 🧱 Sekcja B — Podział Zadań

### Sekcja B1 — FAZA 1: Task Sourcing Logic (Backend)

> **📁 Scope:** `smartmyodoo/swarm/task_sourcing.py`, `smartmyodoo/swarm/models.py`, `tests/swarm/test_task_sourcing.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Model `TaskDTO` (Pydantic): `id, provider, title, status, description, project_name, url` | Import OK | [ ] |
| 1.2 | 🔴 RED — Test `fetch_projects()`: mockowany OdooClient zwraca listę projektów | Failing | [ ] |
| 1.3 | 🟢 GREEN — `TaskSourcer.fetch_projects()` → `search_read('project.project', [], fields=['id','name','description'], limit=100)` | PASS | [ ] |
| 1.4 | 🔴 RED — Test `fetch_tasks(project_id)`: mockowany OdooClient | Failing | [ ] |
| 1.5 | 🟢 GREEN — `TaskSourcer.fetch_tasks(project_id)` → `search_read('project.task', [('project_id','=',pid)])` | PASS | [ ] |
| 1.6 | 🔴 RED — Test `log_timesheet(task_id, hours, description)`: mock `create('account.analytic.line')` | Failing | [ ] |
| 1.7 | 🟢 GREEN — `TaskSourcer.log_timesheet()` → `create('account.analytic.line', [{...}])` | PASS | [ ] |
| 1.8 | 🔴 RED — Test: `fetch_projects()` gdy Odoo offline → graceful fail (pusta lista) | Failing | [ ] |
| 1.9 | 🟢 GREEN — Error handling: `ConnectionError` → `return []` | PASS | [ ] |
| 1.10 | **BRAMKA:** `pytest tests/swarm/test_task_sourcing.py -v` | ✅ ALL GREEN | [ ] |

---

### Sekcja B2 — FAZA 2: REST Endpoints

> **📁 Scope:** `smartmyodoo/api.py`, `tests/test_api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Endpoint `GET /api/projects` — lista projektów z Odoo | 200 + JSON | [ ] |
| 2.2 | Endpoint `GET /api/tasks/{project_id}` — lista zadań | 200 + JSON | [ ] |
| 2.3 | **BRAMKA:** `pytest tests/test_api.py -k "projects or tasks" -v` | ✅ GREEN | [ ] |

---

## 📊 PROGRESS BAR

| # | Faza | /arch | /dev | /qa | Status |
|---|------|:-----:|:----:|:---:|:------:|
| 1 | Task Sourcing Logic | ✅ | ⬜ | ⬜ | 🔵 |
| 2 | REST Endpoints | ✅ | ⬜ | ⬜ | 🔵 |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|-----------------|
| V1 | Testy Sourcing | `pytest tests/swarm/test_task_sourcing.py -v` | ALL GREEN (min. 4 testy) |
| V2 | API Endpoints | `pytest tests/test_api.py -k "projects or tasks" -v` | ALL GREEN |
| V3 | Graceful Fail | Test ConnectionError → pusta lista | Brak crash |

---
_Wygenerowane przy użyciu szablonów TeamEngine._
