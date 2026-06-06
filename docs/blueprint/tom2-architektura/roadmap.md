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

## Faza 1: Fundament — SmartMyVault + Packaging
**Cel:** Zunifikowanie projektu jako jeden pakiet Python `smartmyodoo`.

### 1.1 Migracja Backend: Flask → FastAPI
- Przepisanie `vault_server.py` (191 LOC) na async FastAPI + Uvicorn.
- Dodanie walidacji Pydantic do wszystkich endpointów API.
- Auto-generowany Swagger UI na `/docs`.
- **Stack:** `fastapi>=0.115.0`, `uvicorn>=0.32.0`, `pydantic>=2.10.0`

### 1.2 Migracja Storage: JSON → SQLite
- Utworzenie `smartmyodoo.db` z tabelami: `proposals`, `token_usage`, `audit_log`, `agent_tasks`.
- Shadow Mode (`proposals.json`) → tabela `proposals`.
- Token Governor (in-memory) → tabela `token_usage` (persystentna historia).
- **WYJĄTEK:** `vault_data.enc` zostaje jako zaszyfrowany plik Fernet (nie do SQLite!).
- **Stack:** `sqlite3` (stdlib Python)

### 1.3 Packaging: Jeden punkt wejścia
- Struktura pakietu `smartmyodoo/` z podmodułami (`vault/`, `mcp/`, `dashboard/`).
- Uruchamianie: `python -m smartmyodoo serve|mcp|vault`.
- Zachowanie obecnego Premium UI (`index.html` — Vanilla JS + Tailwind CDN).

### 1.4 Schema Migrations (ADR-010)
- Wdrożenie `alembic>=1.14.0` jako systemu migracji SQLite.
- Auto-upgrade przy starcie (`alembic upgrade head` przed FastAPI).
- Backup-before-migrate: `smartmyodoo.db` → `smartmyodoo.db.bak.{timestamp}` (retencja 3 kopie).

### 1.5 Logging & Error Sanitization (ADR-011)
- Centralny `log_config.py` z filtrem `SecretFilter` (Deny List: hasła, klucze API, PII).
- Globalny `@app.exception_handler` — brak stacktrace'ów w odpowiedziach produkcyjnych.
- Poziomy logowania: ERROR/WARNING/INFO/DEBUG z polityką sanityzacji.

---

## Faza 2: Odoo MCP Bridge
**Cel:** Pełna łączność odczyt/zapis z Odoo (v16-v19) przez XML-RPC.
- Rozbudowa `OdooClient` o obsługę `write`, `create`, `unlink`.
- Async wrapper na `xmlrpc.client` (lub migracja na `aiohttp`).
- Integracja z `vault.py run` — sekrety wstrzykiwane przez ENV.
- **Fetch Guard (ADR-012):** Paginacja `search_read` (default 100, max 500). Zakaz pobierania pól binarnych w batch.
- **Stack:** `xmlrpc.client` (stdlib), `mcp>=1.2.0` (FastMCP stdio)

---

## Faza 3: Token Governor, Multi-Workspace UI & Project Hub
**Cel:** Monitorowanie budżetu LLM, wsparcie wielu projektów jednocześnie w GUI, konfiguracja integracji z systemami zewnętrznymi (Odoo v16 / Jira) oraz powiązanie Workspace z zadaniami.
- **LLM Context Guardrails (ADR-012):** Hard limits na input tokens per model, Session Budget ($2/sesja, $10/dzień), Context Compression przy 70% okna.
- **Data Retention & GDPR (ADR-013):** Kolumna `workspace_id` w każdej tabeli, Auto-Purge (audit 90d, proposals 30d, tokens 365d), endpoint `DELETE /api/workspace/{id}/purge`.
- Przejście interfejsu (Vanilla JS) na architekturę Multi-Workspace (Micro-SPA) ze zmianą kontekstów (styl Discord/Slack).
- **Project Hub — Integration Setup Wizard (US 7.1):**
  - Ekran ⚙️ Ustawienia → Dodaj Połączenie z systemem zarządzania projektami.
  - Wizard: Wybór systemu (`Odoo v16` | `Jira`) → Credentials (URL, Login, Hasło) → `[ 🔌 Testuj Połączenie ]` → Zapis do Vault.
  - Możliwość konfiguracji wielu połączeń jednocześnie (np. Odoo wewnętrzne + Odoo klienta).
  - Credentials szyfrowane w `vault_data.enc` pod kluczem `PROJECT_HUB_<nazwa>`.
- **Task Picker (US 7.2):**
  - Przy tworzeniu `[ + Nowy Workspace ]` → dropdown z połączeniami → wyszukiwarka zadań z autouzupełnianiem (XML-RPC `project.task.search_read`).
  - Podgląd: nazwa zadania, klient, przypisana osoba, status.
- **Fast Connect & Workspace Memory:** Każdy Workspace przechowuje konfigurację i *Lessons Learned*. Aby wrócić do pracy, podajesz tylko 4-cyfrowy PIN, a agenty mają od razu pełen kontekst.
- **Task Binding (US 4.3):** Każdy Workspace jest powiązany z konkretnym zadaniem w Odoo Project (`project.task`) lub Jira. Otwierając Workspace, system wie *dla kogo* i *nad czym* pracujesz.
- **Auto-Timesheets (US 4.1 + 4.3):** Czas pracy (estymowany/rzeczywisty/hybrydowy). Przy zamknięciu system automatycznie tworzy wpis Timesheet w Odoo v16 (`hr.analytic.line`) z notatką wygenerowaną przez AI.
- **AI Session Summary (US 4.4):** Po zakończeniu sesji AI generuje zwięzły raport z Audit Logu i wysyła go jako komentarz (`mail.message`) do powiązanego zadania w Odoo.
- **Synchronizacja Dwukierunkowa (US 7.3):** Zamknięcie Workspace → opcjonalna zmiana statusu zadania w Odoo. Polling co 60s.
- **Raport Miesięczny (US 4.5):** Tabela + wykresy godzin i kosztów tokenów per miesiąc/klient. Eksport CSV.
- Persystentna historia w SQLite (`token_usage`).
- Hard budget per sesja + per użytkownik + per klient.
- Dashboard widget z wizualizacją kosztów (wykres w `index.html`).
- Integracja z OpenRouter: `list_models`, `get_token_usage`.
- **Stack:** `sqlite3`, OpenRouter MCP tools, `xmlrpc.client` (do Odoo v16 Timesheets + Task Picker)

---

## Faza 4: Microsoft Presidio Middleware (✅ Wdrożone)
**Cel:** Anonimizacja (pseudonimizacja) danych PII w locie, zanim trafią do LLM.
- Pseudonimizacja: `Jan Kowalski` → `<PERSON_1>`, `NIP 1234567890` → `<NIP_1>`.
- Reversible mapping (odwracalne — agent pracuje na tokenach, system podmienia z powrotem).
- Warstwa middleware w pipeline MCP (przed wysyłką do OpenRouter).
- Audit Log Filter chroniący logi systemowe przed PII.
- **Stack:** `presidio-analyzer>=2.2.0`, `presidio-anonymizer>=2.2.0`, `spacy` + `pl_core_news_md`

---

## Faza 5: Agent Swarm & Ekosystem Narzędzi (w tym Odoo)
**Cel:** Dispatcher (router), specjalistyczne persony, Shadow Mode z akceptacją w Odoo oraz pełna integracja z zewnętrznym ekosystemem (Fireflies, Zarządzanie Projektami).
- **Agent Decision Protocol (ADP):** Wdrożenie 8-krokowego potoku decyzyjnego (Historia → Kontekst → Wersja Odoo → Best Practices → Analiza → Trudność → Research → Prezentacja Planu).
- **Execution Pipeline (FSM):** Implementacja twardej, 5-fazowej maszyny stanów (Vault Auth → Reconnaissance → Cognitive → Actuation → Teardown & Sync) ze wstrzykiwaniem technologii z `EnvironmentRecon` prosto do kontekstu decyzyjnego ADP, wspierana transakcyjnym systemem zrzutów `pg_dump` dla trybu `LIVE_DB`.
- **Global Knowledge Sync (Shared Brain):** Mechanizm rozproszonej pamięci (lokalny SQLite + zdalne repozytorium GitHub) wzmocniony o **Knowledge Seeding** (scraping Stack Overflow i Odoo Forums).
- **Dispatcher & SkillExecutor:** Scentralizowany routing oparty na `SkillName` (zamiast starego modelu Person). Obejmuje 11 wyizolowanych specjalizacji (np. `ODOO_BUSINESS_ANALYST`, `ODOO_DEVELOPER`, `MAGIC_FIX`) zarządzanych przez `SKILL_REGISTRY`. Zabezpieczony rygorystycznym silnikiem **Red Flag Engine** blokującym niszczycielskie zapytania na poziomie regex przed odpytaniem LLM-a.
- **SkillConfig (Pydantic):** Wymuszanie rygorystycznych barier (np. odcinanie potężnych narzędzi takich jak `shadow_mode` dla agentów z flagą `read_only=True` oraz wymuszanie `requires_human_override`).
- Wzorzec `forward_message` (eliminacja problemu "głuchego telefonu").
- **Fireflies AI Connector:** Integracja odpowiedzialna za transkrypcję i analizę spotkań (boty obecne na callach), oraz automatyczne zamienianie notatek na tikety.
  - *Szczegóły:* Posiada 4-krokowy kaskadowy algorytm dopasowywania (Email -> Domena -> Partner -> Słowo kluczowe) oraz stabilizację webhooków REST omijającą JSON-RPC Odoo.
  - *Źródło do migracji:* `C:\od_zera_do_ai\Smart_odoo\addons_myodoo\fireflies_connector`
- **Automatyczne Projekty (styl Jira/Odoo):** Agenty samodzielnie prowadzą dziennik prac (uzupełnianie wpisów w projektach) i zgłaszają bugi.
  - *Źródło do migracji:* Moduły `project_addons`, `project_update` z `C:\od_zera_do_ai\Smart_odoo\addons_myodoo\`
- Chat Widget wbudowany w Odoo (moduł `smart_chat`).
- Shadow Mode z przyciskiem [Potwierdź] w interfejsie Odoo.
- **Odoo.sh Log Reader:** Implementacja narzędzia MCP do bezpośredniego odczytu i analizy logów chmurowych z Odoo.sh, pozwalającego na błyskawiczne diagnozowanie błędów 'Internal Server Error' (wymaga autoryzacji SSH/API w SmartMyVault).
- **Stack:** `meta-llama/llama-3.1-8b` (dispatcher), `anthropic/claude-sonnet-4` (code-gen), `mcp>=1.2.0`
