---
sprint_id: "F4-02"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-06
closed: null
goal: "Twarde reguły blokujące niebezpieczne akcje per rola agenta (Red Flag Engine)"
prefix: "F4"
complexity: 5
roadmap_ref: "roadmap.md → EPIC-4"
epic_ref: "EPIC-F4-GOLDEN"
tags: ["red-flags", "security", "zero-trust", "executor", "tdd"]
---

# 🚀 Sprint: F4-02 Red Flags Engine (Per-Skill Blockers)

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-06

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Agenci w systemach AI halucynują. Red Flag Engine to deterministic regex guard który BLOKUJE niebezpieczne intencje PRZED ich wykonaniem. Nie zależy od LLM — działa na twardych regułach.

### Metryka sukcesu (DoD)
`pytest tests/swarm/test_red_flags.py -v` → ALL PASSED (min. 4 testy dla różnych ról)

### ⚖️ ZASADY SPRINTU
- 🟠 TDD: Każda reguła Red Flag musi mieć dedykowany test
- 🔴 SCOPE: `smartmyodoo/swarm/red_flags.py` (NEW) + integracja z `executor.py`

---

## 🧱 Sekcja B — Podział Zadań

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | 🔴 RED — Test: `check_red_flags('MAGIC_FIX', 'Wykonaj DROP TABLE res_partner')` → raises `RedFlagViolation` | Failing | [ ] |
| 1.2 | 🟢 GREEN — `RedFlagEngine.check(skill_name, intent)`: iteruje po `skill_config.red_flags`, regex match | PASS | [ ] |
| 1.3 | 🔴 RED — Test: `check_red_flags('ODOO_DEVELOPER', 'odinstaluj moduł account')` → BLOCKED | Failing | [ ] |
| 1.4 | 🟢 GREEN — Pattern: `r"(odinstal|uninstall).*(account|sale|purchase|stock|base)"` | PASS | [ ] |
| 1.5 | 🔴 RED — Test: `check_red_flags('ODOO_ETL_MANAGER', 'Usuń wszystkie produkty')` → BLOCKED (no_mass_delete) | Failing | [ ] |
| 1.6 | 🟢 GREEN — Pattern: `r"(usuń|delete|unlink).*(wszystk|mass|bulk|all)"` | PASS | [ ] |
| 1.7 | 🔴 RED — Test: `check_red_flags('ODOO_API_EXPERT', "auth='public'")` → BLOCKED | Failing | [ ] |
| 1.8 | 🟢 GREEN — Pattern: `r"auth\s*=\s*['\"]?public"` | PASS | [ ] |
| 1.9 | 🔴 RED — Test: `check_red_flags('FINANCIAL_AUDIT', 'Zmień fakturę 123')` → BLOCKED (read_only) | Failing | [ ] |
| 1.10 | 🟢 GREEN — Red Flag for read_only skills: any write intent → block | PASS | [ ] |
| 1.11 | Integracja z `executor.py`: `RedFlagEngine.check()` wywoływane PRZED `llm_client.chat()` | Existing executor tests PASS | [ ] |
| 1.12 | **BRAMKA:** `pytest tests/swarm/test_red_flags.py tests/swarm/test_executor.py -v` | ✅ ALL GREEN | [ ] |

---

## 📊 PROGRESS BAR

| # | Faza | /arch | /dev | /qa | Status |
|---|------|:-----:|:----:|:---:|:------:|
| 1 | Red Flags Engine + Integration | ✅ | ⬜ | ⬜ | 🔵 |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|-----------------|
| V1 | Red Flag testy | `pytest tests/swarm/test_red_flags.py -v` | ALL GREEN (min. 5 testów) |
| V2 | Executor regresja | `pytest tests/swarm/test_executor.py -v` | ALL GREEN |
| V3 | Deterministyczność | Test "DROP TABLE" → ZAWSZE blokuje (100 runs) | Zero False Negatives |

---
_Wygenerowane przy użyciu szablonów TeamEngine._
