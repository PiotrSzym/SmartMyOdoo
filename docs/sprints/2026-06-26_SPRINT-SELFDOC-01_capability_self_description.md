---
sprint_id: "SELFDOC-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-26
closed: null
goal: "Sprawić, by czat WIARYGODNIE opowiadał o sobie i swoich umiejętnościach — z PRAWDZIWEGO rejestru (skille + tooltips + narzędzia), a NIE z improwizacji LLM. Dziś na pytanie „co potrafisz?\" model wylicza narzędzia z pamięci JEDNEGO aktywnego skilla (niekompletnie, konfabuluje — zrzut usera: pominął odoo_create). Cel: handler SELF_DESCRIBE, który czyta SKILL_REGISTRY + /api/skills tooltips + TOOL_REGISTRY i zwraca kompletny, zgodny z prawdą opis. Spójne z motywem TRUST (zero konfabulacji o własnych możliwościach)."
prefix: "SELFDOC"
complexity: 4
roadmap_ref: "Analiza /arch 2026-06-26 (self-description). Po WRITE-01. Powiązane: TRUST (anty-konfabulacja), DOC-01/02 (centrum docs)."
parent_sprint: null
tags: ["self-description", "capabilities", "anti-confabulation", "skills", "trust", "discoverability"]
---

# 🧱 Sprint: SELFDOC-01 — Wiarygodny self-opis czatu

> **Architekt:** /arch | **Data:** 2026-06-26

## 0A. Problem (1 zdanie)
Czat nie umie wiarygodnie powiedzieć, co potrafi — uruchamia JEDEN skill na turę, więc LLM widzi tylko jego narzędzia i przy „co potrafisz?\" IMPROWIZUJE (niekompletnie / konfabuluje), zamiast czytać prawdziwą mapę zdolności.

## 0B. Fakty (kod, plik:linia)
| Fakt | Dowód |
|---|---|
| `/api/skills` ma KURATOROWANE opisy (tooltip+przykład) każdego skilla — SSoT opisów | `api_routers/chat.py:73-130` |
| `SKILL_REGISTRY` = skille→SkillConfig (system_prompt, allowed_tools, red_flags) | `swarm/skills/registry.py:17` |
| `TOOL_REGISTRY` = narzędzia + schematy | `swarm/tools.py:18` |
| Docs tab (`docs.js`) ma intro „Czym jest SmartMyOdoo\" + funkcje — pasywne (człowiek czyta) | `ui/js/components/docs.js:48` |
| Czat improwizuje self-opis z 1 aktywnego skilla → niekompletny | zrzut usera (pominięty `odoo_create`) |

## ⚖️ Decyzje (/arch)
- **D1 — Wykrycie intencji self-opisu:** „co potrafisz / co umiesz / opowiedz o sobie / jakie masz umiejętności / kim jesteś / pomoc / help / what can you do\" → kategoria SELF_DESCRIBE (heurystyka + opis w prompcie dispatchera). Działa PL i EN.
- **D2 — Opis GROUNDED, nie improwizowany.** Serwer buduje opis z PRAWDZIWEGO rejestru: intro (z docs.js „Czym jest…\") + lista skili z `/api/skills` tooltipami + kluczowe funkcje (Shadow Mode, PII, Multi-Workspace, tryb 🟢/🔴). LLM NIE wymyśla — albo zwracamy gotowy tekst, albo LLM tylko ŁADNIE FORMUŁUJE z dostarczonych faktów („opisuj WYŁĄCZNIE z poniższej listy, nic nie dodawaj\").
- **D3 — SSoT = `/api/skills` tooltips.** Nie duplikujemy opisów w 3 miejscach — aggregator czyta istniejące tooltips (te z UI), żeby docs/panel/czat mówiły jednym głosem.
- **D4 — Anty-konfabulacja (TRUST):** opis zawiera TYLKO realnie zarejestrowane skille/narzędzia; test pilnuje, że nie pojawia się nic spoza rejestru.

## 0C. User Stories
| ID | JAKO | CHCĘ | KIEDY → TO |
|----|------|------|-----------|
| US-1 | user | spytać „co potrafisz?\" i dostać PRAWDZIWĄ listę | KIEDY pytam o możliwości TO opis z rejestru (skille+funkcje), kompletny |
| US-2 | user | by opis nie zmyślał | KIEDY self-opis TO tylko realne skille/narzędzia (zero wymyślonych) |
| US-3 | user | spójność docs/panel/czat | KIEDY czytam opis w czacie TO zgodny z panelem skili (te same tooltips) |

## 🧱 Sekcja B — Zadania (/dev)
| # | Zadanie | Pliki | Testy | Status |
|---|---------|-------|-------|--------|
| T1 | **Aggregator zdolności** — `build_capabilities()` (intro + skille z tooltipami + kluczowe funkcje + lista narzędzi zapisu/odczytu) z `SKILL_REGISTRY`/`/api/skills`/`TOOL_REGISTRY`. SSoT = tooltips. | NEW `smartmyodoo/swarm/capabilities.py`, reuse `chat.py` get_skills | unit: zawiera realne skille; nie zawiera wymyślonych | ✅ DONE |
| T2 | **Intencja SELF_DESCRIBE + grounded odpowiedź** — wykryj pytanie o możliwości; zwróć opis z T1 (bez improwizacji LLM, albo LLM formułuje z dostarczonych faktów). | `swarm/dispatcher.py`, `api_routers/chat.py` | „co potrafisz"→opis z rejestru; PL+EN | ✅ DONE (`capabilities.is_self_describe_query` + short-circuit `chat.py`; LIVE: category=SELF_DESCRIBE, model=null) |
| T3 | **Regresja + /qa LIVE** — pełna pytest; LIVE: „co potrafisz?\" → lista 8+ skili + Shadow Mode/PII/🟢🔴, zero zmyślonych. | testy | 0 failed; LIVE wiarygodny | ✅ DONE |

## 🛡️ Sekcja D — Security/Trust
- [ ] Opis NIE ujawnia sekretów/PII (tylko nazwy zdolności).
- [ ] Anty-konfabulacja: tylko realne skille/narzędzia (test).

## 🔬 DoD
- [ ] US-1: „co potrafisz?\" → kompletny opis z rejestru (LIVE).
- [ ] US-2: brak wymyślonych zdolności (test grounding).
- [ ] US-3: opis spójny z `/api/skills` (te same tooltips).
- [ ] Regresja 0 failed.

> Po SELFDOC-01: SmartMyOdoo umie sam, wiarygodnie opowiedzieć kim jest i co potrafi — z prawdziwego rejestru, bez zmyślania. Domyka motyw TRUST również na poziomie „wiedzy o sobie\".
