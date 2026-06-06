---
sprint_id: "F5-01"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-06
closed: null
goal: "Centralny config YAML (skill→model LLM + parametry), klucze API w Vault, tabela Lessons Learned, adres bazy wymiany wiedzy"
prefix: "F5"
complexity: 5
roadmap_ref: "roadmap.md → EPIC-5"
epic_ref: "EPIC-F5-CONFIG"
tags: ["config", "yaml", "vault", "llm-keys", "lessons-learned", "knowledge-base", "tdd"]
---

# 🚀 Sprint: F5-01 Agent Config YAML + Vault LLM Keys + Lessons Learned DB

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-06 | **Bazuje na:** architecture_gap_analysis.md

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
System musi mieć **jedno miejsce** (Single Source of Truth) gdzie definiujemy:
1. **Który skill używa jakiego modelu LLM** (np. `magic_fix` → Claude Sonnet 4, `odoo_crud` → GPT-4.1-mini)
2. **Skąd brać klucze API** (z Vault, nie z `os.environ`)
3. **Gdzie jest baza wymiany wiedzy** (Lessons Learned — co poszło nie tak i jak to naprawić)
4. **Adres bazy LanceDB / SQLite** dla wiedzy dzielonej między sesjami

Bez tego: zmiana modelu = edycja kodu Python. Klucze API leżą w env. Brak pamięci błędów.

### User Stories
| ID | As a... | I want... | So that... |
|----|---------|-----------|------------|
| US-F5-01-1 | Admin | zmieniać model LLM per skill bez restartu kodu | mogę testować nowe modele (np. Gemini 2.5 Pro) edytując YAML |
| US-F5-01-2 | System | pobierać klucze API z Vault | sekrety nie leżą w zmiennych środowiskowych |
| US-F5-01-3 | Agent | zapisywać "lekcje nauczone" po każdym błędzie | następnym razem sprawdzę czy ten błąd już się zdarzył |
| US-F5-01-4 | Agent | przeszukać bazę Lessons Learned przed rozpoczęciem zadania | nie powtórzę tego samego błędu |
| US-F5-01-5 | Admin | skonfigurować adres bazy wiedzy (LanceDB, SQLite) w jednym pliku | wszystko w jednym miejscu |

### Metryka sukcesu (DoD)
- `pytest tests/core/test_config.py tests/swarm/test_lessons.py -v` → ALL PASSED
- Plik `config/agent_config.yaml` istnieje i jest walidowany przez Pydantic
- `llm_client.py` czyta model z configu (nie z hardkodu)

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza 2 (Vault integration) wymaga Fazy 1 (Config loader). Faza 3 (Lessons DB) niezależna.

#### Zasada 2: TDD FIRST 🟠
Config loader i Lessons DB muszą mieć testy RED→GREEN. Vault integration = 🔴 obowiązkowy test.

#### Zasada 3: SCOPE ISOLATION 🔴
NEW files: `config/agent_config.yaml`, `smartmyodoo/core/config.py`, `smartmyodoo/swarm/brain/lessons.py`

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności

```
┌──────────────────────────────────────┐
│  FAZA 1 (Config YAML + Loader)       │
│  [agent_config.yaml]                 │
│  [AgentConfig Pydantic model]        │
│  [config.py loader]                  │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: test_config.py GREEN
               ▼
┌──────────────────────────────────────┐      ┌──────────────────────────────┐
│  FAZA 2 (Vault → LLM Keys)          │      │  FAZA 3 (Lessons Learned)    │
│  [llm_client refactor]              │      │  [lessons.py + SQLite]       │
│  [multi-provider support]           │      │  [search + auto-save]        │
└──────────────────────────────────────┘      └──────────────────────────────┘
  ✅ BRAMKA: test_llm_client.py GREEN          ✅ BRAMKA: test_lessons.py GREEN
```

---

### Sekcja B1 — FAZA 1: Config YAML + Pydantic Loader

> **📁 Scope:** `config/agent_config.yaml` (NEW), `smartmyodoo/core/config.py` (NEW), `tests/core/test_config.py` (NEW)

**Docelowa struktura `agent_config.yaml`:**

```yaml
# ═══════════════════════════════════════════
# SmartMyOdoo Agent Configuration (SSoT)
# ═══════════════════════════════════════════

# ── 1. Skill → Model LLM Mapping ──────────
skills:
  odoo_business_analyst:
    model: "anthropic/claude-sonnet-4"
    fallback: ["openai/gpt-4.1", "google/gemini-2.5-pro"]
    max_tokens: 4096
    temperature: 0.3

  odoo_crud:
    model: "openai/gpt-4.1-mini"
    fallback: ["meta-llama/llama-3.1-70b-instruct"]
    max_tokens: 2048
    temperature: 0.1

  odoo_etl_manager:
    model: "openai/gpt-4.1"
    fallback: ["anthropic/claude-sonnet-4"]
    max_tokens: 4096
    temperature: 0.2

  financial_audit:
    model: "anthropic/claude-sonnet-4"
    fallback: ["openai/gpt-4.1"]
    max_tokens: 4096
    temperature: 0.1

  odoo_audit_history:
    model: "openai/gpt-4.1-mini"
    fallback: []
    max_tokens: 2048
    temperature: 0.2

  security_audit:
    model: "anthropic/claude-sonnet-4"
    fallback: ["openai/gpt-4.1"]
    max_tokens: 4096
    temperature: 0.0

  odoo_developer:
    model: "anthropic/claude-sonnet-4"
    fallback: ["openai/gpt-4.1"]
    max_tokens: 8192
    temperature: 0.2

  odoo_devops_github:
    model: "openai/gpt-4.1-mini"
    fallback: []
    max_tokens: 2048
    temperature: 0.3

  odoo_sh_logs:
    model: "openai/gpt-4.1-mini"
    fallback: []
    max_tokens: 2048
    temperature: 0.3

  odoo_api_expert:
    model: "anthropic/claude-sonnet-4"
    fallback: ["openai/gpt-4.1"]
    max_tokens: 4096
    temperature: 0.2

  magic_fix:
    model: "anthropic/claude-sonnet-4"
    fallback: ["openai/gpt-4.1"]
    max_tokens: 8192
    temperature: 0.0
    requires_human_override: true

# ── 2. Dispatcher (Intent Classifier) ─────
dispatcher:
  model: "meta-llama/llama-3.1-8b-instruct"
  fallback_mode: "regex"    # regex gdy brak LLM
  confidence_threshold: 0.6

# ── 3. LLM Providers (API Keys w Vault) ───
llm_providers:
  openrouter:
    api_url: "https://openrouter.ai/api/v1/chat/completions"
    api_key_vault_name: "OPENROUTER_KEY"
  anthropic_direct:
    api_url: "https://api.anthropic.com/v1/messages"
    api_key_vault_name: "ANTHROPIC_KEY"
  openai_direct:
    api_url: "https://api.openai.com/v1/chat/completions"
    api_key_vault_name: "OPENAI_KEY"

# ── 4. Baza Wymiany Wiedzy (Knowledge) ────
knowledge:
  lancedb_path: ".agents/lancedb_store"
  metadata_db: ".agents/brain_metadata.sqlite"
  lessons_db: ".agents/lessons_learned.sqlite"
  embedding_model: "all-MiniLM-L6-v2"
  auto_save_on_error: true

# ── 5. TokenGovernor ──────────────────────
token_governor:
  max_budget_usd: 1.0
  alert_threshold_pct: 80
```

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Pydantic model `AgentConfig`: sekcje `skills`, `dispatcher`, `llm_providers`, `knowledge`, `token_governor` | Walidacja OK | [ ] |
| 1.2 | Pydantic model `SkillModelConfig`: `model: str`, `fallback: list[str]`, `max_tokens: int`, `temperature: float` | Import OK | [ ] |
| 1.3 | Pydantic model `LLMProviderConfig`: `api_url: str`, `api_key_vault_name: str` | Import OK | [ ] |
| 1.4 | Pydantic model `KnowledgeConfig`: `lancedb_path`, `metadata_db`, `lessons_db`, `embedding_model`, `auto_save_on_error` | Import OK | [ ] |
| 1.5 | `load_config(path="config/agent_config.yaml") -> AgentConfig` — ładuje YAML i waliduje | Funkcja OK | [ ] |
| 1.6 | 🔴 RED — Test: `load_config()` poprawnie parsuje YAML | Failing | [ ] |
| 1.7 | 🟢 GREEN — Impl config.py z PyYAML + Pydantic | PASS | [ ] |
| 1.8 | 🔴 RED — Test: `load_config()` z brakującym polem → ValidationError | Failing | [ ] |
| 1.9 | 🟢 GREEN — Pydantic walidacja | PASS | [ ] |
| 1.10 | Utworzenie pliku `config/agent_config.yaml` z pełnym configiem 11 skilli | Plik istnieje | [ ] |
| 1.11 | **BRAMKA:** `pytest tests/core/test_config.py -v` | ✅ ALL GREEN | [ ] |

---

### Sekcja B2 — FAZA 2: Vault → LLM Keys Integration

> **📁 Scope:** `smartmyodoo/swarm/llm_client.py` (refactor), `smartmyodoo/api.py` (refactor)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | 🔴 RED — Test: `create_client_from_config(config)` pobiera klucz z Vault zamiast os.environ | Failing | [ ] |
| 2.2 | 🟢 GREEN — `create_client(vault, provider_config)` → `vault.get_secret(provider_config.api_key_vault_name)` | PASS | [ ] |
| 2.3 | 🔴 RED — Test: `chat_with_model(model, prompt)` używa modelu z configu | Failing | [ ] |
| 2.4 | 🟢 GREEN — Refactor `OpenRouterClient.chat()` → przyjmuje model jako parametr | PASS | [ ] |
| 2.5 | Refactor `api.py` — usunięcie `os.environ.get("OPENROUTER_KEY")` → Vault | Backward compat | [ ] |
| 2.6 | Fallback: jeśli Vault niedostępny → `os.environ` jako safety net | Test PASS | [ ] |
| 2.7 | **BRAMKA:** `pytest tests/swarm/test_llm_client.py -v` | ✅ ALL GREEN | [ ] |

---

### Sekcja B3 — FAZA 3: Lessons Learned DB (Baza Wymiany Wiedzy)

> **📁 Scope:** `smartmyodoo/swarm/brain/lessons.py` (NEW), `tests/swarm/test_lessons.py` (NEW)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Model `LessonLearned` (SQLAlchemy): `id, workspace_id, category, odoo_model, description, solution, skill_name, error_hash, created_at` | Model OK | [ ] |
| 3.2 | Alembic migration: tabela `lessons_learned` | `alembic upgrade head` | [ ] |
| 3.3 | 🔴 RED — Test: `LessonsManager.save_lesson(workspace_id, category, description, solution)` | Failing | [ ] |
| 3.4 | 🟢 GREEN — INSERT do SQLite | PASS | [ ] |
| 3.5 | 🔴 RED — Test: `LessonsManager.search_similar(description)` → zwraca pasujące lekcje | Failing | [ ] |
| 3.6 | 🟢 GREEN — `SELECT WHERE description LIKE '%keyword%'` (MVP) lub LanceDB search (docelowo) | PASS | [ ] |
| 3.7 | 🔴 RED — Test: `auto_save_on_error` → po wyjątku w executor → zapis lekcji | Failing | [ ] |
| 3.8 | 🟢 GREEN — Hook w `SkillExecutor.execute()`: `except Exception → lessons.save_lesson()` | PASS | [ ] |
| 3.9 | Endpoint `GET /api/lessons?q=keyword` — przeszukiwanie bazy lekcji | 200 + JSON | [ ] |
| 3.10 | **BRAMKA:** `pytest tests/swarm/test_lessons.py -v` | ✅ ALL GREEN | [ ] |

---

### Sekcja B4 — FAZA 4: Integracja Config z istniejącymi modułami

> **📁 Scope:** `smartmyodoo/swarm/dispatcher.py`, `smartmyodoo/swarm/executor.py`, `smartmyodoo/api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 4.1 | Dispatcher czyta `config.dispatcher.model` zamiast hardkodu `DEFAULT_MODEL` | Test PASS | [ ] |
| 4.2 | SkillExecutor czyta `config.skills[skill_name].model` per skill | Test PASS | [ ] |
| 4.3 | TokenGovernor czyta `config.token_governor.max_budget_usd` | Test PASS | [ ] |
| 4.4 | Startup: `api.py` ładuje config przy starcie i wstrzykuje do DI | Server startuje | [ ] |
| 4.5 | **BRAMKA:** `pytest tests/ -v` (pełna regresja) | ✅ ALL GREEN | [ ] |

---

## 📊 PROGRESS BAR

| # | Faza | /arch | /dev | /qa | Status |
|---|------|:-----:|:----:|:---:|:------:|
| 1 | Config YAML + Loader | ✅ | ⬜ | ⬜ | 🔵 |
| 2 | Vault → LLM Keys | ✅ | ⬜ | ⬜ | 🔵 |
| 3 | Lessons Learned DB | ✅ | ⬜ | ⬜ | 🔵 |
| 4 | Integration | ✅ | ⬜ | ⬜ | 🔵 |

**Podsumowanie:** 0/4 ✅ Done | 4/4 🔵 Planned

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|-----------------|
| V1 | Config loader | `pytest tests/core/test_config.py -v` | ALL GREEN |
| V2 | LLM Vault | `pytest tests/swarm/test_llm_client.py -v` | ALL GREEN |
| V3 | Lessons DB | `pytest tests/swarm/test_lessons.py -v` | ALL GREEN |
| V4 | YAML exists | `python -c "from smartmyodoo.core.config import load_config; c=load_config(); print(len(c.skills))"` | `11` |
| V5 | Regresja | `pytest tests/ -v` | ALL GREEN, zero regresji |

---
_Wygenerowane przy użyciu szablonów TeamEngine (sprint_plan_multidev_template.md)._
