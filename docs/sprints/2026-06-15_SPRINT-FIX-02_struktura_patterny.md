---
sprint_id: "FIX-02"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-15
closed: null
goal: "Spłacić dług strukturalny (api.py God Module, duplikacje) i wdrożyć brakujące wzorce stacku (litellm.Router, distributed lock, RAG) — BEZ zmiany zachowania"
prefix: "FIX"
complexity: 4
roadmap_ref: "audyt 2026-06-15 → .agents/AUDIT_REPORT.md (Struktura + Patterny)"
epic_ref: "EPIC-FIX-01 (2026-06-15_EPIC-FIX-01_naprawa_weryfikacja.md)"
tags: ["refactor", "architecture", "patterns", "fastapi", "redis", "rag", "tdd"]
---

# 🧱 Sprint: FIX-02 — Struktura i Patterny (dług po audycie)

> **Architekt:** /arch | **Tryb:** Sequential (S3 → S5) | **Data:** 2026-06-15
> **Bazuje na:** main po EPIC-FIX-01 (`d3e1f98`) | **Poprzednik:** [EPIC-FIX-01](2026-06-15_EPIC-FIX-01_naprawa_weryfikacja.md)

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Po EPIC-FIX-01 system jest **bezpieczny i prawdziwy** (atrapy naprawione), ale niesie dług strukturalny: `api.py` to God Module (1315 l.), logika bezpieczeństwa zduplikowana (`execute`/`execute_stream`), dwie warstwy PII. Dług = ryzyko rozjazdu polityk i wolniejszy rozwój. FIX-02 spłaca dług i domyka wzorce stacku (odporność LLM, współbieżność, jakość RAG) — **bez zmiany zachowania widocznego dla użytkownika**.

### User Stories
| ID | As a... | I want... | So that... |
|----|---------|-----------|------------|
| US-FIX-02-1 | /dev | `api.py` rozbity na APIRouter + serwisy | zmiana w jednej domenie nie ryzykuje rozjazdu i testuje się łatwiej |
| US-FIX-02-2 | /sec | jedną wspólną ścieżkę polityk w executorze | red flags / read-only / audyt / PII nie rozjeżdżają się między `execute` a `execute_stream` |
| US-FIX-02-3 | /audyt | jedną kanoniczną warstwę PII | recognizery i tokeny spójne (koniec `mcp/pii_*` vs `security/pii/*`) |
| US-FIX-02-4 | /dev | gateway LLM z retry/fallback/cache | przejściowy błąd dostawcy nie wywala zapytania, a koszty/latencja spadają |
| US-FIX-02-5 | /sec | distributed lock na zatwierdzaniu propozycji | równoległe approve nie wykona operacji dwa razy (TOCTOU) |
| US-FIX-02-6 | /qa | RAG z overlapem + sygnalizacją degradacji | mock/braki nie fabrykują kontekstu, retrieval nie gubi treści na granicach chunków |

### Metryka sukcesu (DoD sprintu)
- `pytest` → **≥ 190 passed / 0 failed** (zero regresji; każde zadanie dokłada test).
- Pokrycie krytycznych modułów (`executor`, `api` routery, `llm_client`, `queue`) **≥ 85%**.
- Re-audyt `/audyt` potwierdza zamknięcie znalezisk Struktura + Patterny.

### ⚖️ ZASADY SPRINTU
- **Zasada 1 — NO BEHAVIOR CHANGE 🔴:** refaktor na zielonym zestawie; istniejące testy API muszą przejść BEZ modyfikacji asercji (dowód braku regresji).
- **Zasada 2 — Evidence Before Claims 🟠:** każde zadanie ma test (czerwony przed / zielony po), bez mocka udającego logikę. (patrz [EPIC-FIX-01 §2](2026-06-15_EPIC-FIX-01_naprawa_weryfikacja.md))
- **Zasada 3 — SEQUENTIAL GATE 🔴:** S5 nie startuje przed zamknięciem S3 (wzorce wdrażamy na uporządkowanej strukturze).
- **Zasada 4 — ⛔ NIE refaktorować `SkillConfig`/`Dispatcher`** pod pretekstem „God Node" — to kohezyjny fan-in (weryfikacja audytu); zamiast tego skorygować próg metryki ART.21.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności
```
S3.1 (api.py → APIRouter) ──┐
S3.2 (dedup executor)       ├─ równolegle ─► BRAMKA: pytest API + executor 100% green
S3.3 (konsolidacja PII)     │
S3.4 (enkapsulacja sandbox)─┘
        │ ✅ S3 zamknięte
        ▼
S5.1 (litellm.Router)  S5.2 (distributed lock)  S5.3 (RAG overlap)
```

### FAZA S3 — Struktura (owner /dev + /audyt, review /gf-review)

| # | Zadanie | Pliki | RED → GREEN (test dowodowy) | Status |
|---|---------|-------|------------------------------|--------|
| S3.1 | Rozbić `api.py` na routery domenowe. ✅ **S3.1a** (auth, secrets) — [art.](2026-06-16_SPRINT-FIX-02-S3.1_api_routers.md). ✅ **S3.1b** (chat + `chat_deps`) — [art.](2026-06-16_SPRINT-FIX-02-S3.1b_chat_router.md); `api.py` 712→95 l. (bootstrap) | `api.py` → `api_routers/{auth,secrets,chat}.py` + `chat_deps.py` | ✅ `test_api`/`test_api_stream`/`test_security_s13`/`test_api_wiring` bez zmian asercji; suita 226 passed | ✅ |
| S3.2 | Ekstrakcja helperów z `execute`/`execute_stream` (7 helperów polityk: red-flag/tools/messages/sandbox/invoke/audit). Szczegóły: [SPRINT-FIX-02-S3.2](2026-06-16_SPRINT-FIX-02-S3.2_dedup_executor.md) | `swarm/executor.py` | ✅ `tests/swarm/test_executor_policy_parity.py` (parytet red-flag sync↔stream; single-source); suita 219 passed | ✅ |
| S3.3 | Konsolidacja PII: kanoniczna impl (stateful, produkcyjna) w `security/pii/`; `mcp/pii_*` = shimy re-eksportujące. Szczegóły: [SPRINT-FIX-02-S3.3](2026-06-16_SPRINT-FIX-02-S3.3_pii_consolidation.md) | `security/pii/*`, `mcp/pii_*`, `tests/security/*` | ✅ NIP/PESEL/PERSON + roundtrip + izolacja ws; `test_pii_*` produkcyjne bez zmian asercji; suita 222 passed | ✅ |
| S3.4a | **deps-module:** `api_deps.py` (security/get_auth_key/require_auth) — zrywa cykl importów `api ↔ api_routers`; routery importują z `api_deps`; `# type: ignore[has-type]` usunięte; `python -m smartmyodoo.api` startuje bez ImportError | `api_deps.py` (new), `api.py`, `api_routers/*` | ✅ `tests/test_api_deps.py` (router nie wciąga api.py; identyczność re-eksportu; brak importu auth z api) | ✅ |
| S3.4b | `SandboxManager.attach_existing_scratchpad(original_db, scratchpad_name)` zamiast pisania po `_active_scratchpad` z `pipeline.py` | `swarm/sandbox.py`, `swarm/pipeline.py` | RED: test, że pipeline ustawia scratchpad publicznym API i respektuje flagę `enabled`; brak dostępu do `_`-pól | ⬜ |
| — | **BRAMKA S3:** `pytest tests/test_api.py tests/swarm/test_executor.py tests/test_pii_middleware.py -v` → ALL GREEN | — | ✅ warunek startu S5 | ✅ ZAMKNIĘTA (S3.1/S3.2/S3.3/S3.4 zielone; suita 226) |

### FAZA S5 — Patterny (owner /dev, review /gf-review) — po S3

| # | Zadanie | Pliki | RED → GREEN (test dowodowy) | Status |
|---|---------|-------|------------------------------|--------|
| S5.1 | Gateway LLM: retry/backoff + fallback (K5) + **cache** (`core/llm_cache.py`: InMemory/Redis) + `temperature`/`max_tokens` konfigurowalne. Decyzja: klient+backoff zamiast `litellm.Router` (patrz [art.](2026-06-16_SPRINT-FIX-02-S5.1_llm_router_cache.md)) | `swarm/llm_client.py`, `core/llm_cache.py` | ✅ `tests/test_llm_cache.py` (cache hit/miss, backoff, parametry) + `test_llm_resilience`; suita 231 | ✅ |
| S5.2 | Distributed lock (`SET NX PX`) + idempotencja na approve propozycji; fallback proces-lokalny. Szczegóły: [art.](2026-06-16_SPRINT-FIX-02-S5.2_distributed_lock.md). (rate-limit LLM = follow-up) | `core/lock.py`, `api_routers/proposals.py` | ✅ `tests/test_proposal_lock.py` (8 równoległych approve → 1 przejście; mutual exclusion; timeout) | ✅ |
| S5.3 | RAG: chunking z overlapem po granicach zdań; próg `distance` + opcjonalny re-ranker; mock RAG **sygnalizuje degradację** (flaga), nie fabrykuje kontekstu | `swarm/brain/rag_api.py`, `swarm/brain/lancedb_client.py` | RED: tekst > 1 chunk → sąsiednie chunki mają overlap; mock zwraca `degraded=True` zamiast zmyślonego kontekstu | ⬜ |

---

## 🔬 Sekcja C — Weryfikacja & Wyjście

### Bramki wyjścia (Definition of Done)
- [ ] `api.py` rozbity na APIRouter + serwisy; brak globali/importów w handlerach; modele Pydantic
- [ ] `execute`/`execute_stream` współdzielą helpery polityk; jedna warstwa PII
- [ ] `litellm.Router` (retry/fallback/cache); distributed lock dla approve; RAG z overlapem + sygnalizacją degradacji
- [ ] `pytest` ≥ 190 passed / 0 failed; pokrycie krytycznych ≥ 85% (`pytest --cov`)
- [ ] /audyt re-audyt: znaleziska Struktura + Patterny zamknięte; brak nowych „God Node" false-positive (próg ART.21 skorygowany)
- [ ] /doc: CHANGELOG wpis [FIX-02]

### Handoff
```
/arch (ten artefakt) → /dev (S3 → S5) → /qa (pokrycie+regresja) → /gf-review (gate) → /doc → Release
```

> **Następny krok wykonawczy:** S3.1 (rozbicie `api.py`) — odblokowuje czystsze testy domenowe dla reszty sprintu.
