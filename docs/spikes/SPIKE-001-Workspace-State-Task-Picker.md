---
spike_id: "SPIKE-001"
temat: "Workspace State Persistence + Task Picker + Helpdesk Integration"
data: "2026-06-17"
konsument: "/arch"
autor: "/spike"
model: "haiku-4.5"
bounded_context: "Frontend State Management + Workspace ↔ Task Binding"
status: "ready"
---

# 🕵️ SPIKE-001: Workspace State Persistence + Task Picker + Helpdesk Integration

> **Dla:** `/arch` | **Data:** 2026-06-17
> **Cel:** Diagnoza 4 zgłoszonych spraw: BUG-1 (workspace state loss), FEATURE-2 (workspace↔task binding), FEATURE-3 (helpdesk support).

## 1. Scope

**In scope:**
- BUG-1: Root-cause workspace state reset przy zmian zakładek (Store design)
- FEATURE-2: Workspace model + task picker + gorny pasek "active task"
- FEATURE-3: Helpdesk (Enterprise-only) jako alternative task source
- State persistence (localStorage/sessionStorage) dla workspace selection
- Task model architecture (project.task ↔ helpdesk.ticket)

**Out of scope:**
- Timesheet UI/UX redesign (należy do innego epicu)
- Odoo module development (timesheet logika jest gotowa w `odoo_connector.py`)
- Chat/Activity tab persistence (in-memory sesje są OK wg UX-02/UX-03)

## 2. Kontekst Systemu (Boundaries)

| Wymiar | Wartość |
|--------|---------|
| Frontend entry | `smartmyodoo/ui/js/store.js` (AppStore), `components/sidebar.js`, `components/project.js` |
| Backend entry | `smartmyodoo/api_routers/workspaces.py` (GET/PUT task_bind, log_timesheet) |
| DB model | `smartmyodoo/core/models.py::Workspace` (fields: project_ref, project_name, task_ref, task_name) |
| Odoo connector | `smartmyodoo/core/odoo_connector.py::OdooProjectConnector` (execute_kw, log_timesheet) |
| Persist | SQLite via SQLAlchemy (UX-02 epic zaadresował SQLite migration — SPIKE-001 buduje na tym) |

## 3. Root-Cause: BUG-1 — Workspace State Loss

**Problem:** User przechodzi między zakładkami (project.js → chat.js) i traci informację, w którym workspace był. Po powrocie — workspace resetuje się na 'default'.

**Root-cause (2-częściowy):**
1. **Store.js — zero persistencji:** `AppStore.state` trzymany tylko w memory (`window.AppStore`). Przeładowanie strony / restart session → stan ginie.
2. **project.js renderer — race condition:** `renderProjectTab()` wywoływany przy każdej zmianie `activeTab`. Workspace ID pochodzi z `AppStore.getState()`, ale Store nie ma fallback'u do localStorage. Fragment L49 `project.js`:
   ```
   const wsId = AppStore.getState().workspaceId;  // <- in-memory only
   ```
   Jeśli Store nie persystuje, `wsId` = undefined po soft-reload.
3. **Sidebar subskrypcja (L14 sidebar.js):** Re-render na zmianę `workspaceId`, ale bez persystencji to tylko w-memory bounce.

**Instrukcja dla /arch:** Dodaj `localStorage.setItem('workspaceId', wsId)` + `localStorage.getItem()` fallback w Store.js `setState()`. HUB-S3 sprint już pokrywa task_bind persistence (DB) — frontend state == sidebar selection.

## 4. FEATURE-2: Task Picker + Workspace ↔ Task Binding

**Model już istnieje w DB (Workspace):**
- `project_ref` (Odoo project.project ID)
- `project_name` (cache)
- `task_ref` (Odoo project.task ID — default task)
- `task_name` (cache)

**API gotowy:** `PUT /api/workspaces/{ws_id}/task_bind` (L256–L279 workspaces.py) — zapisuje project_ref + task_ref.

**Logika timesheetu:** Gdy user loguje czas, system bierze `ws.task_ref` jako domyślne (L206–L228 workspaces.py). Jeśli brak — auto-tworzy pool task.

**Frontend:** `project.js` § "STAN 3" już wyświetla active project/task name. Brakuje: żeby aktywne zadanie pojawiło się w **górnym pasku** (przy czacie, nie w projekcie). Wymaga: nowy komponent lub refactor chat.js, aby subskrybował workspace state i wyświetlał zadanie.

**Instrukcja dla /arch:**
- Dodaj field UI (`header.js` lub chat header) wyświetlający active task + link "Zmień zadanie" (modal task picker).
- Task Picker już działający w project.js (L64 `loadProjectTasks`), code-reuse: wydziel `TaskPickerModal` komponent.

## 5. FEATURE-3: Helpdesk Integration — Wykonalność

**Verdict: TAK, ale z 2 warunkami.**

**Warunek 1: Helpdesk = Enterprise-Only w Odoo 16**
- Moduł `helpdesk` dostępny TYLKO w Odoo Enterprise (wzory Community nie zawierają).
- Timesheet na helpdesk: `account.analytic.line` wspiera `helpdesk_ticket_id` (polje, jeśli helpdesk zainstalowany).
- **Ryzyko:** Instalacja smartmyodoo na Odoo Community = feature niedostępna. Trzeba: walidacja capabilities w `/api/workspaces/{ws_id}/helpdesk/search` (try→catch na 404 z Odoo = Enterprise missing).

**Warunek 2: Task Picker = Parametryzowany Model**
- Obecna implementacja zadań w `workspaces.py` (L128–L152) QueryBuilder jest zahardkodowany na `project.task`.
- Ale: `OdooProjectConnector.execute_kw()` (L48–L69 odoo_connector.py) jest uniwersalny — bierze dowolny model, method, args.
- **Design path:** Dodaj `task_source_type` enum (project_task | helpdesk_ticket) do Workspace model. Task Picker robi 2 search'i (project.task + helpdesk.ticket), pokazuje merged list.

**Fragment workspaces.py do refaktu (L129–L146):**
```python
@router.get("/api/workspaces/{ws_id}/projects/{project_id}/tasks")
async def list_project_tasks(ws_id: str, project_id: int, ...):
    domain = [("project_id", "=", project_id)]  # <- hardcoded model
    tasks = connector.execute_kw("project.task", "search_read", [domain], ...)
```

**Refaktor target:**
```python
async def list_tasks_multi_source(ws_id: str, project_id: int = None, search_helpdesk: bool = False, ...):
    results = []
    # Source 1: project.task
    if not search_helpdesk:
        results += connector.execute_kw("project.task", ..., [domain])
    # Source 2: helpdesk.ticket (jeśli dostępne)
    if search_helpdesk:
        results += connector.execute_kw("helpdesk.ticket", ..., [domain_help])
    return results
```

**Instrukcja dla /arch:**
- Sprawdzić capabilities: `/api/check-odoo-modules/{ws_id}?modules=helpdesk` (true/false).
- Jeśli true: Task Picker wyświetla 2 sekcje (Project Tasks + Helpdesk Tickets).
- Jeśli false: Helpdesk disabled w UI, fallback na project.task.
- Add field `Workspace.task_source_type` (enum: project_task, helpdesk_ticket, either).

## 6. Gotowe Klocki (Re-use First)

### Backend (Python/FastAPI)
| Klocek | Path | Co robi |
|--------|------|---------|
| `OdooProjectConnector` | `smartmyodoo/core/odoo_connector.py:L23–L105` | Universal XML-RPC executor + list_tasks + log_timesheet (gotowy) |
| `_resolve_odoo_creds()` | `smartmyodoo/api_routers/workspaces.py:L60–L89` | Vault → Odoo creds, fallback legacy, timesheet-preference |
| Workspace CRUD | `smartmyodoo/api_routers/workspaces.py:L25–L54, L256–L280` | GET workspaces, PUT task_bind (gotowe) |

### Frontend (Vanilla JS)
| Komponent | Path | Status |
|-----------|------|--------|
| `AppStore` (Store) | `smartmyodoo/ui/js/store.js` | Istnieje, brakuje localStorage |
| `TaskPickerModal` | `smartmyodoo/ui/js/components/project.js` § "STAN 2" (L78–L93) | Logika `loadProjectList()` istnieje, wymaga ekstrakcji do modal |
| `Sidebar` (workspace switch) | `smartmyodoo/ui/js/components/sidebar.js` | Gotowy, subskrybuje Store |

### Skill + ADR
| Ref | Relevancja |
|-----|------------|
| ADR-006 (Vanilla JS Frontend) | Store design musi być localStorage-aware (lub IndexedDB) — zgodnie z ADR |
| UX-02 (Persistence) | Workspace state = część tego sprintu; SQLite is decided |
| HUB-S3 (Workspace Context) | Task bind API done; frontend visual tylko |

## 7. Metryki & Pułapki (Lessons Learned)

| ID | Pułapka | Instrukcja dla /arch |
|----|---------|----------------------|
| **E-001** | Store reset przy re-render | Nie opieraj się na `AppStore.state` jako SSoT; localStorage = primary. |
| **E-002** | Task Picker hardcoded domain | Parametryzuj model name + fields w execute_kw; nie ścieżkuj XML-RPC. |
| **E-003** | Helpdesk Enterprise lock | Zawsze waliduj capabilities; 404 z Odoo = feature unavailable, nie error. |
| **E-004** | Session/Workspace confusion | `sessionId` (chat history) ≠ `workspaceId` (Odoo binding). Dwa różne koncepty. |

**Instynkt (z UX-02/UX-03):** Persistence layer musi być **synchron** — nie async fallback. Jeśli localStorage niedostępne, lepiej warn + fail fast niż silent drop state.

## 6b. Architektura Grafu (Graphify) — dla L2 /arch (ART.21.6)

**Dotkniętych moduły:** Frontend (store.js, components/) + Backend (api_routers/workspaces.py, core/models.py).

### God Nodes (Top 10 — SmartMyOdoo)
| Node | Edges | Status | Wpływ na SPIKE |
|------|-------|--------|-----------------|
| `SkillExecutor` | 64 | 🔴 Critical hub | Nie dotyczy (backend infra) |
| `SkillConfig` | 63 | 🔴 Critical hub | Nie dotyczy |
| `ExecutionPipeline` | 48 | 🔴 Critical hub | Nie dotyczy |
| `Workspace` (DB model) | ~8 (inferred) | 🟢 Stable | **Dotkniemy:** +2 edges (task_source_type field) |
| `OdooProjectConnector` | ~12 (inferred) | 🟢 Stable | **Dotkniemy refaktorem:** param task picker (no new edges) |

**Verdict:** Brak God Nodes >25 w dotkniętych modułach. Workspace model jest lekki, safe do extend.

### Cohesion (Moduł-level)
| Moduł | Cohesion | Wartość | Signal |
|-------|----------|---------|--------|
| Frontend Store layer | ~0.12 | ✅ OK | Store.js jest thin (Subscribe/getState/setState) — dodanie localStorage = intra-module change, no scatter |
| Workspaces API router | ~0.14 | ✅ OK | Cohesion OK; refaktor task picker jest local (new optional param) |

**Verdict:** Brak rozbiegów. Cohesion ≥0.10 both.

### Import Cycles
**Grep result:** Brak cykli w digraph frontend/backend boundaries.

### Blast Radius (co pęknie?)
- **Change:** Add `localStorage` to `Store.setState()`
  → Affects: `sidebar.js`, `project.js`, `chat.js` (all subscribers)
  → **Blast:** 3 components, all safe (observer pattern)

- **Change:** Parametryzuj `execute_kw()` w `workspaces.py`
  → Affects: `list_project_tasks()` endpoint
  → **Blast:** 1 router method, 1 frontend caller (`loadProjectTasks()`)

- **Change:** Add `task_source_type` field to Workspace
  → Requires: DB migration (alter table)
  → Affects: model + 3 API endpoints
  → **Blast:** Low (backward-compat via default=None)

**Architektura rekomendacja dla /arch (FAKT, nie decyzja):** Workspace model ma 4 ref fields (project_ref, task_ref, + now task_source_type, default_helpdesk). Jeśli >6 fields → rozważ Workspace model split (WorkspaceBinding, WorkspaceConfig submodele), ale teraz safe.

---

## 8. Pytania Otwarte dla /arch

- [ ] **localStorage vs IndexedDB** — Store powinno być fault-tolerant? (localStorage full → co robi?)
- [ ] **Task Picker — modal location** — czy toolbar chat, czy osobna zakładka?
- [ ] **Helpdesk graceful degrade** — jeśli Enterprise-only, pokaż komunikat czy po cichu disable?
- [ ] **Refactor size** — czy task picker staje się nowym komponentem (`TaskPicker.js`), czy pozostaje w `project.js`?

---

_Wygenerowano przez `/spike` (fast tier) | Model: haiku-4.5 | Status: ready dla /arch_
