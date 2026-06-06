---
sprint_id: "F2-02"
workspace: "SmartMyOdoo"
status: "COMPLETED"
created: 2026-06-06
closed: 2026-06-06
goal: "Zdefiniowanie granic, promptów i Red Flags dla 6 ról: BA, CRUD, ETL, Financial, AuditHistory, Security + SkillConfig model + Registry + Dispatcher integration"
prefix: "F2"
complexity: 5
roadmap_ref: "roadmap.md → EPIC-2"
epic_ref: "EPIC-F2-BRAIN"
tags: ["swarm", "skills", "personas", "registry", "dispatcher", "tdd"]
---

# 🚀 Sprint: F2-02 Rejestr 6 Skilli (Analitycy & Operatorzy Danych)

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-06 | **Bazuje na:** Brain v3.0 (Dream Team) + implementation_plan.md

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Każdy agent ma wytyczone granice (co WOLNO, co ZAKAZANE) i dedykowany prompt systemowy. Dispatcher routuje bezpośrednio do `SkillName` (11 wartości) zamiast ogólnego `Persona` (8 wartości). Decyzja /arch Q1: Opcja B.

### User Stories
| ID | As a... | I want... | So that... |
|----|---------|-----------|------------|
| US-F2-02-1 | Dispatcher | routować do konkretnego SkillName (np. `ODOO_ETL_MANAGER`) | od razu trafiam do właściwego eksperta |
| US-F2-02-2 | Agent | mieć hardkodowany system_prompt z wiedzą ekspercką | odpowiadam zgodnie ze swoją specjalizacją |
| US-F2-02-3 | System | blokować intencje łamiące Red Flags | agent nie może przekroczyć swoich granic |

### Metryka sukcesu (DoD)
`pytest tests/swarm/ -v` → ALL PASSED, `len(SKILL_REGISTRY) == 6`

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza 2 (definicje ról) wymaga zamkniętej Fazy 1 (model SkillConfig). Faza 3 (Dispatcher) wymaga Fazy 2 (Registry z 6 wpisami).

#### Zasada 2: TDD FIRST 🟠
Model `SkillConfig` i `SKILL_REGISTRY` muszą mieć testy. Dispatcher refactor musi mieć test RED→GREEN.

#### Zasada 3: SCOPE ISOLATION 🔴
NEW directory: `smartmyodoo/swarm/skills/`. Dispatcher refactor w `smartmyodoo/swarm/dispatcher.py`.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności

```
┌──────────────────────────────────────┐
│  FAZA 1 (SkillConfig Model)          │
│  [SkillConfig Pydantic]              │
│  [SkillName Enum - 11 wartości]      │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: test_skill_config.py GREEN
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (6 Definicji + Registry)     │
│  [6x skill files]                    │
│  [SKILL_REGISTRY dict]               │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: len(REGISTRY) == 6
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (Dispatcher ↔ SkillName)     │
│  [ROUTING_TABLE refactor]            │
│  [Deprecate Persona enum]            │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: SkillConfig Model & SkillName Enum

> **📁 Scope:** `smartmyodoo/swarm/skills/skill_config.py` (NEW), `smartmyodoo/swarm/models.py`, `tests/swarm/test_skill_config.py` (NEW)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | `SkillName` enum (11 wartości): `ODOO_BUSINESS_ANALYST`, `ODOO_DEVELOPER`, `ODOO_DEVOPS_GITHUB`, `ODOO_SH_LOGS`, `ODOO_AUDIT_HISTORY`, `ODOO_CRUD`, `ODOO_ETL_MANAGER`, `FINANCIAL_AUDIT`, `SECURITY_AUDIT`, `ODOO_API_EXPERT`, `MAGIC_FIX` | Import OK | [x] |
| 1.2 | `SkillConfig` (Pydantic): `name: SkillName`, `system_prompt: str`, `allowed_tools: list[str]`, `red_flags: list[str]`, `read_only: bool = False`, `requires_shadow_mode: bool = False`, `requires_human_override: bool = False`, `recommended_model: str` | Walidacja OK | [x] |
| 1.3 | 🔴 RED — Test: SkillConfig waliduje poprawne dane i odrzuca brakujący `system_prompt` | Failing test | [x] |
| 1.4 | 🟢 GREEN — Impl SkillConfig z walidacjami | Test PASS | [x] |
| 1.5 | **BRAMKA:** `pytest tests/swarm/test_skill_config.py -v` | ✅ GREEN | [x] |

---

### Sekcja B2 — FAZA 2: Definicje 6 Ról + Registry

> **📁 Scope:** `smartmyodoo/swarm/skills/*.py` (6 NEW files), `smartmyodoo/swarm/skills/registry.py` (NEW)

**Struktura katalogowa (NEW):**
```
smartmyodoo/swarm/skills/
├── __init__.py
├── skill_config.py
├── registry.py
├── odoo_business_analyst.py
├── odoo_crud.py
├── odoo_etl_manager.py
├── financial_audit.py
├── odoo_audit_history.py
└── security_audit.py
```

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | `odoo_business_analyst.py`: prompt "Standard First — 90% problemów da się rozwiązać konfiguracją", tools: `[rag, xmlrpc_read]`, red_flags: `[no_code_generation]` | Dict ładuje się | [x] |
| 2.2 | `odoo_crud.py`: prompt "Magic Tuples (0,0,{}) for One2many", tools: `[xmlrpc, shadow_mode]`, red_flags: `[no_delete_posted_invoice]`, `requires_shadow_mode=True` | Dict OK | [x] |
| 2.3 | `odoo_etl_manager.py`: prompt "Batching Mandatory — max 200 rekordów/request", tools: `[xmlrpc, shadow_mode]`, red_flags: `[no_mass_delete, use_archive]`, `requires_shadow_mode=True` | Dict OK | [x] |
| 2.4 | `financial_audit.py`: prompt "Lock Dates Respect — Credit Note zamiast Cancel", tools: `[xmlrpc_read]`, `read_only=True`, red_flags: `[no_write_to_posted_moves]` | Dict OK | [x] |
| 2.5 | `odoo_audit_history.py`: prompt "Chatter tracking via mail.message", tools: `[xmlrpc_read]`, `read_only=True` | Dict OK | [x] |
| 2.6 | `security_audit.py`: prompt "Client-side Pseudonymization (PII)", tools: `[pii_middleware, xmlrpc_read]`, `read_only=True` | Dict OK | [x] |
| 2.7 | `registry.py`: `SKILL_REGISTRY: Dict[SkillName, SkillConfig]` z 6 wpisami | `len() == 6` | [x] |
| 2.8 | 🔴 RED — Test: `SKILL_REGISTRY` ma 6 ról, każda ma niepusty `system_prompt` | Failing | [x] |
| 2.9 | 🟢 GREEN — Registry poprawnie zbudowany | PASS | [x] |
| 2.10 | **BRAMKA:** `pytest tests/swarm/test_registry.py -v` | ✅ GREEN, `len == 6` | [x] |

---

### Sekcja B3 — FAZA 3: Dispatcher ↔ SkillName Integration

> **📁 Scope:** `smartmyodoo/swarm/dispatcher.py`, `smartmyodoo/swarm/models.py`, `tests/swarm/test_dispatcher_skills.py` (NEW)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Rozszerzenie `DispatchResult`: dodaj pole `skill_name: SkillName | None` | Model OK | [x] |
| 3.2 | 🔴 RED — Test: Dispatcher dla "Zaimportuj 5000 produktów" → `skill_name = ODOO_ETL_MANAGER` | Failing | [x] |
| 3.3 | 🟢 GREEN — Refactor `ROUTING_TABLE` → mapuje `IntentCategory` na `SkillName` + `SkillConfig` | PASS | [x] |
| 3.4 | 🔴 RED — Test: Dispatcher dla "Sprawdź kto zmienił fakturę" → `skill_name = ODOO_AUDIT_HISTORY` | Failing | [x] |
| 3.5 | 🟢 GREEN — Dodanie nowych heurystyk (import/audit/security keywords) | PASS | [x] |
| 3.6 | Deprecation: `Persona` enum zostaje ale `DispatchResult.persona` = `Optional` | Backward compat | [x] |
| 3.7 | **BRAMKA:** `pytest tests/swarm/test_dispatcher.py tests/swarm/test_dispatcher_skills.py -v` | ✅ ALL GREEN | [x] |

---

## 📊 PROGRESS BAR

| # | Faza | /arch | /dev | /qa | Status |
|---|------|:-----:|:----:|:---:|:------:|
| 1 | SkillConfig Model | ✅ | ✅ | ✅ | 🟢 |
| 2 | 6 Ról + Registry | ✅ | ✅ | ✅ | 🟢 |
| 3 | Dispatcher ↔ SkillName | ✅ | ✅ | ✅ | 🟢 |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|-----------------|
| V1 | Testy Skilli | `pytest tests/swarm/test_skill_config.py tests/swarm/test_registry.py -v` | ALL GREEN |
| V2 | Testy Dispatcher | `pytest tests/swarm/test_dispatcher.py tests/swarm/test_dispatcher_skills.py -v` | ALL GREEN |
| V3 | Import Registry | `python -c "from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY; print(len(SKILL_REGISTRY))"` | Wypisze `6` |
| V4 | Backward Compat | Stare testy `test_dispatcher.py` nadal PASS | Brak regresji |

---

## 💡 Lekcje Nauczone (Lessons Learned)
- **Modułowość Rejestru:** Podział na osobne pliki (np. `odoo_crud.py`, `financial_audit.py`) sprawdza się lepiej niż jeden wielki plik. Łatwiej w przyszłości dodać 50 nowych skilli bez tworzenia konfliktu merge.
- **TDD i Walidacja Pydantic:** Obłożenie konfiguracji skilla modelem Pydantic `SkillConfig` z `min_length=1` automatycznie zabezpiecza nas przed lukami, do których agent mógłby uciec (brak promptu).
- **Rozszerzone Heurystyki:** Użycie keywordów w kodzie (np. `5000`, `import`) odciąża LLM-a i sprawia, że do powtarzalnych testów E2E nie potrzebujemy połączenia z OpenRouterem – kod sam bezbłędnie znajduje odpowiedni `SkillName`.

---
_Wygenerowane przy użyciu szablonów TeamEngine (sprint_plan_multidev_template.md)._
