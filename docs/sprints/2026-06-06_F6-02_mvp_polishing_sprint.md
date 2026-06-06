---
sprint_id: "F6-02"
workspace: "SmartMyOdoo"
status: "IN_PROGRESS"
created: 2026-06-06
closed: null
goal: "MVP Polishing — persystentna historia chatów (Smart Context), automatyczny Rollback (Scratchpad DB), Audit Trail, Activity UI, Task Binding do Odoo"
prefix: "F6"
complexity: 7
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
tags: ["chat-history", "rollback", "scratchpad-db", "audit-trail", "activity-feed", "task-binding", "smart-context", "mvp"]
arch_decisions:
  D1_chat_context: "SMART CONTEXT — ładuj skróty/keywords z poprzednich sesji, pełny chat on-demand"
  D2_rollback: "MANDATORY — Scratchpad DB przy KAŻDYM write tool (odoo_create/update/delete)"
  D3_task_source: "ODOO ONLY — project.task via XML-RPC; Jira/Linear → roadmap Faza 8"
  D4_pipeline_fsm: "DEFERRED — Pipeline FSM (pipeline.py) nie jest częścią F6-02, zamrożona jako Faza 7"
  D5_ui_framework: "VANILLA JS — kontynuacja istniejącego Micro-SPA (store.js + components)"
depends_on: ["F6-01"]
---

# 🚀 Sprint: F6-02 MVP Polishing — Historia, Rollback, Audit, Karty Pracy

> **Architekt:** /arch | **Tryb:** Implementation
> **Data:** 2026-06-06 | **Bazuje na:** Audycie kodu po zamknięciu F6-01 + decyzji o Feature Freeze Fazy 7

---

## 📈 PROGRESS BAR
- [x] EP-1.1: Model `ChatMessage` w `core/models.py`
- [x] EP-1.2: `core/chat_repository.py` (Smart Context Pattern)
- [x] EP-2.1: `swarm/sandbox.py` (SandboxManager)
- [x] EP-3.1: `core/audit.py` (log_tool_call + sanityzacja)
- [x] EP-CORE: `swarm/executor.py` — integracja Chat + Audit + Sandbox
- [x] EP-1.4: `cli.py` — sesje, Smart Context, `/sessions`
- [x] EP-1.5: `__main__.py` — wiring (DB, ChatRepo, Sandbox → Executor → CLI)
- [x] EP-1.5+3.3: API endpointy (`/api/chat/sessions`, `/api/audit`)
- [x] EP-4.2: `activity.js` — timeline aktywności agenta
- [ ] EP-4.1+4.3: Wiring Activity do `index.html` + `canvas.js`
- [ ] EP-5.1: Rozszerzenie `Workspace` o `task_ref` (model gotowy, API brakuje)
- [ ] EP-5.2: API: search tasks, bind task, log time
- [ ] EP-5.3: UI Settings — sekcja "Powiązane Zadanie"
- [ ] **Testy jednostkowe** (chat_repo, audit, sandbox)
- [ ] **Release Gate**

---

## 📋 Sekcja A — Business Discovery & Problem Definition

### Problem 1: Agent traci pamięć (Chat History)
CLI i Web UI przechowują konwersacje wyłącznie w RAM. Restart = utrata kontekstu. Użytkownik musi za każdym razem tłumaczyć od nowa.

**Rozwiązanie:** Tabela `ChatMessage` w SQLite + **Smart Context Pattern** — przy wznowieniu sesji LLM dostaje skróty (preview 120 znaków + liczba wiadomości) z poprzednich sesji. Pełna konwersacja ładowana on-demand, gdy temat bieżący dotyczy wcześniejszego chatu.

### Problem 2: Brak safety net przy write operations (Rollback)
Agent może wywołać `odoo_create()` i uszkodzić dane w produkcji bez możliwości cofnięcia.

**Rozwiązanie:** `SandboxManager` opakowujący istniejący `OdooDBManager.duplicate_database()`. Przy KAŻDYM write tool call automatycznie klonuje bazę Odoo (Scratchpad DB). Błąd → rollback (drop klona). Sukces → klon zachowany do audytu.

### Problem 3: Pusta tabela AuditLog (Audit Trail)
Tabela SQLite istnieje od Fazy 1, ale Executor nie zapisuje do niej wywołań narzędzi. Brak śladu "kto/co/kiedy".

**Rozwiązanie:** Hook w Executor po każdym `TOOL_REGISTRY[func_name]["callable"](**args)` → `audit.log_tool_call()` z sanityzacją (Deny List na hasła/klucze).

### Problem 4: Brak wizualnej historii aktywności (UI)
Web UI ma piękny chat, ale nie pokazuje co agent robił "pod spodem" (jakie narzędzia wywoływał).

**Rozwiązanie:** Nowa zakładka "📋 Aktywność" z pionowym timeline (wzorzec GitHub Activity Feed).

### Problem 5: Workspace nie powiązany z zadaniem (Task Binding)
Brak pola `odoo_task_id`. Nie ma automatycznego raportowania czasu pracy z powrotem do Odoo.

**Rozwiązanie:** Pole `task_ref` + `task_name` w modelu `Workspace`. Endpoint proxy do `project.task.search_read`. Tylko Odoo (Jira → roadmap Faza 8).

---

## 🏛️ Sekcja A.1 — Decyzje Architektoniczne (ROZSTRZYGNIĘTE)

| # | Decyzja | Rozwiązanie | Uzasadnienie |
|---|---------|-------------|--------------|
| D1 | Kontekst LLM przy wznowieniu sesji | **Smart Context** | Ładuj skróty, nie pełne wiadomości — oszczędność tokenów + prywatność |
| D2 | Kiedy tworzyć Scratchpad DB | **Przy KAŻDYM write tool** | Bezpieczeństwo > wygoda; wyłączenie via `SANDBOX_ENABLED=false` |
| D3 | Źródło zadań | **Tylko Odoo** | MVP scope; Jira/Linear do roadmapy |
| D4 | Pipeline FSM | **DEFERRED** | Zamrożona jako Faza 7, zbyt duży scope |
| D5 | Framework UI | **Vanilla JS (Micro-SPA)** | Kontynuacja istniejącego stosu, brak potrzeby migracji |

---

## ✅ Metryka sukcesu (DoD)

### Functional
1. CLI: `python -m smartmyodoo chat` → pokazuje poprzednie sesje → `y` wznawia kontekst.
2. CLI: Komenda `/sessions` → tabelka Rich z ostatnimi sesjami.
3. API: `GET /api/chat/sessions?workspace_id=X` → lista sesji z preview.
4. API: `GET /api/audit?workspace_id=X` → wpisy z narzędzi.
5. Web UI: Zakładka "📋 Aktywność" → timeline z ikonkami per tool.
6. Executor: Każde wywołanie narzędzia → wpis w tabeli `AuditLog`.
7. Executor: `odoo_create()` → automatyczny Scratchpad DB.

### Quality Gates
8. `python -m pytest tests/ -v` → ALL GREEN.
9. `ruff check smartmyodoo/` → 0 errors.
10. Sprint zamknięty w YAML frontmatter.

---

## 🧱 Sekcja B — Podział Zadań

### EP-1: Chat History Persistence (🔴 P0 — 3-4h)

| # | Plik | Zadanie | Status |
|---|------|---------|--------|
| 1.1 | `core/models.py` | Model `ChatMessage` (workspace_id, session_id, role, content, metadata_json) | ✅ |
| 1.2 | `core/chat_repository.py` [NEW] | `ChatRepository` — save, get, list_sessions, get_smart_context | ✅ |
| 1.3 | `swarm/executor.py` | Zapis user/assistant do historii po każdej turze + Smart Context prefix | ✅ |
| 1.4 | `cli.py` | Tabela sesji, prompt "Kontynuować?", komenda `/sessions` | ✅ |
| 1.5 | `api.py` | Endpointy: `GET /api/chat/sessions`, `GET /api/chat/sessions/{id}/messages` | ✅ |
| 1.6 | `ui/js/components/chat.js` | Panel sesji w UI (lewy sidebar w widoku chat) | ⏳ |

### EP-2: Rollback Safety Net (🟡 P1 — 2-3h)

| # | Plik | Zadanie | Status |
|---|------|---------|--------|
| 2.1 | `swarm/sandbox.py` [NEW] | `SandboxManager` — enter/exit sandbox, is_write_tool | ✅ |
| 2.2 | `swarm/executor.py` | Pre/post hooks: auto-enter before write, rollback on error | ✅ |
| 2.3 | `swarm/tools.py` | Tool `rollback_changes` w TOOL_REGISTRY | ⏳ |

### EP-3: Audit Trail Enrichment (🟡 P1 — 1-2h)

| # | Plik | Zadanie | Status |
|---|------|---------|--------|
| 3.1 | `core/audit.py` [NEW] | `log_tool_call()` + `log_event()` z Deny List sanityzacją | ✅ |
| 3.2 | `swarm/executor.py` | Audit po każdym tool call (success + error) | ✅ |
| 3.3 | `api.py` | Endpoint `GET /api/audit` | ✅ |

### EP-4: UI Polish (🟡 P1 — 3-4h)

| # | Plik | Zadanie | Status |
|---|------|---------|--------|
| 4.1 | `ui/js/components/chat.js` | Panel sesji (lewy sidebar w chat) | ⏳ |
| 4.2 | `ui/js/components/activity.js` [NEW] | Timeline aktywności agenta | ✅ |
| 4.3 | `ui/index.html` + `canvas.js` | Nowa zakładka "Aktywność" + wiring | ⏳ |

### EP-5: Task Binding & Timesheets (🟢 P2 — 2-3h)

| # | Plik | Zadanie | Status |
|---|------|---------|--------|
| 5.1 | `core/models.py` | `Workspace.task_ref`, `Workspace.task_name` | ✅ |
| 5.2 | `api.py` | Endpointy: search tasks, bind task, log time | ⏳ |
| 5.3 | `ui/index.html` | Settings → sekcja "Powiązane Zadanie" | ⏳ |

---

## 📦 Sekcja C — Zależności

### Nowe pliki (utworzone w tym sprincie)
| Plik | Cel |
|------|-----|
| `smartmyodoo/core/chat_repository.py` | Persystencja chatu (Smart Context Pattern) |
| `smartmyodoo/core/audit.py` | Audit Trail z sanityzacją |
| `smartmyodoo/swarm/sandbox.py` | SandboxManager (Rollback) |
| `smartmyodoo/ui/js/components/activity.js` | Timeline UI |

### Istniejące moduły re-użyte
| Moduł | Użycie |
|-------|--------|
| `swarm/db_manager.py` | `OdooDBManager` — owinięty przez `SandboxManager` |
| `core/log_config.py` | Wzorzec `SecretFilter` → reuse w `audit.py` Deny List |
| `swarm/project_logger.py` | `FSMProjectLogger` — fundament dla Task Binding (EP-5) |
| `core/database.py` | SQLAlchemy engine + `SessionLocal` |

### Brak nowych pakietów Python
Wszystkie zależności (SQLAlchemy, Rich, prompt_toolkit, litellm) zostały dodane w F6-01.

---

## ❓ Otwarte Kwestie (rozstrzygnięte)

| # | Kwestia | Decyzja |
|---|---------|---------|
| Q1 | Głębokość historii | Smart Context — skróty, nie pełne wiadomości |
| Q2 | Rollback scope | Przy KAŻDYM write tool, bez wyjątków |
| Q3 | Task source | Tylko Odoo; Jira/Linear → roadmap Faza 8 |

---

## 🏁 CLOSE CHECKLIST (Bramka Zamykająca)
- [ ] EP-1: Chat History działa w CLI i API.
- [ ] EP-2: Sandbox tworzy Scratchpad przy write tools.
- [ ] EP-3: Audit loguje każde wywołanie narzędzia.
- [ ] EP-4: Zakładka "Aktywność" w Web UI.
- [ ] EP-5: Task Binding w Settings.
- [ ] `python -m pytest tests/ -v` → ALL GREEN.
- [ ] `ruff check smartmyodoo/` → 0 errors.
- [ ] Sprint zamknięty w YAML frontmatter (`status: DONE`, `closed: <data>`).
