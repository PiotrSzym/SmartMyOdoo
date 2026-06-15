# Changelog — SmartMyOdoo

Format: [Keep a Changelog](https://keepachangelog.com/). Daty ISO. Szczegóły w `docs/sprints/`.

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
