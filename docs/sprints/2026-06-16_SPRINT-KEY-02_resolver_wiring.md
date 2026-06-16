---
sprint_id: "KEY-02"
workspace: "SmartMyOdoo"
status: "IN_PROGRESS"
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
| KEY-02-1 | ✅ Helper `resolve_llm_key(vault_data, workspace_id)` — resolver(LLM/openrouter; auto-tag legacy) → ENV | `vault/resolver.py` | ✅ typed dowolna nazwa / legacy / ENV / None / preferencja ws |
| KEY-02-2 | ✅ `handle_chat` + `chat_stream` + `run_pipeline` używają `resolve_llm_key` zamiast `get("OPENROUTER_KEY")` | `api_routers/chat.py` | ✅ strażnik: brak `get("OPENROUTER_KEY")`, jest `resolve_llm_key` |
| KEY-02-3 | ⬜ (follow-up) Odoo w chat/pipeline przez `resolve_credential(ODOO_*)` — Odoo już działa ad-hoc + sanitizer; konsolidacja z `workspaces` jako osobny krok | `api_routers/chat.py` | — |
| KEY-02-4 | ✅ Testy `tests/test_credential_wiring.py` (LLM) | — | ✅ 6 testów |

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
