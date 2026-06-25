---
sprint_id: "TRUST-02"
workspace: "SmartMyOdoo"
status: "IN_PROGRESS"
created: 2026-06-25
closed: null
goal: "Domknąć trzy krawędzie ujawnione w /qa LIVE TRUST-01: (A) confab-guard nad-strzela (literówka brana za maskę) i maskuje niespójnie ([zamaskowane] blokuje deanonymize) → guard v2 verbatim-only; (B) retencja kontekstu krucha — scope gubi projekt przy nazwie zadania / intencji zapisu → deterministyczny filtr project_id na warstwie narzędzia; (C) brak regresji na te scenariusze → testy 3 trybów awarii."
prefix: "TRUST"
complexity: 5
roadmap_ref: "TRUST-01 /qa LIVE (2026-06-25): czat trzyma kontekst tylko dla czystych follow-upów; confab-guard ma 2 ostre krawędzie."
parent_sprint: "TRUST-01"
tags: ["pii", "confab-guard", "conversation-scope", "deterministic", "trust", "regression", "adr-008"]
---

# 🧱 Sprint: TRUST-02 — Hardening kontekstu i maskowania

> **Architekt:** /arch | **Owner:** /dev | **Review:** /gf-review | **Data:** 2026-06-25
> **Bazuje na:** TRUST-01 (main + zmiany w drzewie) | **Recon:** /qa LIVE TRUST-01 (2 rozmowy na żywej bazie Odoo 19, read-only) | **ADR:** ADR-008 (Local-Only), ADR-011 (PII)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch)

### 0A. Business Discovery
- **Dla kogo?** Konsultant Odoo prowadzący WIELOTUROWĄ rozmowę o danych.
- **Problem (1 zdanie):** po TRUST-01 czat trzyma kontekst tylko przy „czystym" follow-upie — **gubi projekt, gdy nazwiesz zadanie lub zmienisz intencję**, a confab-guard czasem bierze zwykłe słowo za maskę i blokuje przywrócenie prawdziwej nazwy lokalnemu userowi.
- **Metryka sukcesu:** w sekwencji (RMO → „opis zadania price list" → „dodaj test") czat NIE wychodzi poza projekt 136 bez wyraźnej zgody; literówka NIE jest traktowana jak maska; lokalny user widzi prawdziwe nazwy (deanonymize), a chmura nadal tylko tokeny.
- **ROI:** robi z czatu narzędzie do PRACY wieloturowej, nie tylko pojedynczych pytań.
- **Źródło:** /qa LIVE TRUST-01 (2026-06-25), zweryfikowane na bazie.
- **Zakres:** cel LOKALNY (ADR-008). Bez zmian izolacji/multi-tenant.

### 0B. Fakty (recon /qa LIVE + plik:linia)
| # | Fakt | Dowód | Zadanie |
|---|---|---|---|
| 1 | **Confab-guard daje 2 ścieżki** — „cytuj dosłownie" (deanonymize OK) vs „[zamaskowane]" (blokuje) | `executor.py:18-26`; deanonymize `executor.py:80-81` | T1 |
| 2 | **Guard nad-strzela** — literówkę „jkie" model uznał za zamaskowany token | rozmowa /qa LIVE tura 1 | T1 |
| 3 | **Maskowanie niespójne** — raz „RMO Henk Molenkamp" (deanonymize), raz „RMO [zamaskowane]" | /qa LIVE tura 2 vs test TRUST-01 | T1 |
| 4 | **scope_hint = podpowiedź probabilistyczna**, wąskie słowa-sygnały | `conversation_scope.py` (`_FOLLOWUP_HINTS`, `scope_hint`) | T2 |
| 5 | **Gubi projekt przy nazwie zadania** — „opis price list" → globalne szukanie, zwróciło zadanie 2671 z projektu SO276-Enbio (NIE RMO) | /qa LIVE tura 3; weryfikacja na bazie (RMO=136 ma 2 zadania) | T2 |
| 6 | **Gubi projekt przy intencji zapisu** — „dodaj test" → „2920 zadań" | /qa LIVE tura 4 | T2 |
| 7 | Hak `capture_domain` już istnieje (można dołożyć enforce) | `executor.py:112` | T2 |
| 8 | Brak testów na te 3 tryby awarii | recon | T3 |

> **Ground-truth (Odoo 19):** RMO Henk Molenkamp (id=136) = 2 zadania (6862 Audtyt Hinduskich modułów, 6706 Price list possibility). „Zmiana logiki w cenniku (price list)" = zadanie 2671, projekt SO276-Enbio (id=3) — NIE RMO.

### 0C. User Stories
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-T1a | konsultant | by literówka/zwykłe słowo NIE było brane za maskę | nie dostać absurdalnej odpowiedzi „to zamaskowana wartość" | KIEDY słowo nie ma formy `<TYP_numer>` TO model NIE traktuje go jak maski |
| US-T1b | konsultant (lokalny) | by widzieć PRAWDZIWE nazwy (po deanonymize), nie „[zamaskowane]" | korzystać z danych, do których mam dostęp (vault) | KIEDY model cytuje token dosłownie TO warstwa lokalna podmienia na realną wartość |
| US-T2a | konsultant | by „opis zadania X" trzymał aktywny projekt | nie dostać zadania z innego projektu | KIEDY aktywny project scope i pytanie o `project.task` bez innego projektu TO domena dostaje `project_id` aktywnego projektu |
| US-T2b | konsultant | by móc świadomie wyjść poza projekt | szukać globalnie gdy trzeba | KIEDY powiem „wszystkie/globalnie" lub nazwę inny projekt TO scope się NIE narzuca |
| US-T3 | zespół | by te 3 tryby awarii miały testy | TRUST-02 się nie cofnął | KIEDY regresja TO scenariusze (literówka, follow-up po nazwie, zapis) są pokryte |

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| Confab-guard | `PII_CONFAB_GUARD` + `build_system_prompt` (`executor.py:18-38`) | 📐 IN-PATTERN (uprość do verbatim-only) |
| Deanonymize | `_deanonymize` (`executor.py:80-81`) | 📐 REFERENCE (verbatim echo go wyzwala) |
| Scope rozmowy | `ConversationScope.capture_domain/inject_hint` | 📐 IN-PATTERN (dołóż deterministyczny enforce) |
| Enforce na narzędziu | hak `capture_domain` w pętli narzędzi (`executor.py:112`) | 📐 IN-PATTERN (dołóż `enforce_scope` przy budowie args) |

### 0E. Test Strategy
| Warstwa | Co testować | Narzędzie |
|---|---|---|
| Unit | guard v2: brak „[zamaskowane]" w regule; instrukcja „verbatim only"; słowo bez `<>` nie maska | pytest |
| Unit | `enforce_scope`: domena `project.task` bez project_id + aktywny scope → doklejony `[(project_id,=,X)]`; „wszystkie"/inny projekt → bez doklejania | pytest |
| Integracja | sekwencja RMO → „opis price list" → trzyma project 136 (nie 2671); „dodaj test" → pyta w kontekście RMO, nie „2920" | pytest (mock danych) |
| Regresja | pełna pytest 0 failed | pytest |

### 0F. US → Test Mapping
| US | Weryfikacja | Prio |
|----|----------|-----|
| US-T1a/b | `tests/test_pii_confab_guard.py` (rozszerzony: verbatim-only, nie-token nie maskowany) | 🔴 |
| US-T2a/b | `tests/test_scope_enforce.py` (nowy) | 🔴 |
| US-T3 | `tests/test_dispatcher_context.py` (rozszerzony o 3 tryby) | 🟡 |

### 0G. Security Scope → Sekcja D
ADR-008/011 zachowane. **Verbatim-only NIE odsłania danych chmurze** — model nadal dostaje tylko token; deanonymize działa WYŁĄCZNIE lokalnie (po stronie serwera, dla lokalnego usera). `enforce_scope` operuje na technicznym `project_id`, nie na PII.

### ⚖️ Decyzje (/arch)
- **D1 (Problem A → A1):** Confab-guard v2 = JEDNA reguła „cytuj token `<TYP_numer>` DOSŁOWNIE; nigdy nie zgaduj, nigdy nie pisz [zamaskowane], słowo bez nawiasów ostrokątnych NIE jest maską". Usuwa ścieżkę „[zamaskowane]" (blokowała deanonymize i napędzała niespójność). Naprawia objawy 2 i 3 jednym fixem.
- **D2 (Problem B → B2 + B1):** Deterministyczny `enforce_scope` na warstwie narzędzia (prymarne) + szersze brzmienie hintu (uzupełnienie). Enforce omija się jawnie: user mówi „wszystkie/globalnie" albo nazywa inny projekt.
- **D3:** Brak nowego modelu/endpointu. Czysta logika + prompt.

---

## 🧱 Sekcja B — Podział Zadań (TDD-friendly) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| T1 | **Confab-guard v2 (verbatim-only)** 🔴: przepisz `PII_CONFAB_GUARD` — maska = wyłącznie `<TYP_numer>`; cytuj DOSŁOWNIE; NIGDY nie zgaduj, NIGDY „[zamaskowane]", słowo bez `<>` NIE jest maską. Zaktualizuj `build_system_prompt` (idempotencja po nowym markerze, nie po „[zamaskowane]"). | `smartmyodoo/swarm/executor.py` | D1 | guard verbatim-only; zakaz „[zamaskowane]"; zwykłe słowo nie maska | ✅ DONE (`executor.py:18-46`; +3 testy; LIVE: tokeny cytowane dosłownie, zero „Billing Type") |
| T2 | **Deterministyczny scope enforce** 🔴: w `ConversationScope` dodaj `enforce_scope(workspace, session, tool_name, args, message)` — gdy aktywny `project_id`, narzędzie dotyczy `project.task`/zadań, a domena nie ma `project_id` i message nie sygnalizuje „wszystkie/globalnie"/innego projektu → doklej `[(project_id,=,X)]`. Wepnij w pętlę narzędzi executora (przy budowie args, obok `capture_domain` `executor.py:112`). Rozszerz hint (B1). | `smartmyodoo/swarm/conversation_scope.py`, `smartmyodoo/swarm/executor.py` | D2, `executor.py:112` | unit `enforce_scope` + furtki | ✅ DONE (`conversation_scope.py` + `executor.py` wpięte 2 ścieżki; LIVE: „opis price list" został w RMO, nie SO276; „dodaj" → id 6706/proj 136, nie 2920) |
| T3 | **Regresja 3 trybów** 🟡: rozszerz testy o: (1) literówka „jkie" nie jest maską, (2) follow-up po nazwie zadania trzyma projekt (nie wychodzi do 2671/SO276), (3) intencja zapisu dziedziczy scope (nie „2920"). | `tests/test_pii_confab_guard.py`, `tests/test_scope_enforce.py`, `tests/test_dispatcher_context.py` | 0F | 3 tryby + furtki | ✅ DONE (`test_scope_enforce.py` 11 testów; regresja 372 passed/0 failed) |

> **Kolejność /dev:** T1 (guard v2 — najtańszy, 2 bugi) → T2 (enforce — rdzeń) → T3 (regresja). Po każdym: pełna pytest `-m 'not e2e'` = 0 failed. NA KOŃCU /qa LIVE: powtórz sekwencję RMO→„opis price list"→„dodaj test" na :8001 i potwierdź brak wycieku do innego projektu.

---

## 🛡️ Sekcja D — Security (/sec)
- [ ] Verbatim-only nie wysyła danych do chmury — LLM dalej widzi tylko token; deanonymize wyłącznie lokalnie.
- [ ] `enforce_scope` operuje na `project_id` (technicznym), nie na PII; nie loguje wartości.
- [ ] Brak nowych endpointów / modeli.

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review)
- [x] US-T1a: guard precyzuje „maska = wyłącznie `<TYP_numer>`"; literówka/zwykłe słowo nie jest maską (test `test_confab_guard_says_plain_word_is_not_a_mask`). LIVE: tokeny cytowane dosłownie.
- [⚠️] US-T1b: model cytuje token DOSŁOWNIE (verbatim-only ✅, koniec „Billing Type"), ALE deanonymize czasem nie trafia, bo model RENUMERUJE token (`<PERSON_1>` zamiast utworzonego numeru) → user widzi surowy token. **Nowy edge → TRUST-03** (nie błąd danych, kwestia round-tripu PII).
- [x] US-T2a: LIVE — „opis zadania price list" został w RMO (id 6706), NIE zwrócił 2671/SO276.
- [x] US-T2b: „wszystkie"/inny projekt → scope NIE narzucony (testy furtek w `test_scope_enforce.py`).
- [x] US-T3: 11 testów w `test_scope_enforce.py` + 3 nowe w `test_pii_confab_guard.py` (3 tryby awarii).
- [x] Regresja: pełna pytest **372 passed, 2 skipped, 0 failed**.
- [x] /qa LIVE: RMO→„opis price list"→„dodaj test" — wszystko trzyma projekt 136; zapis bezpiecznie zablokowany przez Shadow Mode.

### Close Checklist
- [ ] Sekcja B = ✅, status → `DONE`, `closed`.
- [ ] Lessons Learned.
- [ ] Merge + roadmap.

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa po realizacji)

### Recon /arch (TRUST-02, 2026-06-25)
- **Podpowiedź ≠ gwarancja.** scope_hint (prompt) gubi się, bo to sugestia dla modelu. Egzekwowanie zakresu należy robić DETERMINISTYCZNIE na warstwie narzędzia, nie prosić o nie modelu.
- **„Bezpieczna" ścieżka [zamaskowane] szkodziła.** Druga opcja w confab-guardzie blokowała deanonymize i odbierała lokalnemu userowi dane, do których ma prawo. Mniej opcji = mniej niespójności.
- **/qa LIVE łapie to, czego unit nie złapie.** Wszystkie 42 testy TRUST-01 były zielone, a krawędzie wyszły dopiero w realnej rozmowie. Instynkt: po sprincie z LLM zawsze 1 przebieg /qa LIVE.

---

### Handoff
```
/arch (ten artefakt) — DO AKCEPTACJI USERA
   → /dev (T1 guard v2 → T2 enforce → T3 regresja)
   → /sec (verbatim-only nie wysyła do chmury; enforce na project_id)
   → /qa (unit + LIVE: RMO→opis→zapis trzyma projekt 136)
   → /gf-review (gate) → merge → roadmap
```

> Po TRUST-02: rozmowa wieloturowa trzyma projekt deterministycznie, confab-guard nie nad-strzela, lokalny user widzi prawdziwe nazwy. SaaS/multi-tenant nadal POZA (ADR-008).
