# ADR-007 — Jedna ścieżka rozwiązywania poświadczeń (typowany resolver)

- **Status:** Accepted (implementacja: sprint KEY-02)
- **Data:** 2026-06-16
- **Powiązane:** [DESIGN — Rejestr kluczy + Routing modeli](DESIGN-credentials-and-model-routing.md), KEY-01 (K1–K6), ADR-006

## Kontekst
KEY-01 wprowadził **typowany rejestr poświadczeń** (`CredentialType`: `odoo_data`/`odoo_timesheet`/`llm_provider`)
i **resolver** `vault.resolver.resolve_credential(vault_data, type, workspace_id, provider)` — wybiera
najlepsze poświadczenie po **typie + provider + workspace** (preferuje workspace nad `default`).

Problem: resolver jest używany **tylko** w `api_routers/workspaces.py` (Odoo). Handlery czatu
(`api_routers/chat.py`) omijają go i czytają poświadczenia **po sztywnych nazwach**:
- klucz LLM: `vault_data.get("OPENROUTER_KEY")` (×3 handlery),
- Odoo: `get("ODOO")`/`get("ODOO_URL")`/`get("ODOO_DB")`/`get("ODOO_MASTER_PASSWORD")` (osobny, ad-hoc schemat).

### Skutki
- Klucz OpenRouter działa **tylko** gdy sekret nazwano dokładnie `OPENROUTER_KEY` — mimo że UI (K6)
  pozwala dodać `type=llm_provider, provider=openrouter` pod dowolną nazwą (wtedy czat go **nie znajduje**).
- Dwie różne metody rozwiązywania Odoo (resolver w `workspaces` vs nazwy w `chat`) → ryzyko rozjazdu.
- „Magiczne nazwy" mieszają identyfikację z prezentacją; trudniej o multi-workspace / wielu providerów.

## Decyzja
1. **Kanoniczna ścieżka:** wszystkie konsumenty poświadczeń (chat, pipeline, workspaces) rozwiązują je
   przez **`resolve_credential(...)`** — po **typie + provider + workspace**, nie po nazwie.
2. **Fallback wsteczny (zachowany):** jeśli resolver nic nie znajdzie → spróbuj **legacy nazw**
   (`OPENROUTER_KEY`, `ODOO`, `ODOO_DB`, …) i na końcu **ENV**. Zero regresji dla istniejących wdrożeń.
3. **Prezentacja ≠ identyfikacja:** nazwa sekretu jest dowolną etykietą; o użyciu decyduje `type`/`provider`.

## Konsekwencje
- ✅ Dowolnie nazwany sekret `llm_provider/openrouter` działa w czacie; multi-provider i per-workspace „za darmo".
- ✅ Jeden, spójny mechanizm (łatwiejszy audyt bezpieczeństwa: jedno miejsce rozwiązywania kluczy).
- ✅ Stare wdrożenia (`OPENROUTER_KEY`, ENV) nadal działają (fallback).
- ⚠️ Resolver tylko klasyfikuje legacy po heurystyce (`to_credential`) — pokryć testami.
- ⚠️ Klucz LLM: do `OpenRouterClient` trafia `api_key` z `Credential` (a nie `password`) — ujednolicić.

## Zakres wdrożenia (KEY-02)
- `chat.py` (handle_chat, run_pipeline, chat_stream): LLM przez `resolve_credential(LLM_PROVIDER, ws, 'openrouter')`
  + fallback nazwa/ENV; Odoo przez `resolve_credential(ODOO_DATA/ODOO_TIMESHEET, ws)` (jak w `workspaces`).
- Testy: nazwany `OPENROUTER_KEY` nadal działa; sekret `llm_provider/openrouter` o dowolnej nazwie też;
  preferencja workspace; brak klucza → tryb heurystyczny.

## Powiązane
- [SPRINT-KEY-02](../sprints/2026-06-16_SPRINT-KEY-02_resolver_wiring.md)
