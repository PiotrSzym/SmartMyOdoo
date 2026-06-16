---
sprint_id: "FIX-03"
workspace: "SmartMyOdoo"
status: "IN_PROGRESS"
created: 2026-06-16
closed: null
goal: "Wpięcie w handlery czatu: effective_model (budżet→tańszy tier), rate-limit /api/chat, cache LLM (warunkowo)"
prefix: "FIX"
complexity: 3
roadmap_ref: "Analiza follow-upów (2026-06-16_ANALIZA_followups_*.md)"
tags: ["llm", "rate-limit", "cache", "resilience", "tdd"]
---

# 🧱 Sprint: FIX-03 — Rate-limit + cache LLM + effective_model w handlerach

> **Owner:** /dev + /sec | **Data:** 2026-06-16 | **Bazuje na:** analiza follow-upów

## Cel
Domknięcie 3 follow-upów (analiza, część B+C): wpięcie do **handlerów** czatu mechanizmów, które
były zbudowane, ale nieużywane (`effective_model` z K5, `cache` z S5.1) + nowy throttling.

## Zmiany
- **`core/ratelimit.py`** (NEW): `RateLimiter` (sliding-window, Redis `INCR`+`EXPIRE` + fallback
  proces-lokalny). `chat_limiter` konfigurowalny ENV (`CHAT_RATE_MAX`=30, `CHAT_RATE_WINDOW_S`=60).
- **`chat_deps.get_llm_cache()`** (NEW): provider cache (Redis gdy `REDIS_URL`, inaczej In-Memory; `LLM_CACHE=off` wyłącza).
- **`api_routers/chat.py`** (handlery):
  - **rate-limit** — `_enforce_chat_rate(workspace)` w `handle_chat` + `run_pipeline` (HTTP 429 + Retry-After),
    ręczny check w WS `chat_stream` (close 1013).
  - **effective_model** — `handle_chat` i WS dobierają model przez `effective_model(skill, governor)`
    (polityka tierów + degradacja przy niskim budżecie) zamiast stałej/heurystyki.
  - **cache** — `llm.cache = get_llm_cache()` **tylko** dla skilli `read_only` (świeżość danych live Odoo).

## Decyzje (z analizy)
- Rate-limit jako osobny komponent (nie rozszerzanie `_AuthRateLimiter` — inna semantyka: throttle vs lockout).
- Cache **wąsko** (read-only) — unik podania nieaktualnych danych live jako pewnik.
- effective_model: niskie ryzyko, duża wartość (budżet→tańszy model w produkcji).

## Dowód
`tests/test_ratelimit.py`: limiter (allow→block, niezależność kluczy, okno) + strażnik wpięcia
(handlery używają `_enforce_chat_rate`/`effective_model`/`get_llm_cache`/429/read_only).
Istniejące `test_api`/`test_api_stream`/`test_api_wiring` bez zmian asercji. Pełna suita zielona.

## DoD
- [x] rate-limit na 3 ścieżkach LLM; 429+Retry-After.
- [x] effective_model wpięty (budżet-aware) w handle_chat + WS.
- [x] cache wpięty warunkowo (read-only) + provider Redis/In-Memory + ENV off.
- [x] testy + brak regresji.

> Pozostały follow-up: i18n głębokie (osobny PR I18N-02) — patrz analiza, część A.
