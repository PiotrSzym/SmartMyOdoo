---
sprint_id: "ARCH-F7-03"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-08
goal: "Stabilizacja MVP — prawdziwe odpowiedzi LLM, autologin fix, knowledge seeding, persystentny chat"
prefix: "ARCH-F7"
complexity: 5
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
tags: ["stabilisation", "llm-integration", "autologin", "brain-seeding", "chat-persistence"]
parent_sprint: "FIX-F7-02"
depends_on: ["FIX-F7-02", "HOTFIX-S1.1"]
---

# 🏗️ Sprint ARCH-F7-03 — SmartMyOdoo Stabilisation & Pipeline Integration

> **Architekt:** /arch | **Data:** 2026-06-08
> **Roadmap ref:** `docs/blueprint/tom2-architektura/roadmap.md`
> **Parent Phase:** Faza 7 — Production Hardening & Client-Server Mode

---

## 📊 Audyt Bieżącego Stanu (Spike Recon)

### Baza danych (SQLite WAL)

| Tabela | Rekordy | Status |
|--------|---------|--------|
| `workspaces` | 4 (default, dev, prod, smartTest) | ✅ Persystentne |
| `chat_messages` | 0 | ⚠️ Puste — chat nie zapisuje do DB w trybie HUB |
| `audit_log` | 0 | ⚠️ Puste — audit trail nie jest wyzwalany z poziomu `/api/chat` |
| `proposals` | 0 | ✅ OK (brak operacji Shadow Mode) |
| `token_usage` | 0 | ⚠️ Puste — brak integracji z LLM cost tracking |
| `alembic_version` | 1 | ✅ Migracje aktywne |

### Testy (57 zebranych)

```
tests/                         → 57 testów zebranych
├── e2e/                       → 2 testy (Playwright: chat layout, project tab)
├── security/                  → 3 testy (PII middleware, recognizers)
├── swarm/                     → 19 testów (dispatcher, executor, pipeline, recon, registry, brain)
├── test_api.py                → 21 testów (auth, CRUD, proposals, workspaces)
├── test_audit.py              → 1 test
├── test_chat_repository.py    → 1 test
├── test_database.py           → 3 testy
├── test_log_config.py         → 3 testy
├── test_mcp_pii_integration.py → 1 test
└── ...                        → 3 testy (sandbox, schema, tool_registry, ui_dnd)
```

### Serwer API (FastAPI — port 8000)

| Endpoint | Status | Uwagi |
|----------|--------|-------|
| `GET /api/status` | ✅ | Sprawdza `vault_data.enc` |
| `POST /api/auth` | ✅ | Dual-auth (PIN + Master) |
| `GET /api/workspaces` | ✅ | Auto-seed 3 domyślnych |
| `GET /api/skills` | ✅ | 11 skilli z `SKILL_REGISTRY` |
| `POST /api/chat` | ⚠️ **HOLLOW** | Zwraca hardkodowany template, NIE odpytuje LLM |
| `GET /api/audit` | ✅ | Działa, ale brak danych do wyświetlenia |
| `GET /api/proposals` | ✅ | CRUD działa |
| `GET /api/chat/sessions` | ✅ | ChatRepository działa |
| `POST /api/workspaces/{ws_id}/timesheet` | ✅ | Auto-create task + Pydantic |

### Agent Swarm (Backend)

| Komponent | Plik | Status |
|-----------|------|--------|
| **Dispatcher** | `smartmyodoo/swarm/dispatcher.py` | ✅ Heurystyczny fallback + LLM classify |
| **SkillExecutor** | `smartmyodoo/swarm/executor.py` | ✅ Tool loop + Sandbox + Audit |
| **Tool Registry** | `smartmyodoo/swarm/tools.py` | ✅ 8 narzędzi zarejestrowanych |
| **Skill Registry** | `smartmyodoo/swarm/skills/registry.py` | ✅ 11 skilli (wydmuszki z promptami) |
| **LLM Client** | `smartmyodoo/swarm/llm_client.py` | ⚠️ Wymaga klucza `OPENROUTER_KEY` |
| **Brain (RAG)** | `smartmyodoo/swarm/brain/lancedb_client.py` | ⚠️ Pusta baza — brak seedingu wiedzy |
| **Pipeline FSM** | `smartmyodoo/swarm/pipeline.py` | ⚠️ NIE podłączony do Tool Engine |

### Narzędzia zarejestrowane (`TOOL_REGISTRY`)

| Narzędzie | Typ | Źródło |
|-----------|-----|--------|
| `odoo_search` | READ | MCP → `search_odoo_records()` |
| `odoo_schema` | READ | MCP → `read_odoo_schema()` |
| `odoo_create` | WRITE | MCP → `create_odoo_record()` (Shadow Mode) |
| `search_knowledge_base` | READ | Brain → `SharedBrain.ask_brain()` |
| `scaffold_module` | WRITE | Tworzy szkielet modułu Odoo |
| `read_odoo_log` | READ | Czyta `odoo.log` |
| `search_odoo_code` | READ | Regex grep po `custom_addons/` |
| `rollback_changes` | SYSTEM | Wymusza wycofanie zmian |

### Skills (11 zarejestrowanych)

| Skill | Icon | Shadow | Human Override |
|-------|------|--------|----------------|
| `ODOO_BUSINESS_ANALYST` | 📊 | ❌ | ❌ |
| `ODOO_DEVELOPER` | 💻 | ❌ | ❌ |
| `ODOO_DEVOPS_GITHUB` | 🚀 | ❌ | ❌ |
| `ODOO_SH_LOGS` | 📋 | ❌ | ❌ |
| `ODOO_AUDIT_HISTORY` | 🔍 | ❌ | ❌ |
| `ODOO_CRUD` | 🗄️ | ✅ | ✅ |
| `ODOO_ETL_MANAGER` | 📦 | ✅ | ✅ |
| `FINANCIAL_AUDIT` | 💰 | ❌ | ❌ |
| `SECURITY_AUDIT` | 🔒 | ❌ | ❌ |
| `ODOO_API_EXPERT` | 🔌 | ❌ | ❌ |
| `MAGIC_FIX` | 🪄 | ✅ | ✅ |

### Frontend (Vanilla JS Micro-SPA)

| Komponent | Plik | Status |
|-----------|------|--------|
| **Store** | `smartmyodoo/ui/js/store.js` | ✅ Observer pattern, 4 properties |
| **Sidebar** | `smartmyodoo/ui/js/components/sidebar.js` | ✅ API-driven + D&D reorder |
| **Canvas** | `smartmyodoo/ui/js/components/canvas.js` | ✅ Tab switching |
| **Chat** | `smartmyodoo/ui/js/components/chat.js` | ✅ Sessions, Proposals, Skills badges |
| **Activity** | `smartmyodoo/ui/js/components/activity.js` | ✅ Timeline z audit_log |
| **Skills** | `smartmyodoo/ui/js/components/skills.js` | ✅ Checkboxy + programy predefiniowane |
| **Project** | `smartmyodoo/ui/js/components/project.js` | ✅ 3-state wizard + timesheet |
| **Theme** | `smartmyodoo/ui/js/components/theme.js` | ✅ Dark/light toggle |

---

## 🔴 Zidentyfikowane Luki (Gaps)

| # | Gap | Krytyczność | Opis |
|---|-----|-------------|------|
| **G1** | `/api/chat` nie odpytuje LLM | 🔴 CRITICAL | Endpoint zwraca hardkodowany template (`PERSONA_REPLIES`). Brak wywołania `SkillExecutor`. Agent nie myśli. |
| **G2** | Pipeline FSM rozłączony | 🟡 HIGH | `pipeline.py` (AUTH→RECON→COGNITIVE→ACTUATION→SYNC) istnieje, ale `/api/chat` go nie używa |
| **G3** | Autologin race condition | 🟡 HIGH | URL `?pin=X` nie gwarantuje sekwencyjnego załadowania komponentów (skills, workspaces) po auth |
| **G4** | Brain pusty (brak seedingu) | 🟡 MEDIUM | LanceDB istnieje, ale zero dokumentów → `search_knowledge_base` zwraca mocki |
| **G5** | Chat nie zapisuje do DB | 🟡 MEDIUM | `/api/chat` endpoint nie wywołuje `ChatRepository.save_message()` |

---

## ⚠️ Decyzje wymagające zatwierdzenia

### D1: Priorytet Gapów
**Rekomendacja:** G3 → G1 → G5 → G4 → G2 (od najprostszego blokera do najgłębszej integracji)

### D2: Klucz LLM
Do uruchomienia prawdziwego LLM w `/api/chat` potrzebny jest działający `OPENROUTER_KEY` w ENV lub w Vault.
**Pytanie:** Czy masz aktywny klucz? Jeśli nie, implementuję tryb fallback z mockami.

### D3: Scope sprintu
**Opcja A:** Pełny sprint (wszystkie 5 gapów) — estymacja 4-6h
**Opcja B:** Tylko G1+G3 (krytyczne) — estymacja 1-2h
**Opcja C:** Tylko G3 (frontend fix, już częściowo zrobione) — estymacja 15min

---

## 🧱 Proposed Changes

### FAZA 1: Frontend Auth & State Hydration Fix (G3)

> **📁 Scope:** `smartmyodoo/ui/index.html`, `smartmyodoo/ui/js/components/skills.js`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Auto-login via `URLSearchParams.get('pin')` w `window.onload` | PIN z URL → automatyczne logowanie | ✅ DONE |
| 1.2 | Dodanie `console.log` diagnostyki do `skills.js` | Trace ładowania skilli w konsoli | ✅ DONE |
| 1.3 | Subskrypcja `isAuthenticated` w `SkillPanel` → automatyczny `loadSkills()` | Skille ładują się po logowaniu | [ ] |
| 1.4 | Test manualny: `?pin=1111` → 4 workspaces + 11 skilli widocznych | Full hydration | [ ] |

---

### FAZA 2: Real LLM Responses w `/api/chat` (G1 + G5)

> **📁 Scope:** `smartmyodoo/api.py`, `smartmyodoo/swarm/executor.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Zamienić `PERSONA_REPLIES` template na wywołanie `SkillExecutor.execute()` | Prawdziwa odpowiedź AI | [ ] |
| 2.2 | Zintegrować `ChatRepository.save_message()` w `/api/chat` | Wiadomości zapisane w DB | [ ] |
| 2.3 | Dodać obsługę `OPENROUTER_KEY` z Vault (fallback na ENV) | Klucz automatycznie wstrzykiwany | [ ] |
| 2.4 | **BRAMKA:** Chat z AI → odpowiedź od LLM (nie template) | ✅ End-to-end | [ ] |

---

### FAZA 3: Knowledge Seeding (G4)

> **📁 Scope:** `smartmyodoo/swarm/brain/` (nowy plik)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Nowy skrypt `seed_knowledge.py` — chunking dokumentów z `docs/` | Skrypt istnieje | [ ] |
| 3.2 | Uruchomienie seedingu: `python -m smartmyodoo.swarm.brain.seed_knowledge` | >50 chunków w LanceDB | [ ] |
| 3.3 | **BRAMKA:** `search_knowledge_base("Odoo security")` → trafne wyniki | ✅ RAG działa | [ ] |

---

### FAZA 4: Pipeline Integration (G2) — Opcjonalnie

> **📁 Scope:** `smartmyodoo/swarm/pipeline.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 4.1 | Podłączenie `SkillExecutor` jako fazy COGNITIVE w FSM | Pipeline end-to-end | [ ] |
| 4.2 | Integracja `SandboxManager` jako fazy ACTUATION | Auto-sandbox przed write | [ ] |
| 4.3 | **BRAMKA:** `python -m pytest tests/swarm/test_pipeline.py -v` → GREEN | ✅ Testy przechodzą | [ ] |

---

## 📈 Sprint Metrics

| Metryka | Przed | Cel |
|---------|-------|-----|
| `/api/chat` → LLM response | ❌ Template | ✅ Prawdziwa odpowiedź AI |
| Autologin via URL | ⚠️ Race condition | ✅ Sekwencyjne ładowanie |
| Chat messages w DB | 0 | >0 po rozmowie |
| Knowledge Base docs | 0 | >50 chunków |
| Audit trail entries | 0 | >0 po użyciu narzędzia |
| Testy | 57 zebranych | 57+ GREEN |

---

## 🏁 Definition of Done

- [ ] `http://127.0.0.1:8000/?pin=1111` → automatyczne logowanie + pełny dashboard
- [ ] Zakładka Skille → 11 checkboxów widocznych i klikalnych
- [ ] Chat z AI → prawdziwa odpowiedź LLM (nie template)
- [ ] `chat_messages` tabela zawiera wpisy po rozmowie
- [ ] `python -m pytest tests/ -v` → ALL GREEN
- [ ] Sprint zamknięty w YAML frontmatter (`status: DONE`)
