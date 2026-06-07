---
sprint_id: "FIX-F7-02"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-07
closed: 2026-06-07
goal: "Hotfix QA — usunięcie tracked binaries, scalenie duplikatów API, Pydantic validation, vault fallback consistency"
prefix: "FIX-F7"
complexity: 3
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
tags: ["hotfix", "qa-review", "cleanup", "api-consolidation", "pydantic", "vault", "gitignore"]
parent_sprint: "F7-01"
qa_report_ref: "qa_review_hotfix.md"
arch_decisions:
  D1_single_timesheet: "JEDEN ENDPOINT — scalenie /timesheet i /log_time w jeden POST /api/workspaces/{ws_id}/timesheet z auto-create task"
  D2_global_vault: "DEFAULT_ODOO — globalny klucz vault dla wszystkich workspace'ów (jeden Odoo do projektów/timesheetów)"
  D3_pydantic_strict: "PYDANTIC EVERYWHERE — każdy endpoint z payloadem musi używać BaseModel, nie dict"
  D4_no_binaries: "ZERO BINARIES — żadne pliki .db, .png, .txt diagnostyczne w tracked files"
depends_on: ["F7-01"]
---

# 🔧 Sprint: FIX-F7-02 Hotfix QA — Porządki po F7-01

> **Architekt:** /arch | **QA Report:** qa_review_hotfix.md
> **Data:** 2026-06-07 | **Ocena wejściowa:** 6.3/10 | **Cel:** 8.5+/10

---

## 📋 Sekcja A — Problem Definition

### Problem 1: Pliki binarne śledzone w Git (BUG-K01)
Pliki `.db-shm`, `.db-wal`, `screenshot.png`, `screenshot_dashboard.png`, `diff.txt`, `check_vault.py` są tracked w repozytorium mimo reguł `.gitignore`. Powoduje to fałszywy dirty state przy każdym restarcie serwera i zaśmieca historię commitów.

### Problem 2: Duplikacja endpointów timesheet (BUG-K02)
Dwa endpointy realizują tę samą logikę:
- `POST /api/workspaces/{ws_id}/timesheet` (nowy, Pydantic) ✅
- `POST /api/workspaces/{ws_id}/log_time` (stary, dict, brak fallbacku vault) ❌

### Problem 3: Niespójny vault fallback (BUG-K04)
`/log_time` szuka `{ws_id}_ODOO` bez fallbacku na `default_ODOO`. Przy globalnym kluczu → zawsze 400 error.

### Problem 4: Brak Pydantic walidacji na task_bind (BUG-K03)
`PUT /api/workspaces/{ws_id}/task_bind` przyjmuje `payload: dict` → dowolny JSON przechodzi bez walidacji.

### Problem 5: Duplikacja w .gitignore (WARN-03)
Linie 53-55 i 58-61 zawierają identyczne reguły (`*.db`, `*.db-wal`, `*.db-shm`).

---

## 🏛️ Sekcja A.1 — Decyzje Architektoniczne

| # | Decyzja | Rozwiązanie | Uzasadnienie |
|---|---------|-------------|--------------|
| D1 | Ile endpointów timesheet? | **Jeden: `/timesheet`** | Scalamy logikę auto-create z `/log_time` do `/timesheet`, usuwamy `/log_time` |
| D2 | Klucz Vault | **`default_ODOO` (globalny)** | Jeden Odoo = jeden klucz; `_get_odoo_connector()` z fallbackem |
| D3 | Walidacja payloadów | **Pydantic BaseModel** | `TaskBindRequest`, `TimesheetRequest` — strict typing |
| D4 | Tracked binaries | **Zero tolerance** | `git rm --cached` + rozszerzenie `.gitignore` |

---

## ✅ Metryka sukcesu (DoD)

### Functional
1. `git ls-files -- "*.db*" "*.png" "diff.txt" "check_vault.py"` → 0 wyników (poza `docs/Wymagania.txt`, `requirements.txt`)
2. Jeden endpoint timesheet: `POST /api/workspaces/{ws_id}/timesheet` z `TimesheetRequest(BaseModel)`
3. `PUT /api/workspaces/{ws_id}/task_bind` z `TaskBindRequest(BaseModel)`
4. Stary endpoint `/log_time` usunięty
5. `.gitignore` bez duplikacji

### Quality Gates
6. `python -m pytest tests/ -v` → ALL GREEN
7. `ruff check smartmyodoo/` → 0 errors
8. `mypy smartmyodoo/` → 0 errors
9. Sprint zamknięty w YAML frontmatter

---

## ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza N+1 nie startuje dopóki bramka Fazy N nie jest zielona.

#### Zasada 2: SCOPE ISOLATION 🔴
Zmiany wyłącznie w plikach wymienionych w scope. Zero zmian w `swarm/`, `mcp/`, `vault/vault.py`.

#### Zasada 3: NO FUNCTIONAL REGRESSION 🔴
Frontend `project.js` nie wymaga zmian — wyłącznie backend cleanup.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności

```
┌─────────────────────────────────────────────────────┐
│  FAZA 1: Git Cleanup (BUG-K01, WARN-03)            │
│  [1.1] git rm --cached binaries/diagnostics        │
│  [1.2] Deduplikacja + rozszerzenie .gitignore       │
│  [1.3] Commit: chore: remove tracked artifacts      │
└──────────────┬──────────────────────────────────────┘
               │ ✅ BRAMKA: git ls-files → 0 binaries
               ▼
┌─────────────────────────────────────────────────────┐
│  FAZA 2: API Consolidation (BUG-K02, K03, K04)     │
│  [2.1] Rozszerzenie TimesheetRequest o auto-create  │
│  [2.2] Dodanie TaskBindRequest Pydantic model       │
│  [2.3] Usunięcie starego /log_time endpoint         │
│  [2.4] Weryfikacja: serwer startuje + API smoke     │
└──────────────┬──────────────────────────────────────┘
               │ ✅ BRAMKA: pytest + ruff + mypy GREEN
               ▼
┌─────────────────────────────────────────────────────┐
│  FAZA 3: Weryfikacja & Zamknięcie                   │
│  [3.1] Pre-commit hooks pass                        │
│  [3.2] git commit + push                            │
│  [3.3] Zamknięcie sprintu                           │
└─────────────────────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Git Cleanup

> **📁 Scope:** `.gitignore`, tracked binaries

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | `git rm --cached smartmyodoo.db-shm smartmyodoo.db-wal screenshot.png screenshot_dashboard.png diff.txt check_vault.py` | Pliki usunięte z index, fizycznie pozostają na dysku | [ ] |
| 1.2 | Deduplikacja `.gitignore`: usunąć linie 58-61 (duplikaty), dodać `check_vault.py`, `screenshot*.png`, `diff.txt` | Gitignore czytelny, bez powtórzeń | [ ] |
| 1.3 | **BRAMKA:** `git ls-files -- "*.db*" "*.png" "diff.txt" "check_vault.py"` → zwraca wyłącznie `docs/Wymagania.txt` i `requirements.txt` | ✅ Zero binaries w tracked | [ ] |

---

### Sekcja B2 — FAZA 2: API Consolidation

> **📁 Scope:** `smartmyodoo/api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Rozszerzenie `TimesheetRequest` o pola: `task_id: Optional[int] = None`, `is_nominal: bool = False`. Scalenie logiki auto-create task ze starego `/log_time` do `/timesheet` | Endpoint obsługuje: podany `task_id` ✅, fallback na `ws.task_ref` ✅, auto-create ✅ | [ ] |
| 2.2 | Nowy model `TaskBindRequest(BaseModel)` z polami `project_ref: str`, `project_name: str`, `task_ref: str = ""`, `task_name: str = ""`. Zmiana `bind_workspace_task(payload: dict)` → `bind_workspace_task(payload: TaskBindRequest)` | Strict Pydantic validation na `PUT /task_bind` | [ ] |
| 2.3 | Usunięcie endpointu `POST /api/workspaces/{ws_id}/log_time` (L572-632) — dead code | Endpoint nie istnieje w routerze | [ ] |
| 2.4 | **BRAMKA:** `python -m smartmyodoo.api` startuje + `curl POST /api/workspaces/smartTest/timesheet` zwraca odpowiedź | ✅ Serwer działa, API odpowiada | [ ] |

---

### Sekcja B3 — FAZA 3: Weryfikacja & Zamknięcie

> **📁 Scope:** `tests/`, `docs/sprints/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Pre-commit hooks (Ruff, Mypy, Bandit) → ALL PASS | ✅ Zero errors | [ ] |
| 3.2 | `git commit -m "fix(FIX-F7-02): QA hotfix — cleanup, API consolidation, Pydantic strict"` + `git push` | Commit w historii | [ ] |
| 3.3 | Zamknięcie sprintu: `status: DONE`, `closed: 2026-06-07` | Sprint formalnie zamknięty | [ ] |

---

## 📦 Sekcja C — Zależności

### Pliki modyfikowane
| Plik | Zmiana |
|------|--------|
| `.gitignore` | Deduplikacja + nowe reguły |
| `smartmyodoo/api.py` | Scalenie endpointów, Pydantic models, usunięcie `/log_time` |

### Pliki usuwane z Git index (nie z dysku)
| Plik | Powód |
|------|-------|
| `smartmyodoo.db-shm` | Runtime binary — zmienia się przy każdym restarcie |
| `smartmyodoo.db-wal` | WAL journal — runtime |
| `screenshot.png` | Debug artifact |
| `screenshot_dashboard.png` | Debug artifact |
| `diff.txt` | Debug artifact |
| `check_vault.py` | Diagnostic script |

### Brak nowych pakietów Python
Zmiany wyłącznie w istniejącym kodzie.

---

## 🏁 CLOSE CHECKLIST (Bramka Zamykająca)
- [ ] FAZA 1: Zero binaries w `git ls-files`
- [ ] FAZA 2: Jeden endpoint `/timesheet`, brak `/log_time`, `TaskBindRequest` Pydantic
- [ ] FAZA 3: Pre-commit hooks pass, commit + push
- [ ] `ruff check smartmyodoo/` → 0 errors
- [ ] `mypy smartmyodoo/` → 0 errors
- [ ] Sprint zamknięty w YAML frontmatter
