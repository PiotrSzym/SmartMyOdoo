---
sprint_id: "TRUST-03"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-25
closed: null
goal: "Zbudować REALNĄ pamięć kontekstu rozmowy wg best practice rynkowego. Dziś LLM NIE dostaje poprzednich tur bieżącej sesji (get_smart_context pomija ją, ładuje tylko skróty innych sesji) — stąd 'price list' → cennik zamiast zadania. Plan: (1) Buffer Window — odtwarzanie ostatnich N tur bieżącej sesji do LLM; (2) Entity Memory + disambiguacja — jawny blok aktywnego kontekstu (projekt + ostatnio pokazane rekordy) i reguła 'preferuj pokazany rekord nad modelem o tej samej nazwie'; (3) Summary Buffer — streszczanie starszych tur w ramach budżetu; (4) wycofanie plastrów TRUST-01/02 + regresja + /qa LIVE."
prefix: "TRUST"
complexity: 8
roadmap_ref: "Analiza /arch 2026-06-25 + research rynkowy (Summary Buffer / Entity Memory / coreference). Po TRUST-02."
parent_sprint: "TRUST-02"
tags: ["conversation-memory", "context-window", "entity-memory", "coreference", "summary-buffer", "token-budget", "trust", "adr-008"]
---

# 🧱 Sprint: TRUST-03 — Fundament pamięci kontekstu rozmowy

> **Architekt:** /arch | **Owner:** /dev | **Review:** /gf-review | **Data:** 2026-06-25
> **Bazuje na:** TRUST-02 (`950c606`) | **Recon:** analiza przechowywania kontekstu (kod) + research best practice (6 źródeł) | **ADR:** ADR-008 (Local-Only), ADR-011 (PII)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch)

### 0A. Business Discovery
- **Dla kogo?** Konsultant Odoo prowadzący naturalną, wieloturową rozmowę o danych.
- **Problem (1 zdanie):** czat **nie ma realnej pamięci bieżącej rozmowy** — LLM nie dostaje poprzednich tur tej sesji, więc gubi, o czym mowa („price list" → model `product.pricelist`/cennik zamiast zadania „Price list possibility" z RMO).
- **Metryka sukcesu:** w rozmowie, w której tura wcześniej pokazano zadanie „Price list possibility", polecenie „dodaj do opisu price list" trafia w **zadanie 6706 (project.task)**, nie w `product.pricelist`; zmiana projektu resetuje kotwicę; koszt tokenów mieści się w `MAX_BUDGET_USD`.
- **ROI:** zamienia „pojedyncze pytania" w realną rozmowę roboczą; usuwa źródło błędów, którego plastry TRUST-01/02 nie sięgały.
- **Źródło:** analiza /arch 2026-06-25 (kod) + research rynkowy.
- **Zakres:** cel LOKALNY (ADR-008). Bez multi-tenant.

### 0B. Fakty — JAK KONTEKST JEST DZIŚ PRZECHOWYWANY (plik:linia)
| # | Fakt | Dowód | Zadanie |
|---|---|---|---|
| 1 | **Baza `chat_messages` trzyma PEŁNĄ historię** (session_id, role, content) — trwałe | `core/models.py:21`; zapis `executor.py:691` | baza OK |
| 2 | **LLM dostaje TYLKO `get_smart_context`** — a ono POMIJA bieżącą sesję, zwraca jednolinijkowe skróty INNYCH sesji | `executor.py:231`, `chat_repository.py:146` (`continue`) | T1 |
| 3 | **Historia bieżącej sesji NIE jest odtwarzana do LLM** — `get_session_messages` wołane TYLKO w UI | `monitoring.py:62` (jedyny consumer) | T1 |
| 4 | **`ConversationScope` (RAM) trzyma tylko `project_id`** — nie rekordy/encje; ginie przy restarcie | `chat_deps.py`, `conversation_scope.py` | T2 |
| 5 | **Kolizja nazw** — „price list" = tytuł zadania ORAZ model `product.pricelist` | /qa LIVE 2026-06-25 | T2 |
| 6 | **Budżet tokenów istnieje** (`TokenGovernor`, `MAX_BUDGET_USD`) — można go użyć do limitu okna | `mcp/token_governor.py`, `.env` | T1/T3 |
| 7 | Plastry TRUST-01/02 (`scope_hint`, `enforce_scope`) wstrzykują 1 fakt (project_id), bo historia nie trafia do modelu | `conversation_scope.py` | T4 |

### 0B-bis. RESEARCH — best practice rynku (2025/2026) → decyzje
| Wzorzec | Źródło | Decyzja |
|---|---|---|
| **Buffer Window (last-N tur dosłownie)** — płaski koszt, baseline | Pinecone/LangChain; OpenAI Cookbook (context trimming) | **D1** → T1 fundament |
| **Summary Buffer (last-N + streszczenie starszych, limit tokenów)** — „domyślny wybór dla produkcji" | Pinecone („start with Summary Buffer"); mem0; OpenAI Cookbook (summarization) | **D2** → T3 |
| **Entity Memory** — śledzenie faktów o encjach, nie pełnych tur (domeny entity-heavy) | LangChain ConversationEntityMemory | **D3** → T2 (kotwica projekt+rekordy) |
| **Coreference / disambiguation względem listy encji** — dwuznaczne odwołania rozwiązuje się dopasowaniem do encji i przepisaniem | coreference-RAG (arXiv 2507.07847); „align ambiguous mention to most probable entry in entity list" | **D3** → T2 (reguła price-list↔cennik) |
| **Token budget: system + kontekst + last-N, 30–50% zapasu na tool-output; oznaczaj streszczenia metadanymi** | Arize; getMaxim; OpenAI Cookbook (`synthetic: true`) | **D4** → T1/T3 |

> **Konsensus:** zacznij od **Buffer Window**, podnieś do **Summary Buffer** dla produkcji; w domenie z encjami dołóż **Entity Memory**; dwuznaczne odwołania rozwiązuj względem **listy encji**. Mapuje się 1:1 na intuicję usera (projekt jako kotwica) i na dzisiejszy bug.

### 0C. User Stories
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-T1 | konsultant | by model PAMIĘTAŁ poprzednie tury tej rozmowy | nie powtarzać kontekstu | KIEDY zadaję follow-up TO LLM dostaje ostatnie N tur bieżącej sesji (zanonimizowane, w budżecie) |
| US-T2a | konsultant | by „price list" (po pokazaniu zadania) trafiało w ZADANIE, nie cennik | dostać sensowną akcję | KIEDY nazwa pasuje do niedawno pokazanego rekordu TO model preferuje rekord nad modelem Odoo o tej samej nazwie |
| US-T2b | konsultant | by kontekst projektu resetował się przy zmianie projektu | nie mieszać projektów | KIEDY zmieniam projekt TO kotwica (aktywny projekt + rekordy) jest aktualizowana/resetowana |
| US-T3 | maintainer | by długa rozmowa nie rozsadzała budżetu | trzymać koszt | KIEDY historia > limit TO starsze tury są streszczane (Summary Buffer), last-N zostaje dosłownie |
| US-T4 | zespół | by plastry TRUST-01/02 nie dublowały nowej pamięci | czysta architektura | KIEDY 1–3 działa TO scope_hint/enforce_scope są wycofane/uproszczone, regresja zielona |

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| Historia bieżącej sesji | `get_session_messages` (`chat_repository.py:52`) | 📐 IN-PATTERN (podłącz do LLM, nie tylko UI) |
| Budowa promptu | `_build_initial_messages` (`executor.py:214`) | 📐 IN-PATTERN (dołóż okno + kotwicę) |
| Budżet tokenów | `TokenGovernor`, `MAX_BUDGET_USD` | 📐 REFERENCE (limit okna/summary) |
| Encje rozmowy | `ConversationScope` (project_id) | 📐 IN-PATTERN (rozszerz do EntityMemory: project + records) |
| PII | `PiiMiddleware.anonymize` | 📐 OBOWIĄZKOWE (historia do LLM = zanonimizowana) |

### 0E. Test Strategy
| Warstwa | Co testować | Narzędzie |
|---|---|---|
| Unit | okno last-N: zwraca ≤N tur bieżącej sesji, zanonimizowane, w limicie tokenów | pytest (mock repo) |
| Unit | EntityMemory: zapamiętuje pokazane rekordy (id+tytuł); reset przy zmianie projektu; blok kontekstu zawiera regułę disambiguacji | pytest |
| Unit | Summary Buffer: gdy >limit → starsze streszczone, last-N dosłowne, summary oznaczone metadanymi | pytest |
| Integracja | sekwencja: pokaż zadania RMO → „dodaj do opisu price list" → trafia w project.task 6706, nie product.pricelist | pytest (mock danych) |
| Regresja | pełna pytest 0 failed; plastry wycofane bez utraty zachowania | pytest |
| /qa LIVE | ta sama rozmowa na Odoo 19: „price list" = zadanie | czat :8001 |

### 0F. US → Test Mapping
| US | Weryfikacja | Prio |
|----|----------|-----|
| US-T1 | `tests/test_conversation_window.py` (nowy) | 🔴 |
| US-T2a/b | `tests/test_entity_memory.py` (nowy) | 🔴 |
| US-T3 | `tests/test_summary_buffer.py` (nowy) | 🟡 |
| US-T4 | regresja + przegląd /gf-review | 🟡 |

### 0G. Security Scope → Sekcja D
ADR-008/011 zachowane. **Historia odtwarzana do LLM MUSI być zanonimizowana** (`_anon` jak obecny user-message) — chmura nigdy nie dostaje surowego PII. EntityMemory trzyma id+tytuł rekordów (tytuł może zawierać PII → anonimizować przy wysyłce, deanonimizować lokalnie). Summary generowany przez LLM = na danych już zanonimizowanych. Budżet tokenów chroni przed kosztem/DoS.

### ⚖️ Decyzje (/arch, na bazie researchu)
- **D1:** Krok 1 = **Buffer Window (last-N tur)** bieżącej sesji do LLM — fundament, największy efekt, najmniejsze ryzyko. N konfigurowalne (ENV), domyślnie ~6 tur. Zanonimizowane.
- **D2:** Krok 3 = **Summary Buffer** — gdy historia > limit tokenów, streść starsze tury (1 wiadomość system, `synthetic=true`), last-N zostaw dosłownie. To „produkcyjny default" rynku.
- **D3:** Krok 2 = **Entity Memory + disambiguacja** — rozszerz `ConversationScope` o ostatnio pokazane rekordy (id+typ+tytuł); wstrzykuj kompaktowy blok „aktywny kontekst" + regułę „preferuj pokazany rekord nad modelem Odoo o tej samej nazwie". Reset przy zmianie projektu.
- **D4:** Limit przez `TokenGovernor`/`MAX_BUDGET_USD`; 30–50% zapasu na tool-output; streszczenia oznaczone metadanymi.
- **D5:** Po 1–3 — **wycofaj plastry** (`scope_hint`/`enforce_scope`) lub sprowadź do EntityMemory; bez regresji.
- **D6 (osobny, drobny):** edge `<PERSON_1>` (deanonymize nie trafia gdy model renumeruje token) — adresowany pobocznie: po pełnej historii model rzadziej renumeruje; jeśli zostanie, fallback w `_deanon` (nierozpoznany token → „[zamaskowane]") jako ostatnia deska. NICE-TO-HAVE.

---

## 🧱 Sekcja B — Podział Zadań (TDD-friendly) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| T1 | **Buffer Window — historia bieżącej sesji do LLM** 🔴: w `_build_initial_messages` ładuj ostatnie N tur tej sesji (`get_session_messages`), zanonimizowane (`_anon`), z limitem tokenów; wstaw między system a bieżącą wiadomość. ENV `CHAT_HISTORY_TURNS` (dom. 6). NIE psuj `get_smart_context` (cross-session zostaje, ale po historii bieżącej). | `smartmyodoo/swarm/executor.py`, `core/chat_repository.py` | D1, D4 | unit: ≤N tur, anonimizacja, limit | ✅ DONE (`get_recent_window` + `_build_initial_messages`; 4 testy; regresja 376/0; LIVE: „price list"→zadanie 6706, nie cennik) |
| T2 | **Entity Memory + disambiguacja** 🔴: rozszerz `ConversationScope` (lub nowy `EntityMemory`) o ostatnio pokazane rekordy (z wyników narzędzi: id, model, tytuł). Wstrzykuj blok „aktywny kontekst" + regułę „preferuj pokazany rekord nad modelem Odoo o tej samej nazwie". Reset przy zmianie projektu. | `smartmyodoo/swarm/conversation_scope.py` (lub nowy moduł), `executor.py` | D3, coreference | unit: capture rekordów, reset, blok+reguła; integ price-list→task 6706 | ✅ DONE (`ConversationScope.capture_records/context_block` + `executor._capture_records`/wstrzyknięcie; 7 testów; regresja 383/0; LIVE: „opis price list"→zadanie 6706) |
| T3 | **Summary Buffer (budżet)** 🟡: gdy historia > limit, streść starsze tury jednym komunikatem system (`synthetic=true`), last-N dosłownie. Reużyj `TokenGovernor`. | `smartmyodoo/swarm/executor.py`, `mcp/token_governor.py` | D2, D4 | unit: trigger po limicie; summary oznaczone; last-N dosłowne | ✅ DONE (`get_history_context` + `_summarize_older` deterministyczne; `synthetic=true`; 5 testów; regresja 388/0; LIVE sanity OK) |
| T4 | **Wycofanie plastrów + regresja + /qa LIVE** 🟡: gdy T1–T3 działa, uprość/wytnij `scope_hint`/`enforce_scope` (lub oprzyj na EntityMemory) bez utraty zachowania; pełna regresja; LIVE „price list"→zadanie. Opcjonalnie D6 fallback `_deanon`. | `conversation_scope.py`, `executor.py`, testy | D5, D6 | regresja 0 failed; LIVE OK; brak martwego kodu | ✅ DONE (wycięto `scope_hint`/`inject_hint`/`_is_followup` — zastąpione `context_block`+`enforce_scope`; `enforce_scope` ZOSTAJE (deterministyczny); D6 `_mask_leftover_tokens`; regresja 387/0; LIVE: „RMO [zamaskowane]", price list→zadanie) |

> **Kolejność /dev:** T1 (fundament — sam rozwiązuje większość) → T2 (kotwica+disambiguacja) → T3 (budżet) → T4 (sprzątanie). Po każdym: pełna pytest `-m 'not e2e'` = 0 failed. NA KOŃCU /qa LIVE.

---

## 🛡️ Sekcja D — Security (/sec)
- [ ] Historia odtwarzana do LLM jest ZANONIMIZOWANA (`_anon`); chmura nie dostaje surowego PII.
- [ ] EntityMemory: tytuły rekordów anonimizowane przy wysyłce, deanonimizacja lokalnie.
- [ ] Summary generowane na danych zanonimizowanych; oznaczone `synthetic`.
- [ ] Limit tokenów (TokenGovernor) chroni przed kosztem/rozdęciem.
- [ ] Brak nowych endpointów; ADR-008 zachowane.

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review)
- [x] US-T1: LLM dostaje ≤N tur bieżącej sesji (`get_recent_window`, ENV `CHAT_HISTORY_TURNS`=6); LIVE potwierdzone.
- [x] US-T2a: jawna kotwica encji (projekt + pokazane rekordy + reguła disambiguacji); LIVE: „opis price list" → zadanie 6706 (project.task), nie product.pricelist.
- [x] US-T2b: zmiana projektu resetuje kotwicę rekordów (`capture_domain` czyści `_records`; test `test_records_reset_on_project_change`).
- [x] US-T3: historia > okno → starsze tury streszczone (deterministycznie, `synthetic`), last-N dosłowne; bez dodatkowego wywołania LLM (zero kosztu/ryzyka context-poisoning).
- [x] US-T4: `scope_hint`/`inject_hint` wycięte (zastąpione `context_block` T2); `enforce_scope` zostaje (deterministyczny); D6 maskowanie resztek tokenów; regresja 387/0; brak martwego kodu.
- [x] /qa LIVE: „pokaż opis price list" → opis zadania „Price list possibility" (project.task), nie cennik; „RMO [zamaskowane]" zamiast surowego tokenu.

### Close Checklist
- [x] Sekcja B = ✅ (T1–T4), status → `DONE`. Merge/roadmap = krok gita (po zapisie usera).
- [ ] Lessons Learned.
- [ ] Merge + roadmap.

---

## 📚 Sekcja F — Lessons Learned (recon /arch)
- **Plastry maskowały brak fundamentu.** TRUST-01/02 (scope_hint/enforce_scope) wstrzykiwały 1 fakt, bo prawdziwa historia rozmowy nie trafiała do LLM. Instynkt: gdy „kontekst się gubi", najpierw sprawdź CZY model w ogóle dostaje historię, zanim dołożysz heurystykę.
- **„Smart Context" oszczędził tokeny kosztem pamięci.** Cross-session skróty zamiast bieżącej historii — oszczędność, która wywołała klasę błędów. Research: właściwa odpowiedź to Summary Buffer (oszczędza I pamięta).
- **Domena Odoo jest entity-heavy** → Entity Memory + disambiguacja to nie ekstra, tylko konieczność (kolizje nazw model↔rekord).

### Źródła (research 2026-06-25)
- Pinecone/LangChain — typy pamięci konwersacyjnej (buffer/window/summary/summary-buffer/entity).
- OpenAI Cookbook — Session memory (context trimming + summarization, `synthetic`, identyfikatory w summary).
- mem0 — chat history summarization 2025. genmind — „Your LLM Has Amnesia".
- Arize / getMaxim — context window management, budżet tokenów (30–50% zapasu).
- coreference-RAG (arXiv 2507.07847) — disambiguacja względem listy encji.

### Handoff
```
/arch (ten artefakt) — DO AKCEPTACJI USERA
   → /dev (T1 okno → T2 entity+disambiguacja → T3 summary → T4 sprzątanie)
   → /sec (historia anonimizowana; budżet)
   → /qa (unit + LIVE: price list = zadanie; reset projektu)
   → /gf-review (gate) → merge → roadmap
```

> Po TRUST-03: czat ma REALNĄ pamięć rozmowy (Buffer/Summary) + kotwicę encji (projekt+rekordy) wg best practice rynku; price-list↔cennik rozwiązane u źródła; plastry wycofane.
