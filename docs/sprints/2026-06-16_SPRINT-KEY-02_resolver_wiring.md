---
sprint_id: "KEY-02"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-16
closed: null
goal: "Wpiąć typowany resolver poświadczeń do handlerów czatu/pipeline — klucz LLM i Odoo rozwiązywane po typie/provider/workspace, nie po sztywnej nazwie (z fallbackiem)"
prefix: "KEY"
complexity: 3
roadmap_ref: "ADR-007; domknięcie KEY-01 (resolver użyty end-to-end)"
tags: ["credentials", "resolver", "llm", "odoo", "security", "tdd"]
---

# 🔑 Sprint: KEY-02 — Wpięcie resolvera poświadczeń (domknięcie KEY-01)

> **Architekt:** /arch | **Owner:** /dev + /sec | **Decyzja:** [ADR-007](../architecture/ADR-007_credential_resolution_single_path.md)

---

## 📋 Sekcja A — Analiza

### Stan faktyczny
- `vault.resolver.resolve_credential(vault_data, type, workspace_id, provider)` — gotowy (K1-K3), wybiera
  poświadczenie po typie+provider+workspace (preferuje workspace nad `default`).
- Używa go **tylko** `api_routers/workspaces.py` (Odoo). `api_routers/chat.py` czyta **po nazwie**:
  `OPENROUTER_KEY` (×3), `ODOO`/`ODOO_URL`/`ODOO_DB`/`ODOO_MASTER_PASSWORD`.

### Problem (zgłoszenie użytkownika)
Klucz OpenRouter dodany przez UI (K6: `type=llm_provider, provider=openrouter`) pod inną nazwą niż
`OPENROUTER_KEY` **nie jest używany** w czacie — bo handler szuka sztywnej nazwy.

### Reguła docelowa (ADR-007)
> O użyciu poświadczenia decyduje **typ + provider + workspace**, nie nazwa. Sztywne nazwy + ENV =
> tylko **fallback** (kompatybilność). Jedna kanoniczna ścieżka rozwiązywania.

### ⚖️ Zasady
- **NO BEHAVIOR CHANGE dla istniejących:** sekret `OPENROUTER_KEY` i ENV nadal działają (fallback).
- **Evidence Before Claims:** testy dla obu ścieżek (nazwa legacy + typed dowolna nazwa).

---

## 🧱 Sekcja B — Podział Zadań

| # | Zadanie | Pliki | Test dowodowy |
|---|---------|-------|---------------|
| KEY-02-1 | Helper `resolve_llm_key(vault_data, workspace_id)` — `resolve_credential(LLM_PROVIDER, ws, 'openrouter')` → `api_key`; fallback `OPENROUTER_KEY` (name) → ENV | `chat_deps.py` lub `vault/resolver.py` | typed (dowolna nazwa) zwraca klucz; brak → None |
| KEY-02-2 | `handle_chat` + `chat_stream` + `run_pipeline`: użyj `resolve_llm_key` zamiast `get("OPENROUTER_KEY")` | `api_routers/chat.py` | nazwany `OPENROUTER_KEY` dalej działa; typed `llm_provider/openrouter` o innej nazwie też |
| KEY-02-3 | Odoo w chat/pipeline przez `resolve_credential(ODOO_DATA/TIMESHEET, ws)` (jak w `workspaces`) + fallback nazw/ENV; nazwa bazy przez `sanitize_db_name` | `api_routers/chat.py` | spójność z `workspaces._resolve_odoo_creds`; preferencja workspace |
| KEY-02-4 | Test parytetu: chat i workspaces rozwiązują Odoo tak samo | `tests/test_credential_wiring.py` | identyczny wynik dla tego samego vaulta |

---

## 🔬 Sekcja C — Definition of Done
- [ ] Klucz LLM działa, gdy sekret ma `type=llm_provider, provider=openrouter` **pod dowolną nazwą**.
- [ ] `OPENROUTER_KEY` (nazwa) i ENV nadal działają (fallback) — bez regresji.
- [ ] Odoo w czacie/pipeline rozwiązywane przez resolver (spójnie z `workspaces`), z `sanitize_db_name`.
- [ ] Testy dowodowe zielone; pełna suita bez regresji; restart serwera → klucz LLM działa per typ.

### Handoff
```
/arch (ADR-007 + ten sprint) → /dev (wpięcie) → /sec (parytet rozwiązywania) → /qa → /gf-review → /doc
```

> Po KEY-02: użytkownik dodaje klucz LLM dowolną nazwą (Typ „Model AI" + provider openrouter) i czat go używa.
> Follow-up (opcj.): w UI mapowanie ID→sekret zamiast sztywnej nazwy w pozostałych miejscach.
