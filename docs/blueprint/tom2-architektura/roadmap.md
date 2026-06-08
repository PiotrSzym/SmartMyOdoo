# 🛤️ Roadmap (Smart Odoo AI Agent)

## Faza 0: Infrastruktura i Procedury (✅ Wdrożone / ⏳ W trakcie)
- **TeamEngine v5.0:** Orkiestracja farmy agentów (Scout, Pol, Dev, QA, Arch).
- **Conductor System:** Każde zadanie kodowania musi być otwierane jako Track/Epic.
- **OdooE2E / TDD (The Iron Law):** Procedura Double-Loop TDD. Zakaz pisania kodu bez "oblanego" testu.
- **Pre-Commit Iron Gate (QA-01):** ✅ Wdrożone - Zabezpieczenie kodu (Ruff, Mypy, Bandit, pre-commit).
- **KSeF Readiness:** Gotowość technologiczna (pipeline `v7` z projektu `KSEF/`).
- **OCA Guidelines:** Standard modułów Odoo (PEP8, Humble Object, Repository Pattern).
- **Stack Technologiczny:** Zdefiniowany w `docs/blueprint/tom2-architektura/TECH_STACK.md`.

---

## Faza 1: Fundament — SmartMyVault + Packaging (✅ Wdrożone)
**Cel:** Zunifikowanie projektu jako jeden pakiet Python `smartmyodoo`.

### 1.1 Migracja Backend: Flask → FastAPI
- ✅ Przepisanie `vault_server.py` (191 LOC) na async FastAPI + Uvicorn.
- ✅ Dodanie walidacji Pydantic do wszystkich endpointów API.
- ✅ Auto-generowany Swagger UI na `/docs`.
- **Stack:** `fastapi>=0.115.0`, `uvicorn>=0.32.0`, `pydantic>=2.10.0`

### 1.2 Migracja Storage: JSON → SQLite
- ✅ Utworzenie `smartmyodoo.db` z tabelami: `proposals`, `token_usage`, `audit_log`, `agent_tasks`.
- ✅ Shadow Mode (`proposals.json`) → tabela `proposals`.
- ✅ Token Governor (in-memory) → tabela `token_usage` (persystentna historia).
- **WYJĄTEK:** `vault_data.enc` zostaje jako zaszyfrowany plik Fernet (nie do SQLite!).
- **Stack:** `sqlite3` (stdlib Python)

### 1.3 Packaging: Jeden punkt wejścia
- ✅ Struktura pakietu `smartmyodoo/` z podmodułami (`vault/`, `mcp/`, `dashboard/`).
- ✅ Uruchamianie: `python -m smartmyodoo serve|mcp|vault`.
- ✅ Zachowanie obecnego Premium UI (`index.html` — Vanilla JS + Tailwind CDN).

### 1.4 Schema Migrations (ADR-010)
- ✅ Wdrożenie `alembic>=1.14.0` jako systemu migracji SQLite.
- ✅ Auto-upgrade przy starcie (`alembic upgrade head` przed FastAPI).
- ✅ Backup-before-migrate: `smartmyodoo.db` → `smartmyodoo.db.bak.{timestamp}` (retencja 3 kopie).

### 1.5 Logging & Error Sanitization (ADR-011)
- ✅ Centralny `log_config.py` z filtrem `SecretFilter` (Deny List: hasła, klucze API, PII).
- ✅ Globalny `@app.exception_handler` — brak stacktrace'ów w odpowiedziach produkcyjnych.
- ✅ Poziomy logowania: ERROR/WARNING/INFO/DEBUG z polityką sanityzacji.

---

## Faza 2: Odoo MCP Bridge (✅ Wdrożone)
**Cel:** Pełna łączność odczyt/zapis z Odoo (v16-v19) przez XML-RPC.
- ✅ Rozbudowa `OdooClient` o obsługę `write`, `create`, `unlink`.
- ✅ Async wrapper na `xmlrpc.client` (lub migracja na `aiohttp`).
- ✅ Integracja z `vault.py run` — sekrety wstrzykiwane przez ENV.
- **Fetch Guard (ADR-012):** ✅ Paginacja `search_read` (default 100, max 500). Zakaz pobierania pól binarnych w batch.
- **Stack:** `xmlrpc.client` (stdlib), `mcp>=1.2.0` (FastMCP stdio)

---

## Faza 3: Token Governor, Multi-Workspace UI & Project Hub (✅ Wdrożone)
**Cel:** Monitorowanie budżetu LLM, wsparcie wielu projektów jednocześnie w GUI, konfiguracja integracji z systemami zewnętrznymi (Odoo v16 / Jira) oraz powiązanie Workspace z zadaniami.
- **LLM Context Guardrails (ADR-012):** ✅ Hard limits na input tokens per model, Session Budget ($2/sesja, $10/dzień), Context Compression przy 70% okna.
- **Data Retention & GDPR (ADR-013):** ✅ Kolumna `workspace_id` w każdej tabeli, Auto-Purge (audit 90d, proposals 30d, tokens 365d), endpoint `DELETE /api/workspace/{id}/purge`.
- ✅ Przejście interfejsu (Vanilla JS) na architekturę Multi-Workspace (Micro-SPA) ze zmianą kontekstów (styl Discord/Slack).
- **Project Hub — Integration Setup Wizard (US 7.1):**
  - ✅ Ekran ⚙️ Ustawienia → Dodaj Połączenie z systemem zarządzania projektami.
  - ✅ Wizard: Wybór systemu (`Odoo v16` | `Jira`) → Credentials (URL, Login, Hasło) → `[ 🔌 Testuj Połączenie ]` → Zapis do Vault.
  - ✅ Możliwość konfiguracji wielu połączeń jednocześnie (np. Odoo wewnętrzne + Odoo klienta).
  - Credentials szyfrowane w `vault_data.enc` pod kluczem `PROJECT_HUB_<nazwa>`.
- **Task Picker (US 7.2):**
  - ✅ Przy tworzeniu `[ + Nowy Workspace ]` → dropdown z połączeniami → wyszukiwarka zadań z autouzupełnianiem (XML-RPC `project.task.search_read`).
  - ✅ Podgląd: nazwa zadania, klient, przypisana osoba, status.
- **Fast Connect & Workspace Memory:** ✅ Każdy Workspace przechowuje konfigurację i *Lessons Learned*. Aby wrócić do pracy, podajesz tylko 4-cyfrowy PIN, a agenty mają od razu pełen kontekst.
- **Task Binding (US 4.3):** ✅ Każdy Workspace jest powiązany z konkretnym zadaniem w Odoo Project (`project.task`) lub Jira.
- **Auto-Timesheets (US 4.1 + 4.3):** ✅ Czas pracy (estymowany/rzeczywisty/hybrydowy). Przy zamknięciu system automatycznie tworzy wpis Timesheet w Odoo v16 (`hr.analytic.line`) z notatką wygenerowaną przez AI.
- **AI Session Summary (US 4.4):** ✅ Po zakończeniu sesji AI generuje zwięzły raport z Audit Logu i wysyła go jako komentarz (`mail.message`) do powiązanego zadania w Odoo.
- **Synchronizacja Dwukierunkowa (US 7.3):** ✅ Zamknięcie Workspace → opcjonalna zmiana statusu zadania w Odoo. Polling co 60s.
- **Raport Miesięczny (US 4.5):** ✅ Tabela + wykresy godzin i kosztów tokenów per miesiąc/klient. Eksport CSV.
- ✅ Persystentna historia w SQLite (`token_usage`).
- ✅ Hard budget per sesja + per użytkownik + per klient.
- ✅ Dashboard widget z wizualizacją kosztów (wykres w `index.html`).
- ✅ Integracja z OpenRouter: `list_models`, `get_token_usage`.
- **Stack:** `sqlite3`, OpenRouter MCP tools, `xmlrpc.client` (do Odoo v16 Timesheets + Task Picker)

---

## Faza 4: Microsoft Presidio Middleware (✅ Wdrożone)
**Cel:** Anonimizacja (pseudonimizacja) danych PII w locie, zanim trafią do LLM.
- ✅ Pseudonimizacja: `Jan Kowalski` → `<PERSON_1>`, `NIP 1234567890` → `<NIP_1>`.
- ✅ Reversible mapping (odwracalne — agent pracuje na tokenach, system podmienia z powrotem).
- ✅ Warstwa middleware w pipeline MCP (przed wysyłką do OpenRouter).
- ✅ Audit Log Filter chroniący logi systemowe przed PII.
- **Stack:** `presidio-analyzer>=2.2.0`, `presidio-anonymizer>=2.2.0`, `spacy` + `pl_core_news_md`

---

## Faza 5: Agent Swarm & Ekosystem Narzędzi (✅ Deklaratywnie wdrożone / ⚠️ Hollow Skills Gap)
**Cel:** Dispatcher (router), specjalistyczne persony, Shadow Mode z akceptacją w Odoo oraz pełna integracja z zewnętrznym ekosystemem (Fireflies, Zarządzanie Projektami).

> **⚠️ GAP — odkryty audytem F6-01 (2026-06-06):**
> Faza 5 wdrożyła Dispatcher, SkillConfig, Red Flag Engine i SKILL_REGISTRY (11 skilli).
> Jednak skille są **"wydmuszkami"** — deklarują `allowed_tools=["xmlrpc"]` jako stringi,
> ale Executor NIE przekazuje tool schemas do LLM-a. Brak function calling = brak realnej akcji.
> Dodatkowe bugi: `executor.py` crash (`.generate()` nie istnieje), `system_prompt` zakomentowany.
> Ten gap jest adresowany w **Fazie 6 (Sprint F6-01)**.

- **Agent Decision Protocol (ADP):** ✅ 8-krokowy potok decyzyjny (Historia → Kontekst → Wersja Odoo → Best Practices → Analiza → Trudność → Research → Plan).
- **Execution Pipeline (FSM):** ✅ 5-fazowa maszyna stanów (Vault Auth → Reconnaissance → Cognitive → Actuation → Teardown & Sync) ze wstrzykiwaniem technologii z `EnvironmentRecon` do kontekstu ADP.
- **Global Knowledge Sync (Shared Brain):** ✅ Rozproszona pamięć (LanceDB + SQLite metadata). ⚠️ Knowledge Seeding deferred do Fazy 7.
- **Dispatcher & SkillExecutor:** ✅ Routing na `SkillName`, 11 specjalizacji, `SKILL_REGISTRY`, Red Flag Engine.
- **SkillConfig (Pydantic):** ✅ Bariery `read_only`, `requires_human_override`, `requires_shadow_mode`.
- ✅ Wzorzec `forward_message` (eliminacja problemu "głuchego telefonu").
- **Fireflies AI Connector:** ✅ 4-krokowy kaskadowy algorytm dopasowywania + webhook REST.
- ✅ Chat Widget wbudowany w Odoo (moduł `smart_chat`).
- ✅ Shadow Mode z przyciskiem [Potwierdź] w interfejsie Odoo.
- **Odoo.sh Log Reader:** ✅ Narzędzie MCP do odczytu logów chmurowych.
- **Stack:** `meta-llama/llama-3.1-8b` (dispatcher), `anthropic/claude-sonnet-4` (code-gen), `mcp>=1.2.0`

---

## Faza 6: Tool Calling Engine, Interactive CLI & MVP Polishing (✅ Wdrożone)
**Cel:** Przekształcenie "wydmuszek" (Hollow Skills) w realne narzędzia z function calling, stworzenie interaktywnego interfejsu CLI oraz doszlifowanie MVP (Historia, Rollback, Audit).

> **Sprint F6-01:** `docs/sprints/2026-06-06_F6-01_skills_and_ui_sprint.md`
> **Sprint F6-02:** `docs/sprints/2026-06-06_F6-02_mvp_polishing_sprint.md`
> **Decyzje architektoniczne:** Monolith (CLI importuje Swarm bezpośrednio), introspekcja (auto tool schemas), Rollback na poziomie Executor (pre/post hooki), Smart Context dla historii.

### 6.0 Critical Bugfixes (Pre-requisite)
- ✅ Naprawa crash w `executor.py` (`.generate()` → `.chat()`, odkomentowanie `system_prompt`).
- ✅ Refactor `llm_client.py` → wsparcie `messages: List[Dict]` + `tools: List[Dict]`.
- ✅ Dodanie brakujących dependencies: `rich`, `prompt_toolkit`, `litellm`.

### 6.1 Tool Registry & Engine
- ✅ **Tool Registry** (`swarm/tools.py`): Dekorator `@register_tool`, introspekcja `inspect` + type hints → OpenAI JSON Schema.
- ✅ **Adapter Pattern**: Wrappery na istniejące MCP tools (`mcp/server.py`), NIE duplikacja logiki.
- ✅ **Nowe narzędzia**: `read_odoo_log()`, `search_odoo_code()`, `search_knowledge_base()`.
- ✅ **Executor Refactor**: Tool Calling Loop.
- ✅ **SkillConfig validation**: Startup check — tool name musi istnieć w Registry.

### 6.2 Interactive Rich CLI & Premium GUI
- ✅ `smartmyodoo/cli.py` — `PromptSession` + `Rich.Console` + Markdown rendering.
- ✅ Agent Loop: `user_input → Dispatcher → Executor → render response`.
- ✅ Tool Execution UI: `Rich.Live` panel z spinnerem.
- ✅ Web UI (Premium GUI): Tab registry, rozszerzony chat, timeline aktywności (`activity.js`).

### 6.3 MVP Polishing (F6-02)
- ✅ **Chat History Persistence (Smart Context)**: `ChatMessage` w bazie i `ChatRepository`, sidebar z sesjami w Web UI.
- ✅ **Rollback Safety Net**: `SandboxManager` automatycznie duplikuje DB przed groźnymi operacjami mutującymi.
- ✅ **Audit Trail Enrichment**: Logowanie każdego wywołania narzędzia przez `audit.py` + filtrowanie `SecretFilter`. Zapis do bazy i live timeline w UI.
- ✅ **Task Binding (Karty Pracy)**: Modale wyszukiwania, integracja XML-RPC, wiązanie ID zadania i cache nazwy. Odoo jako SSoT dla Tasków.

---

## Faza 7: Production Hardening & Client-Server Mode (⏳ W trakcie)
**Cel:** Stabilizacja, integracja Pipeline FSM z Tool Engine, pełna architektura agentowa i integracja z zewnętrznymi trackerami.

> **Sprint F7-01:** `docs/sprints/2026-06-07_F7-01_projekt_tab_sprint.md`
> **Zrealizowano (F7-01):** Dwustanowy widok projektu (Credentials / Task Picker), obsługa wielu projektów w jednym Odoo, auto-tworzenie domyślnych zadań ([SmartMyOdoo] Pula czasu roboczego), weryfikacja logiki z prawdziwym testem Playwright (E2E).
>
> **Sprint FIX-F7-02:** `docs/sprints/2026-06-07_FIX-F7-02_qa_hotfix_sprint.md`
> **Zrealizowano (FIX-F7-02):** Hotfixy QA, usunięcie śledzonych plików binarnych, scalenie endpointów logowania czasu, strict Pydantic walidacja, ujednolicenie klucza Vault (globalny `default_ODOO`).
>
> **Sprint ARCH-S1.1 (Swarm Integration - Skill Panel):** `docs/sprints/ARCH-S1.1_skill_panel.md`
> **Zrealizowano (ARCH-S1.1):** Dodanie zakładki z ręcznym doborem skilli (Skill Panel) oraz predefiniowanymi programami, endpoint GET /api/skills, omijanie (bypass) automatycznego Dispatchera przy jawnym wyborze oraz odzwierciedlenie autoselekcji w UI.

### 7.1 Pipeline Integration
- Podłączenie Tool Engine do pełnego `pipeline.py` FSM (AUTH→RECON→COGNITIVE→ACTUATION→SYNC).
- Integracja z SmartMyVault (automatyczne wstrzykiwanie credentials w pełnym potoku FSM).

### 7.2 CLI Client-Server Mode
- Przejście CLI z importu bezpośredniego na HTTP client odpytujący FastAPI.
- Naprawa `/api/chat` endpoint → prawdziwy LLM response zamiast hardkodowanego template.
- WebSocket streaming responses dla Live Logs z backendu.

### 7.3 Advanced Features & Extended Ecosystem
- Dry Run mode (`--dry-run` flag w CLI).
- Integracja z systemami zewnętrznymi (Jira / Linear) jako Task Pickery.
- Opcja Knowledge Seeding (Stack Overflow, Odoo Forums).
- ✅ Automatyczne tworzenie logów pracy i zamykanie Timesheetów (Task Binding i Auto-Create Task wdrażane w F7-01).
- **Stack:** `websockets>=12.0`, `aiohttp>=3.9.0`
