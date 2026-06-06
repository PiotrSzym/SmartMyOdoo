---
sprint_id: "F4-03"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-06
closed: null
goal: "Zapisywanie stanu 'przed zmianą' (Previous State Payload) dla każdej mutacji Odoo. Feature: Undo."
prefix: "F4"
complexity: 6
roadmap_ref: "roadmap.md → EPIC-4"
epic_ref: "EPIC-F4-GOLDEN"
tags: ["rollback", "undo", "shadow-mode", "sqlite", "alembic", "tdd"]
---

# 🚀 Sprint: F4-03 Session Rollback (Previous State Undo)

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-06

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Jeśli agent zmieni dane w Odoo i coś pójdzie źle — musi istnieć mechanizm "Undo". Przed każdą mutacją: `search_read()` → stare wartości do SQLite. Decyzja /arch Q2: na MVP używamy `search_read → SQLite` zamiast `pg_dump`.

### Metryka sukcesu (DoD)
`pytest tests/test_rollback.py -v` → ALL PASSED (min. 2 testy: capture + restore)

### ⚖️ ZASADY SPRINTU
- 🔴 **TDD OBOWIĄZKOWY:** Rollback dotyka bazy Odoo (zewnętrzna!) — KAŻDA metoda MUSI mieć mock test.
- 🔴 SEQUENTIAL GATE: Faza 2 (restore) wymaga Fazy 1 (capture).

---

## 🧱 Sekcja B — Podział Zadań

### Sekcja B1 — FAZA 1: Capture State

> **📁 Scope:** `smartmyodoo/core/models.py`, `smartmyodoo/mcp/rollback.py` (NEW), `migrations/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Model `RollbackEntry` (SQLAlchemy): `id, odoo_model: str, record_ids: JSON, previous_values: JSON, timestamp, workspace_id, proposal_id` | Model OK | [ ] |
| 1.2 | Alembic migration: tabela `rollback_entries` | `alembic upgrade head` bez błędów | [ ] |
| 1.3 | 🔴 RED — Test `capture_state('product.template', [42])`: mockowany OdooClient → sprawdza zapis do SQLite | Failing | [ ] |
| 1.4 | 🟢 GREEN — `RollbackManager.capture_state(model, ids)`: `search_read` → JSON → INSERT rollback_entries | PASS | [ ] |
| 1.5 | 🔴 RED — Test: `capture_state` gdy Odoo offline → graceful fail (log warning, nie crash) | Failing | [ ] |
| 1.6 | 🟢 GREEN — Error handling z `try/except ConnectionError` | PASS | [ ] |
| 1.7 | **BRAMKA:** `pytest tests/test_rollback.py -k capture -v` | ✅ GREEN | [ ] |

---

### Sekcja B2 — FAZA 2: Restore State + Shadow Integration

> **📁 Scope:** `smartmyodoo/mcp/rollback.py`, `smartmyodoo/mcp/shadow_mode.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | 🔴 RED — Test `restore_state(rollback_id)`: mockowany OdooClient `write()` z previous_values | Failing | [ ] |
| 2.2 | 🟢 GREEN — `RollbackManager.restore_state(rollback_id)`: SELECT from SQLite → `odoo_client.write()` | PASS | [ ] |
| 2.3 | Endpoint `POST /api/rollback/{id}` — przywrócenie stanu | 200 OK | [ ] |
| 2.4 | Integracja z `shadow_mode.py`: po `accept_proposal()` → `capture_state()` PRZED wywołaniem `odoo_client.write()` | Istniejące testy PASS | [ ] |
| 2.5 | **BRAMKA:** `pytest tests/test_rollback.py -v` | ✅ ALL GREEN | [ ] |

---

## 📊 PROGRESS BAR

| # | Faza | /arch | /dev | /qa | Status |
|---|------|:-----:|:----:|:---:|:------:|
| 1 | Capture State | ✅ | ⬜ | ⬜ | 🔵 |
| 2 | Restore + Integration | ✅ | ⬜ | ⬜ | 🔵 |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|-----------------|
| V1 | Alembic | `alembic upgrade head` | No errors |
| V2 | Capture testy | `pytest tests/test_rollback.py -k capture -v` | ALL GREEN |
| V3 | Restore testy | `pytest tests/test_rollback.py -k restore -v` | ALL GREEN |
| V4 | Shadow Mode regresja | `pytest tests/mcp/test_shadow_mode.py -v` | ALL GREEN |

---
_Wygenerowane przy użyciu szablonów TeamEngine._
