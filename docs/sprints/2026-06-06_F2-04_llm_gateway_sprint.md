---
sprint_id: "F2-04"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-06
closed: null
goal: "Rozbudowa llm_client.py o fallback chain (Claude→GPT→Gemini→Llama), jawny model selection i integrację z TokenGovernor"
prefix: "F2"
complexity: 4
roadmap_ref: "roadmap.md → EPIC-2"
epic_ref: "EPIC-F2-BRAIN"
tags: ["swarm", "llm", "openrouter", "fallback", "token-governor", "tdd"]
---

# 🚀 Sprint: F2-04 LLM Gateway Multi-Model + Fallback Chain

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-06

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Obecny `llm_client.py` obsługuje tylko 1 model (default). Potrzebujemy: (1) jawnego wyboru modelu per skill, (2) fallback chain gdy model niedostępny, (3) logowania kosztu w TokenGovernor.

### Metryka sukcesu (DoD)
`pytest tests/swarm/test_llm_client.py -v` → ALL PASSED (min. 3 nowe testy)

### ⚖️ ZASADY SPRINTU
- 🟠 TDD: Każda nowa metoda (`chat_with_model`, fallback) musi mieć test RED→GREEN
- 🔴 SCOPE: Tylko `smartmyodoo/swarm/llm_client.py` + testy

---

## 🧱 Sekcja B — Podział Zadań

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Definicja `FALLBACK_CHAIN`: `["anthropic/claude-sonnet-4", "openai/gpt-4.1", "google/gemini-2.5-pro", "meta-llama/llama-3.1-70b-instruct"]` | Stała w pliku | [ ] |
| 1.2 | 🔴 RED — Test: `chat_with_model("anthropic/claude-sonnet-4", prompt)` z mockowanym httpx | Failing | [ ] |
| 1.3 | 🟢 GREEN — Impl `chat_with_model(model, prompt)` w `OpenRouterClient` | PASS | [ ] |
| 1.4 | 🔴 RED — Test fallback: model A rzuca HTTPError → próbuje model B → sukces | Failing | [ ] |
| 1.5 | 🟢 GREEN — Impl `chat_with_fallback(prompt)` — iteruje po FALLBACK_CHAIN | PASS | [ ] |
| 1.6 | 🔴 RED — Test: po każdym wywołaniu koszt logowany w TokenGovernor | Failing | [ ] |
| 1.7 | 🟢 GREEN — Integracja: `governor.add_usage(tokens, cost_per_1k, model)` po response | PASS | [ ] |
| 1.8 | **BRAMKA:** `pytest tests/swarm/test_llm_client.py -v` | ✅ ALL GREEN | [ ] |

---

## 📊 PROGRESS BAR

| # | Faza | /arch | /dev | /qa | Status |
|---|------|:-----:|:----:|:---:|:------:|
| 1 | LLM Gateway + Fallback | ✅ | ⬜ | ⬜ | 🔵 |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|-----------------|
| V1 | Testy LLM | `pytest tests/swarm/test_llm_client.py -v` | ALL GREEN |
| V2 | Fallback chain | Test HTTPError → retry z następnym modelem | Sukces na modelu B |
| V3 | TokenGovernor | Koszt zalogowany po wywołaniu | `governor.total_tokens > 0` |

---
_Wygenerowane przy użyciu szablonów TeamEngine._
