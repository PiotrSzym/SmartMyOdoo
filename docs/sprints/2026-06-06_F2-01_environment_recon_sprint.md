---
sprint_id: "F2-01"
workspace: "SmartMyOdoo"
status: "COMPLETED"
created: 2026-06-06
closed: 2026-06-06
goal: "Agent automatycznie rozpoznaje środowisko Odoo (SaaS/sh/OnPrem, Community/Enterprise, wersja) przed podjęciem akcji"
prefix: "F2"
complexity: 4
roadmap_ref: "roadmap.md → EPIC-2"
epic_ref: "EPIC-F2-BRAIN"
tags: ["swarm", "recon", "environment", "odoo-detection", "tdd"]
---

# 🚀 Sprint: F2-01 Environment Reconnaissance (Odoo Detection)

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-06 | **Bazuje na:** implementation_plan.md (cc48e7f9)

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Agent MUSI wiedzieć gdzie pracuje. Złe rozpoznanie środowiska = zły zestaw narzędzi = katastrofa (np. próba wgrania modułu Python na Odoo SaaS, gdzie dostęp do serwera jest zablokowany).

### User Stories
| ID | As a... | I want... | So that... |
|----|---------|-----------|------------|
| US-F2-01-1 | Agent | automatycznie wykryć wersję Odoo (16/17/18/19) | dobrać odpowiednie API i zachowania per wersja |
| US-F2-01-2 | Agent | rozróżnić SaaS vs Odoo.sh vs On-Premise | wiedzieć czy mogę pisać Python (sh/OnPrem) czy tylko Studio (SaaS) |
| US-F2-01-3 | Agent | wykryć Community vs Enterprise | nie proponować modułów Enterprise klientowi Community |

### Metryka sukcesu (DoD)
`pytest tests/swarm/test_recon.py -v` → ALL PASSED (min. 3 testy: wersja, hosting, edycja)

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Faza 2 (Community/Enterprise) nie startuje bez zamknięcia Fazy 1 (wersja + hosting type).

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Każdy krok dotykający `odoo_client` (XML-RPC) wymaga testu RED przed implementacją GREEN.

#### Zasada 3: SCOPE ISOLATION 🔴
Kluczowe pliki: `smartmyodoo/swarm/recon.py` (NEW) + `tests/swarm/test_recon.py` (NEW) + `smartmyodoo/swarm/models.py` (rozszerzenie o `EnvironmentInfo`).

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────┐
│  FAZA 1 (Wersja Odoo + Hosting Type) │
│  [detect_environment()]              │
│  [URL classification]                │
│  [EnvironmentInfo model]             │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: pytest -k "version or hosting"
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Community vs Enterprise)    │
│  [detect_edition()]                  │
│  [ir.module.module check]            │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Wersja Odoo + Hosting Type

> **Trigger:** Start sprintu
> **📁 Scope:** `smartmyodoo/swarm/recon.py`, `smartmyodoo/swarm/models.py`, `tests/swarm/test_recon.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Model `EnvironmentInfo` (Pydantic): `odoo_version: str`, `edition: Literal["community","enterprise","unknown"]`, `hosting_type: Literal["saas","odoo_sh","on_premise","unknown"]` | Import bez błędów | [x] |
| 1.2 | 🔴 RED — Test `detect_version()`: mockowany XML-RPC `version()` zwraca `{"server_version": "18.0"}` | Failing test | [x] |
| 1.3 | 🟢 GREEN — Impl `EnvironmentRecon.detect_version()` w `recon.py` | Test PASS | [x] |
| 1.4 | 🔴 RED — Test klasyfikacji URL: `mycompany.odoo.com`→SaaS, `mycompany.odoo.sh`→sh, `erp.mycompany.pl`→OnPrem | Failing test | [x] |
| 1.5 | 🟢 GREEN — Impl `classify_hosting(url: str) -> str` | Test PASS | [x] |
| 1.6 | 🔴 RED — Test `detect_version()` gdy Odoo nie odpowiada (ConnectionError) → graceful fail | Failing test | [x] |
| 1.7 | 🟢 GREEN — Impl error handling: zwraca `EnvironmentInfo(odoo_version="unknown", ...)` | Test PASS | [x] |
| 1.8 | **BRAMKA:** `pytest tests/swarm/test_recon.py -k "version or hosting" -v` | ✅ ALL GREEN | [x] |

---

### Sekcja B2 — FAZA 2: Community vs Enterprise

> **Trigger:** Faza 1 BRAMKA zamknięta
> **📁 Scope:** `smartmyodoo/swarm/recon.py`, `tests/swarm/test_recon.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | 🔴 RED — Test `detect_edition()`: mock `search_read('ir.module.module', [('name','=','base_setup')], ['license'])` → Enterprise | Failing test | [x] |
| 2.2 | 🟢 GREEN — Impl `detect_edition()`: sprawdza obecność Enterprise-only modułów | Test PASS | [x] |
| 2.3 | 🔴 RED — Test `detect_edition()` gdy brak modułu → Community | Failing test | [x] |
| 2.4 | 🟢 GREEN — Fallback na "community" | Test PASS | [x] |
| 2.5 | **BRAMKA:** `pytest tests/swarm/test_recon.py -v` | ✅ ALL GREEN | [x] |

---

## 📊 PROGRESS BAR

| # | Faza | /arch | /dev | /qa | Status |
|---|------|:-----:|:----:|:---:|:------:|
| 1 | Wersja + Hosting | ✅ | ✅ | ✅ | 🟢 |
| 2 | Community/Enterprise | ✅ | ✅ | ✅ | 🟢 |

**Podsumowanie:** 2/2 ✅ Done | 0/2 🔵 Planned

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|-----------------|
| V1 | Testy Jednostkowe | `pytest tests/swarm/test_recon.py -v` | ALL GREEN (min. 5 testów) |
| V2 | Import modelu | `python -c "from smartmyodoo.swarm.models import EnvironmentInfo"` | Brak błędów |
| V3 | Graceful Fail | Test z ConnectionError nie crashuje | EnvironmentInfo z "unknown" |

---
_Wygenerowane przy użyciu szablonów TeamEngine (sprint_plan_multidev_template.md)._
