# Changelog — SmartMyOdoo

Format: [Keep a Changelog](https://keepachangelog.com/). Daty ISO. Szczegóły w `docs/sprints/`.

## [UX-08] — 2026-06-17 — Stan workspace + zadanie w nagłówku czatu

> Plan: [`docs/sprints/2026-06-17_SPRINT-UX-08_workspace_state_task_binding.md`](docs/sprints/2026-06-17_SPRINT-UX-08_workspace_state_task_binding.md) · Recon: SPIKE-001 · ADR-006. Suita: **315 passed / 0 failed**.

### Fixed
- **Workspace nie gubi się po odświeżeniu** — `Store` persystuje nie-wrażliwy stan UI (`workspaceId`/`activeTab`/`lang`) w `localStorage` (whitelist; token NIGDY nie persystowany). Root-cause: `new Store()` startował zawsze od `default`. [T1]
- **Cache-bust `store.js`** — plik z poprawką persystencji nie miał `?v=` w `index.html`, więc przeglądarka serwowała stary cache (poprawka „niewidzialna"). Zbumpowano wszystkie zmienione JS.

### Added
- **Badge zadania w nagłówku czatu** — `📋 Projekt › Zadanie` (dokąd logują się godziny) + przycisk „Zmień" otwierający Task Picker bez wchodzenia w zakładkę Projekt. [T2, T3]
- **Wspólny `taskPicker.js`** (DRY) — wyekstrahowany ze `project.js`, używany przez czat i zakładkę Projekt (PUT `/task_bind`).

### Security
- **Naprawiono stored-XSS** w Task Pickerze: nazwa zadania/projektu z Odoo trafiała do atrybutu `onclick` (breakout na `"`). Przejście na **event delegation + `data-*`** (`taskPicker.js` + `project.js`) — `dataset` zwraca czysty string, klasa XSS wyeliminowana. [/sec finding]

### Follow-up (osobne sprinty)
- **UX-09:** helpdesk task source (`project_task | helpdesk_ticket`, capability-check, Enterprise potwierdzony).
- Sprzątanie: martwy `task-search-modal`/`bindTask()` w `index.html`; ujednolicenie PIN w fixtures; auto-cache-bust JS.

## [SHARE-02] — 2026-06-17 — Hardening / domknięcie follow-upów

> Plan: [`docs/sprints/2026-06-17_SPRINT-SHARE-02_hardening_followup.md`](docs/sprints/2026-06-17_SPRINT-SHARE-02_hardening_followup.md).
> Domyka 3 findings Low /sec ze SHARE-01 + pre-existing czerwony test. Suita: **314 passed / 0 failed**.

### Security
- **Vault import — koniec cichego osłabienia Mastera:** bez `--master` recovery-init nadal działa (migracja niezablokowana), ale z **głośnym ostrzeżeniem** o niskiej entropii (`Master=PIN`) + instrukcją naprawy. [S2-1]
- **CLI `vault import --master`** — podaj silny Master od razu (recovery-init używa go zamiast PIN). [S2-2]
- **Guard-rail PII przy `seed --shared`** — `detect_pii` (stdlib `re`, **NO NEW DEPS**) z **walidacją sumy kontrolnej NIP** + email (pomija nazwy plików `@2x.png`); chunk z PII pomijany w warstwie `__shared__` z ostrzeżeniem, override `--allow-pii-shared`; warstwa prywatna nietknięta. [S2-3]

### Fixed
- **`test_mcp_pii_integration_roundtrip` zielony** — niekompletny mock (`search_count` zwracał MagicMock → `TypeError` w `int < total`); fix w teście, kod produkcyjny `mcp/server.py` nietknięty. Suita: 1 failed → **0 failed**. [S2-4]
- **Mniej fałszywych alarmów guarda PII** — checksum NIP odsiewa telefon/timestamp/kwotę; NIP ze spacjami teraz łapany. [follow-up /qa+/gf-review]

## [SHARE-01] — 2026-06-16 — Współdzielenie wiedzy + secrets-stay-local

> Plan: [`docs/sprints/2026-06-16_SPRINT-SHARE-01_wiedza_i_vault_sharing.md`](docs/sprints/2026-06-16_SPRINT-SHARE-01_wiedza_i_vault_sharing.md).
> Decyzja: **ADR-015** (Knowledge-as-source / Secrets-stay-local). Suita: **308 passed**.

### Added
- **Wersjonowany folder `knowledge/`** — źródło wiedzy zespołu (lekcje, instynkty); indeks budowany lokalnie. [SHARE-01-1]
- **Izolacja `workspace_id` w LanceDB** — schemat + migracja legacy (braki → `__shared__`); `search(query, top_k, workspace=)` filtruje **shared ∪ bieżący ws** (nigdy cudza prywatna), z escapingiem anti-injection. [SHARE-01-2/3]
- **CLI `smartmyodoo seed`** (`--shared` / `--private --workspace`) — idempotentny (deterministyczne ID, upsert). [SHARE-01-4]
- **`vault export` / `vault import`** — migracja TEJ SAMEJ osoby (samowystarczalny blob PBKDF2+Fernet, wymaga PIN); twarde ostrzeżenie „nie do współdzielenia zespołowego". [SHARE-01-6]
- **Dokumentacja użytkownika**: guide [`docs/guides/sharing_knowledge_and_secrets.md`](docs/guides/sharing_knowledge_and_secrets.md), sekcja w README, oraz **sekcja „Współdzielenie & Przekazanie" w Centrum Dokumentacji (panel, PL/EN)**.

### Fixed
- **`vault export/import` nie crashuje na konsoli Windows (cp1250)** — helper `_safe_print` + ASCII-markery; ostrzeżenie ADR-015 realnie dociera (Finding B z /gf-review).

### Follow-up (nie blokują)
recovery-init `Master=PIN` · brak `--master` w CLI `import` · PII-w-`__shared__` niewymuszone kodem.

## [FIX-02] — 2026-06-16 — Struktura i Patterny (dług po audycie)

> Plan: [`docs/sprints/2026-06-15_SPRINT-FIX-02_struktura_patterny.md`](docs/sprints/2026-06-15_SPRINT-FIX-02_struktura_patterny.md) + artefakty S3.x/S5.x.
> Zasada: **NO BEHAVIOR CHANGE** (refaktory) / **Evidence Before Claims**. Suita: 207 → **240 passed**.

### Changed — Struktura (FAZA S3)
- **God Module `api.py` rozłożony** (712 → 95 l.): domeny `auth`/`secrets`/`chat` wydzielone do
  `api_routers/*` (obok proposals/monitoring/workspaces/models) + deps-module `api_deps.py`/`chat_deps.py`. [S3.1]
- **`api_deps` zrywa cykl importów** `api ↔ routery` — `python -m smartmyodoo.api` startuje bez ImportError. [S3.4]
- **Dedup `execute`/`execute_stream`** — 7 wspólnych helperów polityk (red-flag/tools/PII/sandbox/audit). [S3.2]
- **Konsolidacja PII** — jedna kanoniczna warstwa w `security/pii/`; `mcp/pii_*` = shimy. [S3.3]

### Added — Patterny (FAZA S5)
- **Gateway LLM**: cache odpowiedzi (`core/llm_cache.py` In-Memory/Redis) + exp backoff + `temperature`/`max_tokens` z konfiguracji (retry/fallback już z K5). [S5.1]
- **Distributed lock** (`core/lock.py`, `SET NX PX` + fallback proces-lokalny) + idempotencja approve propozycji — anty-TOCTOU; `PRAGMA busy_timeout`. [S5.2]
- **Jakość RAG**: chunking z overlapem po granicach zdań; mock **sygnalizuje degradację** (`degraded=True`) zamiast fabrykować kontekst. [S5.3]

### Follow-up (nie blokują)
rate-limit endpointów LLM · pełny `litellm.Router` · NIP z myślnikami · wpięcie cache/`effective_model` w handlery.

## [KEY-01] — 2026-06-15 — Typowany rejestr kluczy + routing modeli LLM

> Plan: [`docs/sprints/2026-06-15_SPRINT-KEY-01_credentials_model_routing.md`](docs/sprints/2026-06-15_SPRINT-KEY-01_credentials_model_routing.md).
> Design: [`docs/architecture/DESIGN-credentials-and-model-routing.md`](docs/architecture/DESIGN-credentials-and-model-routing.md).

### Added
- **Typowany rejestr kluczy** (K1-K3): `CredentialType` (odoo_data/odoo_timesheet/llm_provider),
  `Credential` z walidacją per-typ, resolver (auto-tag legacy) + routing creds Odoo (timesheet→data→legacy).
- **Routing modeli per skill** (K4): `model_policy` — tier CHEAP/STANDARD/PREMIUM (ENV-override),
  Dispatcher dobiera model wg skilla zamiast stałej.
- **Odporność LLM** (K5): retry + fallback model w `OpenRouterClient`; `effective_model` degraduje tier
  przy niskim budżecie zamiast twardej blokady.
- **UI rejestru + zakładka „Modele"** (K6): w Skarbcu dropdown **Typ** + pola dynamiczne (LLM/Odoo/timesheet)
  i ikony typu na liście; nowa zakładka **Modele** (edycja tier→model + budżet + mapa skill→tier);
  badge modelu przy odpowiedziach w Czacie. Backend: `GET/PUT /api/models/policy`, utrwalanie
  `type/provider/ref` w sekrecie.

## [FIX-01] — 2026-06-15 — Remediacja audytu (bezpieczeństwo + reality-check)

> Źródło: audyt 5-wymiarowy (`.agents/AUDIT_REPORT.md`, 39 znalezisk).
> Plan: [`docs/sprints/2026-06-15_EPIC-FIX-01_naprawa_weryfikacja.md`](docs/sprints/2026-06-15_EPIC-FIX-01_naprawa_weryfikacja.md).
> PR: [#1](https://github.com/PiotrSzym/SmartMyOdoo/pull/1). Testy: **125/9/33 → 188 passed**.
> Każda zmiana poparta testem dowodowym (czerwony→zielony).

### Security
- **PII na ścieżce czat/pipeline** (`swarm/executor.py`) — pseudonimizacja przed LLM + deanonimizacja
  argumentów narzędzi i odpowiedzi (ścieżki `execute`/`execute_stream`). [🔴 krytyczne, S1.1]
- **Sandbox fail-closed** (`swarm/sandbox.py`) — koniec domyślnego hasła master `admin`. [🔴 S1.2]
- **CORS jawne originy** + rate-limit/lockout `/api/auth` (`api.py`). [S1.3]
- **Path traversal** w `scaffold_module` (`swarm/tools.py`); koniec logowania `master_pwd` (`swarm/db_manager.py`). [S1.4]

### Fixed (reality-check — atrapy → realne działanie)
- **Dispatcher** kontrakt `chat(messages=[...])` — koniec crasha klasyfikacji intencji. [S2.1]
- **TokenGovernor** podłączony do LLM — realny koszt + pre-flight hard-block (`spent` ≠ 0.0). [S2.2]
- **Sandbox** faktycznie izoluje — redirect `ODOO_DB` na scratchpad + fail-closed. [S2.3]
- **Routing skilli** do pipeline — koniec hardkodu `ODOO_DEVELOPER` (`swarm/pipeline.py`). [S2.6]
- **Workery** — uczciwe handlery (shadow_ops real, `not_implemented` zamiast fałszywego `completed`)
  + graceful shutdown (`workers/main_worker.py`). [S2.5]
- **Kolejka** niezawodna (`core/queue.py`) — BLMOVE+ack+requeue_stale (redelivery), TTL na `job:*`,
  atomowy `update_job` z ochroną przed regresją statusu. [S2.4]

### Tooling
- **Fundament testów** (`pyproject.toml`, `tests/e2e/conftest.py`) — `asyncio_mode=auto`, izolacja e2e
  (Playwright psuł testy async), coverage. Odblokowane 36 błędnych testów. [S4.1]
- `.gitignore` domknięty: TeamEngine (`.agents/`, `.claude/` wrappery), `graphify-out/`, mypy/pytest cache.

### Review hardening (bramka /review)
- **Wpięcie produkcyjne:** `api.py` przekazuje `pii=` do każdego `SkillExecutor` i `governor=` do
  każdego `OpenRouterClient` (chat/pipeline/WS) — wcześniej PII i kontrola kosztów były martwe na
  żywym ruchu (zielone tylko w testach jednostkowych). Strażnik: `tests/test_api_wiring.py`.
- **N3:** `enter_sandbox` przy braku hasła → fail-closed (try/except), nie crash requestu.
- **N2:** `execute_stream` ma parytet S2.3 (fail-closed + redirect `ODOO_DB` na scratchpad).
- Suite: **190 passed**.

### Not done (świadomie, poza FIX-01)
- S3 (refaktor `api.py` God Module, dedup `execute`/`execute_stream`, konsolidacja PII), S5 (patterny).
  → następny sprint: [`FIX-02`](docs/sprints/2026-06-15_SPRINT-FIX-02_struktura_patterny.md).
- NIE refaktorowano `SkillConfig`/`Dispatcher` jako „God Node" — to kohezyjny fan-in (weryfikacja audytu).
