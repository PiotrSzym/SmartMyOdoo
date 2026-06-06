---
sprint_id: "F2-03"
workspace: "SmartMyOdoo"
status: "COMPLETED"
created: 2026-06-06
closed: 2026-06-06
goal: "Dodanie 5 ról deweloperskich (developer/devops/logs/api/magic_fix) + implementacja SkillExecutor z Red Flag detection"
prefix: "F2"
complexity: 6
roadmap_ref: "roadmap.md → EPIC-2"
epic_ref: "EPIC-F2-BRAIN"
tags: ["swarm", "skills", "executor", "red-flags", "tdd"]
---

# 🚀 Sprint: F2-03 Rejestr 5 Skilli (Devs & DevOps) + Skill Executor

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-06 | **Bazuje na:** Brain v3.0 Dream Team

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Pełne 11 ról Dream Team + silnik wykonawczy (SkillExecutor) który: (1) buduje prompt z SkillConfig, (2) odpytuje LLM, (3) BLOKUJE niebezpieczne intencje przez Red Flag Engine.

### Metryka sukcesu (DoD)
- `len(SKILL_REGISTRY) == 11`
- `pytest tests/swarm/test_executor.py -v` → ALL PASSED
- Test: `"DROP TABLE"` → executor BLOKUJE (deterministycznie)

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza 2 (Executor) wymaga Fazy 1 (11 ról w Registry).

#### Zasada 2: TDD FIRST 🟠
Executor i Red Flag detection = 🔴 OBOWIĄZKOWE testy (dotykają LLM i bezpieczeństwa).

#### Zasada 3: SCOPE ISOLATION 🔴
`smartmyodoo/swarm/skills/` (5 NEW files) + `smartmyodoo/swarm/executor.py` (NEW)

---

## 🧱 Sekcja B — Podział Zadań

### Sekcja B1 — FAZA 1: Definicje 5 Ról Deweloperskich

> **📁 Scope:** `smartmyodoo/swarm/skills/` (5 NEW files)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | `odoo_developer.py`: prompt "_inherit mandatory, no core modification", tools: `[xmlrpc, shadow_mode, scaffold]`, red_flags: `[no_core_mod, no_uninstall_base_module]`, `requires_shadow_mode=True` | Dict OK | [x] |
| 1.2 | `odoo_devops_github.py`: prompt "Staging Isolation, Feature Branches, version bump in __manifest__", tools: `[rag]`, red_flags: `[no_force_push_production, no_dns_change]` | Dict OK | [x] |
| 1.3 | `odoo_sh_logs.py`: prompt "Tracebacki bottom-up, rozróżniaj logi aplikacji vs deployment", tools: `[rag]`, red_flags: `[]` | Dict OK | [x] |
| 1.4 | `odoo_api_expert.py`: prompt "API Keys zamiast hasła admina, nigdy auth='public' dla partnerów", tools: `[xmlrpc, rag]`, red_flags: `[no_auth_public_partners, no_plaintext_password]` | Dict OK | [x] |
| 1.5 | `magic_fix.py`: prompt "Force unlock, omijanie ORM tylko w sytuacji kryzysowej", tools: `[database_magic, shadow_mode]`, red_flags: `[no_drop_table, no_truncate]`, `requires_human_override=True`, `requires_shadow_mode=True` | Dict OK | [x] |
| 1.6 | Rozszerzenie `SKILL_REGISTRY` → 11 wpisów | `len() == 11` | [x] |
| 1.7 | **BRAMKA:** `pytest tests/swarm/test_registry.py -v` → `len == 11` | ✅ GREEN | [x] |

---

### Sekcja B2 — FAZA 2: SkillExecutor + Red Flag Engine

> **📁 Scope:** `smartmyodoo/swarm/executor.py` (NEW), `tests/swarm/test_executor.py` (NEW)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | 🔴 RED — Test: `SkillExecutor.execute(skill_config, message)` z mockowanym LLM zwraca odpowiedź | Failing | [x] |
| 2.2 | 🟢 GREEN — Impl `executor.py`: buduje `system_prompt` + `red_flags` jako context, odpytuje LLM przez `llm_client` | PASS | [x] |
| 2.3 | 🔴 RED — Test: Executor BLOKUJE gdy intencja zawiera pattern z `red_flags` (np. "DROP TABLE" dla magic_fix) | Failing | [x] |
| 2.4 | 🟢 GREEN — Impl regex-based Red Flag scan: `re.search(pattern, intent, re.IGNORECASE)` → raise `RedFlagViolation` | PASS | [x] |
| 2.5 | 🔴 RED — Test: Executor zwraca `{"requires_human_override": True}` dla `magic_fix` skill | Failing | [x] |
| 2.6 | 🟢 GREEN — Propagacja `requires_human_override` z `SkillConfig` do response | PASS | [x] |
| 2.7 | 🔴 RED — Test: Executor dla `read_only=True` skill NIE wywołuje Shadow Mode | Failing | [x] |
| 2.8 | 🟢 GREEN — Impl: `if skill_config.read_only: tools = [t for t in tools if t != 'shadow_mode']` | PASS | [x] |
| 2.9 | **BRAMKA:** `pytest tests/swarm/test_executor.py -v` | ✅ ALL GREEN (min. 4 testy) | [x] |

---

## 📊 PROGRESS BAR

| # | Faza | /arch | /dev | /qa | Status |
|---|------|:-----:|:----:|:---:|:------:|
| 1 | 5 Ról + Registry 11 | ✅ | ✅ | ✅ | 🟢 |
| 2 | SkillExecutor + Red Flags | ✅ | ✅ | ✅ | 🟢 |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|-----------------|
| V1 | Registry kompletny | `python -c "from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY; print(len(SKILL_REGISTRY))"` | `11` |
| V2 | Executor testy | `pytest tests/swarm/test_executor.py -v` | ALL GREEN |
| V3 | Red Flag deterministyczny | Test "DROP TABLE" → `RedFlagViolation` | Nie ma False Negative |
| V4 | Regresja skilli | `pytest tests/swarm/test_registry.py -v` | ALL GREEN |

---

## 💡 Lekcje Nauczone (Lessons Learned)
- **Early-Exit przez Regex:** Umiejscowienie detekcji `red_flags` bezpośrednio w warstwie executora (a nie w LLM-ie) zabezpiecza system na poziomie kodu Pythona (rzuca błąd `RedFlagViolation` zanim polecenie opuści naszą infrastrukturę w drodze do LLM-a).
- **Elastyczne filtrowanie narzędzi:** Możliwość dynamicznego usunięcia groźnego narzędzia z listy dozwolonych na poziomie executora (np. `shadow_mode` cięty dla `read_only=True`) pozwala utrzymać prostą architekturę uprawnień.
- **Granularne Skille:** Oddzielenie Dev, DevOps, API i Logów od głównych warstw CRUDowych i analitycznych wymusi na Dispatcherze lepszą alokację zadań technicznych. Ogranicza to skłonność LLM-a do "psucia wszystkiego naraz".

---
_Wygenerowane przy użyciu szablonów TeamEngine (sprint_plan_multidev_template.md)._
