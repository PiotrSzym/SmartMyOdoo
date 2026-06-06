---
sprint_id: "F6-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-06
closed: 2026-06-06
goal: "Ożywienie skilli poprzez implementację Tool Calling Engine, naprawa Executora oraz stworzenie interaktywnego CLI (Rich TUI)"
prefix: "F6"
complexity: 8
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
tags: ["cli", "tui", "tools", "mcp", "llm-function-calling", "rich", "litellm", "tool-registry"]
arch_decisions:
  D1_cli_mode: "MONOLITH — CLI importuje Swarm bezpośrednio (bez pośrednictwa FastAPI)"
  D2_llm_adapter: "litellm — unified tool calling interface (OpenRouter/Anthropic/OpenAI)"
  D3_tool_schemas: "INTROSPECTION — auto-generowane z type hints + inspect"
  D4_pipeline: "DEFERRED — Pipeline FSM (pipeline.py) nie jest częścią F6-01, integracja w F6-02"
  D5_brain_as_tool: "YES — brain/rag_api.py wystawiony jako tool search_knowledge_base()"
---

# 🚀 Sprint: F6-01 Skill Tooling Engine & Interactive CLI

> **Architekt:** /arch | **Tryb:** R&D / Implementation
> **Data:** 2026-06-06 | **Bazuje na:** Audycie Giga z tej daty (12 GAP-ów zidentyfikowanych)

---

## 📈 PROGRESS BAR
- [x] FAZA 0: Critical Bugfixes (executor crash, system_prompt, llm_client)
- [x] FAZA 1: Tool Registry & Engine (tools.py, executor refactor, SkillConfig upgrade)
- [x] FAZA 2: Interactive CLI — Rich TUI (cli.py, __main__.py, dependencies)
- [x] FAZA 3: Skill Hardening & Testing (testy, aktualizacja skilli)
- [x] **Release Gate**

---

## 📋 Sekcja A — Business Discovery & Problem Definition

### Problem 1: "Wydmuszki" w Skillach (Hollow Skills)
Obecnie skille (np. `odoo_developer.py`) są zadeklarowane czysto konfiguracyjnie: `allowed_tools=["xmlrpc", "shadow_mode", "scaffold"]`.
Silnik egzekucyjny (`executor.py`) po prostu przekazuje surowy tekst do LLMa. **LLM nie ma świadomości dostępnych funkcji** (brak definicji Tool Schemas w standardzie OpenAI/Anthropic), przez co nie potrafi realnie wywołać akcji. Skille to na razie tylko specjalistyczne prompty, a nie "agenci", którzy mogą cokolwiek dotknąć w systemie.

**Dodatkowe defekty odkryte audytem:**
- `executor.py:36` woła `self.llm_client.generate()` — metoda NIE ISTNIEJE w `OpenRouterClient` (crash `AttributeError`)
- `executor.py:35` — `system_prompt` jest **zakomentowany** — skille nie wstrzykują swoich promptów
- `llm_client.py:38` wysyła 1 message do API — brak `messages_history` (konwersacja jednokrokowa)

### Problem 2: Brak Interfejsu (UX/UI)
Cała aplikacja "wisi" obecnie wyłącznie na backendzie FastAPI (`api.py`). Endpoint `/api/chat` (L206-234) zwraca **hardkodowany template** z persona replies, NIE prawdziwą odpowiedź LLM-a. Brak wygodnej pętli konwersacyjnej (`REPL`).

### Problem 3: Duplikacja logiki (odkryte audytem)
Moduł MCP (`mcp/server.py`) **już posiada** implementacje narzędzi: `search_odoo_records()`, `create_odoo_record()`, `read_odoo_schema()`, `propose_magic_fix()` etc. Nowy `tools.py` MUSI być adapterem wrapującym istniejący kod, NIE nową implementacją od zera.

---

## 🏛️ Sekcja A.1 — Decyzje Architektoniczne (ROZSTRZYGNIĘTE)

| # | Decyzja | Rozwiązanie | Uzasadnienie |
|---|---------|-------------|--------------|
| D1 | Tryb CLI: Monolith vs Client-Server | **Monolith** | FastAPI `/api/chat` jest niekompletny; naprawianie to oddzielny sprint; import bezpośredni = 2x mniej kodu, zero latencji |
| D2 | Tool Schemas: litellm vs custom adapters | **litellm** | Ujednolica OpenRouter/Anthropic/OpenAI; automatycznie mapuje tool schemas; jeden `completion()` call |
| D3 | Schema generation: introspection vs ręczne | **Introspection** | `inspect` + type hints → automatyczny OpenAI JSON Schema; mniej boilerplate |
| D4 | Pipeline integration (pipeline.py) | **DEFERRED do F6-02** | Pipeline FSM wymaga Scratchpad DB + rollback — zbyt dużo scope na jeden sprint |
| D5 | Brain/RAG jako tool | **TAK** | Prosty wrapper na `brain/rag_api.py` — quick win, dodaje wartość od razu |

---

## ✅ Metryka sukcesu (DoD)

### Functional
1. Komenda `python -m smartmyodoo chat` uruchamia interaktywny REPL w terminalu (Rich + prompt_toolkit).
2. Moduł `smartmyodoo/swarm/tools.py` zawiera Tool Registry z min. 4 realnymi narzędziami Pythona.
3. LLM (via litellm) potrafi zwrócić obiekt `tool_calls`, system to wyłapuje, odpala kod i zwraca wynik LLMowi.
4. Konwersacja utrzymuje `messages_history` między turami.

### Quality Gates
5. `python -m pytest tests/ -v` → ALL GREEN (w tym nowe testy z Fazy 3).
6. `ruff check smartmyodoo/` → 0 errors.
7. `mypy smartmyodoo/ --ignore-missing-imports` → 0 errors.

---

## 🧱 Sekcja B — Podział Zadań

### FAZA 0: Critical Bugfixes (Pre-requisite)

> Naprawy blokujące — bez nich Faza 1 nie ma fundamentu.

| # | Plik | Zadanie | Estymacja |
|---|------|---------|-----------|
| F0.1 | `swarm/llm_client.py` | Refactor `chat()` → akceptuje `messages: List[Dict]` + `tools: List[Dict]` zamiast jednego stringa. Dodać parsowanie `tool_calls` z response. | 30 min |
| F0.2 | `swarm/executor.py` | Fix crash: `.generate()` → `.chat()` | 5 min |
| F0.3 | `swarm/executor.py` | Odkomentować i aktywować `system_prompt` injection | 10 min |
| F0.4 | `pyproject.toml` | Dodać dependencies: `rich>=13.0`, `prompt_toolkit>=3.0`, `litellm>=1.40` | 5 min |
| F0.5 | `requirements.txt` | Zsynchronizować z pyproject.toml | 5 min |

### FAZA 1: Tool Calling Engine (Silnik Narzędzi)

| # | Plik | Zadanie | Estymacja |
|---|------|---------|-----------|
| F1.1 | `swarm/tools.py` [NEW] | **Tool Registry** — dekorator `@register_tool`, introspekcja `inspect` + type hints → OpenAI JSON Schema. Dict `TOOL_REGISTRY: Dict[str, ToolDefinition]` | 45 min |
| F1.2 | `swarm/tools.py` | **Adapter pattern** — wrappery na istniejące MCP tools: `search_odoo_records()` → `odoo_search()`, `read_odoo_schema()` → `odoo_schema()`, `scaffold_odoo_module()` | 30 min |
| F1.3 | `swarm/tools.py` | **Nowe tools**: `read_odoo_log(lines=50)`, `search_odoo_code(regex, path)`, `search_knowledge_base(query)` (wrapper brain/rag_api) | 30 min |
| F1.4 | `swarm/executor.py` | **Tool Calling Loop**: resolve `skill_config.allowed_tools` → schematy z Registry → wyślij z `system_prompt` + `tools` + `messages` → obsłuż `tool_calls` → execute → feedback → loop. Max 10 iteracji. | 60 min |
| F1.5 | `swarm/skills/skill_config.py` | Walidacja startup: jeśli tool name z `allowed_tools` nie istnieje w `TOOL_REGISTRY` → `ValueError` przy imporcie | 15 min |

### FAZA 2: Interfejs CLI (Rich TUI)

| # | Plik | Zadanie | Estymacja |
|---|------|---------|-----------|
| F2.1 | `smartmyodoo/cli.py` [NEW] | **Rich Console + PromptSession** — interaktywny REPL z historią wpisywania, rendering Markdown, spinner podczas tool execution | 60 min |
| F2.2 | `smartmyodoo/cli.py` | **Agent Loop** — `user_input → Dispatcher.classify_intent() → SkillExecutor.execute() → render`. Persistent `messages_history` w pamięci. | 30 min |
| F2.3 | `smartmyodoo/cli.py` | **Tool Execution UI** — `Rich.Live` panel z: "🔧 Wywołuję: scaffold_odoo_module(name='my_addon')..." + wynik po zakończeniu | 20 min |
| F2.4 | `smartmyodoo/__main__.py` | Dodać komendę `chat` do subparsers → import `cli.main()` | 10 min |

### FAZA 3: Skill Hardening & Testing

| # | Plik | Zadanie | Estymacja |
|---|------|---------|-----------|
| F3.1 | `tests/test_tool_registry.py` [NEW] | Test: rejestracja narzędzia → poprawna schema generacja. Test: unknown tool → `KeyError`. Test: `allowed_tools` mapping. | 30 min |
| F3.2 | `tests/test_executor_tools.py` [NEW] | Mock LLM response z `tool_calls` → verify function execution → verify result feedback. Test max iterations guard. Test `RedFlagViolation` wciąż działa. | 45 min |
| F3.3 | `swarm/skills/odoo_developer.py` | Aktualizacja: `allowed_tools` → nazwy z Tool Registry (np. `"xmlrpc"` → `"odoo_search"`) | 10 min |
| F3.4 | `swarm/skills/odoo_business_analyst.py` | Aktualizacja j/w | 10 min |
| F3.5 | Wszystkie skille | Walidacja: `python -c "from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY"` → brak errors | 5 min |

---

## 📦 Sekcja C — Zależności

### Nowe pakiety Python

| Pakiet | Wersja | Cel |
|--------|--------|-----|
| `rich` | >=13.0 | Rich Console, Markdown rendering, spinners, Live display |
| `prompt_toolkit` | >=3.0 | PromptSession z historią, autocomplete |
| `litellm` | >=1.40 | Unified LLM interface (OpenRouter/Anthropic/OpenAI) z native tool calling |

### Istniejące moduły do re-użycia (NIE duplikować!)

| Moduł | Ścieżka | Użycie w tools.py |
|-------|---------|--------------------|
| MCP Odoo Client | `smartmyodoo/mcp/odoo_client.py` | `odoo_search()`, `odoo_schema()` |
| MCP Shadow Mode | `smartmyodoo/mcp/shadow_mode.py` | `odoo_create()`, `odoo_update()` |
| MCP Database Magic | `smartmyodoo/mcp/database_magic.py` | `propose_magic_fix()` |
| Brain RAG API | `smartmyodoo/swarm/brain/rag_api.py` | `search_knowledge_base()` |

---

## ❓ Otwarte Kwestie (do rozwiązania w trakcie)

1. **Permission model**: Jak wyglądać ma prompt "Czy chcesz uruchomić scaffold('my_module')?" w CLI? → Rozwiązać w F2.3.
2. **Error handling**: Co gdy tool rzuci wyjątek? → Propagacja do LLM jako tool result z error message (standard OpenAI).
3. **Dry run mode**: Czy CLI ma mieć `--dry-run` flag? → Nice to have, defer do F6-02.

---

## 🏁 CLOSE CHECKLIST (Bramka Zamykająca)
- [x] FAZA 0: Wszystkie bugi naprawione, dependencies dodane.
- [x] FAZA 1: Tool Registry działa, Executor obsługuje tool_calls.
- [x] FAZA 2: `python -m smartmyodoo chat` działa interaktywnie.
- [x] FAZA 3: Testy GREEN, skille zaktualizowane.
- [x] `python -m pytest tests/ -v` → ALL GREEN.
- [x] `ruff check smartmyodoo/` → 0 errors.
- [x] Sprint zamknięty w YAML frontmatter (`status: DONE`, `closed: <data>`).
