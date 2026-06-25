---
sprint_id: "TRUST-01"
workspace: "SmartMyOdoo"
status: "IN_PROGRESS"
created: 2026-06-25
closed: null
goal: "Podnieść WIARYGODNOŚĆ odpowiedzi czatu o danych Odoo: (1) model nie zgaduje zamaskowanych tokenów PII, (2) presidio nie nad-maskuje terminów biznesowych, (3) connector wykrywa i respektuje wersję Odoo (16/18/19), (4) realny tier PREMIUM + aktualne modele, (5) dispatcher nie gubi kontekstu projektu między turami, (6) odpowiedzi mają provenance (źródło/wersja/maska)."
prefix: "TRUST"
complexity: 7
roadmap_ref: "Sesja diagnostyczna 2026-06-25 (czat Odoo: błędne nazwy projektu/zadań, zgubiony filtr, model o generację do tyłu). Po WIRE-01/CLEAN-01."
parent_sprint: null
tags: ["odoo", "pii", "llm-routing", "version-aware", "trust", "dispatcher", "adr-008"]
---

# 🧱 Sprint: TRUST-01 — Wiarygodność odpowiedzi czatu o Odoo

> **Architekt:** /arch | **Owner:** /dev | **Review:** /gf-review | **Data:** 2026-06-25
> **Bazuje na:** main (`9314fd5`) | **Recon:** sesja diagnostyczna na żywej bazie Odoo 19 (read-only, klucz z vaultu) | **ADR:** ADR-008 (Local-Only), ADR-011 (Logging/PII), KEY-01 (model policy)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch)

### 0A. Business Discovery
- **Dla kogo?** Operator/konsultant Odoo używający czatu do pytań o dane (projekty, zadania, kontakty, faktury).
- **Problem (1 zdanie):** czat zwraca **poprawne liczby, ale niewiarygodne nazwy własne i czasem zły zakres** — myli nazwy projektu/zadań (halucynacja na zamaskowanym PII), gubi filtr projektu między turami, a connector działa „na ślepo" wobec wersji Odoo (16/18/19 w vaultcie).
- **Metryka sukcesu:** w scenariuszu regresji (projekt RMO) czat zwraca **prawdziwą nazwę projektu** (lub jawne „[zamaskowane]"), **2 zadania tego projektu** (nie 2920), a zapytania nie wysypują się na polach nieistniejących w danej wersji Odoo.
- **ROI:** czat staje się **godny zaufania do decyzji** — bez tego konsultant musi ręcznie weryfikować każdą nazwę, co kasuje wartość asystenta.
- **Źródło:** sesja 2026-06-25 — weryfikacja odpowiedzi modelu na ground-truth z żywej bazy Odoo 19.
- **Zakres:** cel LOKALNY (ADR-008). Bez zmian w architekturze izolacji/multi-tenant.

### 0B. Fakty (recon /arch + dowody na żywej bazie, plik:linia)
| # | Fakt | Dowód | Zadanie |
|---|---|---|---|
| 1 | **Model konfabuluje zamaskowane tokeny PII** — `RMO <PERSON_2>` → „RMO Billing Type"; `<LOCATION_1> list possibility` → „can list possibility" | `PiiMiddleware.anonymize` (`security/pii/middleware.py:25`) na realnych nazwach; czat pokazał zmyślone nazwy | T1 |
| 2 | **Presidio nad-maskuje terminy biznesowe** — `'Price'`→LOCATION, `'Audtyt Hinduskich'`→PERSON (false-positive) | uruchomienie middleware na nazwach zadań projektu RMO | T2 |
| 3 | **Connector ślepy na wersję Odoo** — `connect()` robi tylko `authenticate()`, pola hardkodowane | `mcp/odoo_client.py:53-59`, `core/odoo_connector.py` (brak `version()`); wersję zna TYLKO swarm `recon.py:36` | T3 |
| 4 | **Różnice pól między wersjami są ogromne** — `project.task`: 200 pól (v16) vs 166 (v19); `analytic_account_id` tylko v16, `billing_type` tylko v19 | porównanie `fields_get` na instancjach 16 i 19 z vaultu | T3 |
| 5 | **PREMIUM == STANDARD; modele o generację do tyłu** — oba tiery = `claude-sonnet-4.5` | `swarm/model_policy.py:19-37` (PREMIUM duplikuje STANDARD); aktualne: sonnet-4.6/opus-4.8/haiku-4.5 | T4 |
| 6 | **Dispatcher gubi kontekst projektu** — „jakie opisy w zadaniach" zwróciło 2920 (wszystkie) zamiast 2 zadań RMO; dispatcher na llama-3.1-8b | `chat.py:195` (`classify_intent`), `model_policy.py:21` (CHEAP=llama-8b) | T5 |
| 7 | **Brak provenance** — model podaje liczby/nazwy bez źródła i bez oznaczenia maskowania | obserwacja czatu (sesja 2026-06-25) | T6 |
| 8 | Vault ma 4 aktywne credentiale na 3 workspace, Odoo 16/18/19 jednocześnie | diagnostyka vault (read-only, sesja) | kontekst T3 |

> **Ground-truth (Odoo 19, read-only):** projekt „rmo" = **RMO Henk Molenkamp** (id=136), **2 zadania** (`Audtyt Hinduskich modułów` — opis pusty; `Price list possibility` — opis 613 zn.); **102 projekty**; **2920 zadań** łącznie. Liczby od modelu były OK; nazwy — nie.

### 0C. User Stories
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-T1 | konsultant | by model NIE zgadywał zamaskowanych nazw | nie dostać zmyślonej nazwy jako faktu | KIEDY rekord ma `<PERSON_x>`/`<LOCATION_x>` TO odpowiedź cytuje „[zamaskowane]", nie wymyśla |
| US-T2 | konsultant | by terminy biznesowe nie były maskowane jak PII | widzieć „Price list", nie „[LOCATION]" | KIEDY nazwa zawiera słowo z allow-listy (Price, Audyt, …) TO presidio jej nie maskuje |
| US-T3 | operator | by zapytania respektowały wersję Odoo | brak błędów/pustych wyników na 16 vs 19 | KIEDY connect TO wykryta wersja + `fields_get` filtruje pola; brak pola = jawny błąd, nie cisza |
| US-T4 | maintainer | by audyty (finanse/security) szły mocniejszym modelem niż CRUD | jakość proporcjonalna do ryzyka | KIEDY skill=FINANCIAL/SECURITY_AUDIT TO model = PREMIUM (opus-4.8) ≠ STANDARD |
| US-T5 | konsultant | by follow-up „a opisy?" trzymał się projektu z poprzedniej tury | nie dostać 2920 zamiast 2 | KIEDY pytanie nawiązuje do poprzedniego zakresu TO dispatcher dziedziczy `project_id` |
| US-T6 | konsultant | by odpowiedź pokazywała źródło (wersja Odoo, ile rekordów, ile zamaskowanych) | móc zaufać/zweryfikować | KIEDY czat zwraca dane TO stopka provenance: „Odoo 19 · N rekordów · k zamaskowanych" |

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| Wykrywanie wersji Odoo | `common.version()` już w `swarm/recon.py:36` (EnvironmentInfo) | 📐 IN-PATTERN (przenieś do connectora czatu) |
| Maskowanie PII | `security/pii/middleware.py` + `recognizers.py` (presidio) | 📐 IN-PATTERN (dołóż allow-listę) |
| Routing modelu per skill | `swarm/model_policy.py` (tier→model, ENV-override) | 📐 IN-PATTERN (zaktualizuj modele + rozdziel PREMIUM) |
| Dispatcher intencji | `dispatcher.classify_intent` (`chat.py:195`) | 📐 REFERENCE (kontekst rozmowy + mocniejszy model) |
| Connector Odoo | `core/odoo_connector.py` / `mcp/odoo_client.py` | 📐 IN-PATTERN (dodaj version + fields_get guard) |

### 0E. Test Strategy
| Warstwa | Potrzebna? | Co testować | Kto | Narzędzie |
|---|:--:|---|:--:|---|
| Unit | ✅ | PII allow-lista (Price/Audyt nie maskowane); confab-guard w prompt buildzie; `effective_model` per skill (PREMIUM≠STANDARD) | /dev | pytest |
| Unit | ✅ | connector: `version_info` ustawione po connect; `fields_get` odsiewa nieistniejące pola; brak pola → wyjątek/log, nie cisza | /dev | pytest (mock XML-RPC) |
| Integracja | ✅ | dispatcher dziedziczy `project_id` w follow-upie (RMO → „opisy" = 2, nie 2920) | /dev+/qa | pytest |
| E2E/manualny | ✅ | scenariusz RMO na żywej bazie: nazwa = „RMO Henk Molenkamp" lub „[zamaskowane]"; 2 zadania | /qa | czat + ground-truth |
| Regresja | ✅ | pełna pytest 0 failed; brak nowych masek na korpusie testowym | /qa | pytest |

### 0F. US → Test Mapping
| US | Scenariusz | Plik/Weryfikacja | Priorytet |
|----|------------|----------|-----------|
| US-T1 | `<PERSON_x>` w danych → odpowiedź nie zmyśla | nowy `tests/test_pii_confab_guard.py` + review promptu | 🔴 |
| US-T2 | „Price"/„Audyt" nie maskowane | `tests/test_pii_*` (allow-lista) | 🔴 |
| US-T3 | version + fields_get | `tests/test_odoo_connector_version.py` | 🔴 |
| US-T4 | FINANCIAL/SECURITY → opus-4.8 | `tests/test_model_policy.py` (rozdział tierów) | 🟡 |
| US-T5 | follow-up trzyma `project_id` | `tests/test_dispatcher_context.py` | 🟡 |
| US-T6 | stopka provenance | review /qa (UI) | 🟢 |

### 0G. Security Scope → Sekcja D
ADR-008/011 zachowane. **PII to kontrola bezpieczeństwa** — allow-lista NIE może odsłonić realnego PII (nazwiska, e-maile): dozwolone TYLKO terminy biznesowe (Price, Audit, Invoice…), nigdy wzorce osób. Klucze Odoo nadal wyłącznie z vaultu. Zero nowych endpointów. Provenance NIE może logować wartości sekretów ani pełnych danych PII.

### ⚖️ Zasady / Decyzje architektoniczne (/arch)
- **D1 — Confab-guard = instrukcja systemowa, nie post-processing.** Najtańszy, najpewniejszy: model dostaje regułę „tokenów `<PERSON_x>`/`<LOCATION_x>`/`<…_x>` NIE rozwijaj — cytuj dosłownie / mów „[zamaskowane]". (Sekundarnie: walidator odpowiedzi może wykryć, że model wstawił słowo w miejsce tokenu.)
- **D2 — Modele przez ENV, nie hardcode.** `MODEL_TIER_*` w `.env`/`.env.example`. PREMIUM rozdzielony od STANDARD. Slug OpenRouter **do weryfikacji na openrouter.ai** (kierunek: `anthropic/claude-haiku-4.5` / `…sonnet-4.6` / `…opus-4.8`).
- **D3 — Wersja Odoo wykrywana RAZ przy connect i cache'owana per (workspace).** Nie próbkować co request. `fields_get` cache per (workspace, model).
- **D4 — Brak pola = FAIL LOUD.** Zapytanie o pole nieistniejące w danej wersji → log + jawny komunikat, nigdy ciche puste (to napędzało nieufność).
- **D5 — Dispatcher: kontekst rozmowy + rozważ haiku-4.5 zamiast llama-8b.** Błąd klasyfikacji kaskaduje (zły skill→zły tier→zły filtr). Mocniejszy tani model + przenoszenie `project_id`/ostatniego zakresu między turami.

---

## 🧱 Sekcja B — Podział Zadań (TDD-friendly) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| T1 | **Confab-guard PII** 🔴: do promptu systemowego czatu reguła „nie zgaduj tokenów `<…_x>` — cytuj jako [zamaskowane]". Opcjonalnie walidator odpowiedzi wykrywający podmianę tokenu. | prompt systemowy (`api_routers/chat.py` / `swarm/skills/*`), `security/pii/*` | D1 | unit: dane z `<PERSON_1>` → odpowiedź nie zawiera zmyślonej nazwy | ✅ DONE (reguła w `executor.py:14-35`; test pass) |
| T2 | **Allow-lista PII** 🔴: terminy biznesowe (Price, Audit, Invoice, Sale, Order, Stock…) nie maskowane; podnieść próg pewności PL jeśli trzeba. NIE odsłaniać osób/e-maili. | `security/pii/recognizers.py`, `middleware.py` | ADR-011 | unit: 'Price list'/'Audyt' nie maskowane; 'Henk Molenkamp' DALEJ maskowane | ✅ DONE (`recognizers.py` allow-lista + `middleware.py:37`; test pass) |
| T3 | **Version-aware connector** 🔴: w `connect()` zapisać `version_info`/`major` (`common.version()`); `fields_get` guard — brać tylko istniejące pola, brak pola → log+wyjątek (fail loud). Cache per (workspace, model). | `core/odoo_connector.py`, `mcp/odoo_client.py` | `recon.py:36`, D3/D4 | unit (mock XML-RPC): version ustawione; pole spoza wersji → wyjątek nie cisza | ✅ DONE (`odoo_client.py:67-98` version+fields_get cache; test pass) |
| T4 | **Refresh routingu modeli** 🟡: `.env`/`.env.example` — CHEAP=haiku-4.5, STANDARD=sonnet-4.6, PREMIUM=opus-4.8 (rozdzielony!). Komentarz: slug do weryfikacji na OpenRouter. | `.env.example`, `swarm/model_policy.py` (komentarze), docs | KEY-01, D2 | unit: `effective_model('FINANCIAL_AUDIT')` ≠ `effective_model('ODOO_CRUD')` | ✅ DONE (slugi zweryf. na OpenRouter; PREMIUM≠STANDARD; +3 testy; serwer zrestartowany) |
| T5 | **Dispatcher: kontekst + model** 🟡: przenosić `project_id`/ostatni zakres między turami (follow-up „a opisy?" trzyma projekt); dispatcher na mocniejszym tanim modelu (haiku-4.5). | `api_routers/chat.py`, dispatcher, `model_policy.py` | D5 | integ: po „ile zadań w RMO" → „jakie opisy" = 2 (nie 2920) | ✅ DONE (`conversation_scope.py`; wpięte `chat.py:244/422/548`; test pass) |
| T6 | **Provenance odpowiedzi** 🟢: stopka „Odoo {wersja} · {N} rekordów · {k} zamaskowanych" w odpowiedzi czatu (UI + dane z connectora/PII). Bez logowania wartości. | `smartmyodoo/ui/*`, `api_routers/chat.py` | D4, 0G | review /qa: stopka widoczna, liczby zgodne | ✅ DONE (`provenance.py`; wpięte `executor.py:337-439`; test pass) |

> **TDD/kolejność /dev:** T2 (allow-lista — fundament) → T1 (confab-guard) → T3 (version-aware) → T5 (dispatcher) → T4 (ENV modeli — szybkie, niezależne) → T6 (provenance — na końcu, spina). Po każdej zmianie: pełna pytest 0 failed.

---

## 🛡️ Sekcja D — Security (/sec)
- [ ] Allow-lista PII zawiera WYŁĄCZNIE terminy biznesowe; żaden wzorzec osoby/e-mail/telefonu nie został osłabiony (test: 'Henk Molenkamp', e-mail dalej maskowane).
- [ ] Confab-guard nie odsłania oryginału — model nadal nie widzi wartości spod maski.
- [ ] Provenance nie loguje/nie wyświetla wartości sekretów ani pełnych danych PII (tylko liczniki).
- [ ] Klucze Odoo dalej wyłącznie z vaultu; T3 nie wprowadza plaintextu.
- [ ] Brak nowych endpointów wystawiających dane.

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review)
- [x] US-T1: reguła „nie zgaduj `<PERSON_x>`" w prompcie (`executor.py:14-35`); test `test_pii_confab_guard.py`.
- [x] US-T2: 'Price list'/'Audyt' nie maskowane; 'Henk Molenkamp' DALEJ maskowane; test `test_pii_allowlist.py`.
- [x] US-T3: connector ma `version_info`/`major` po connect; `fields_get` guard (fail loud); test `test_odoo_connector_version.py`.
- [x] US-T4: PREMIUM (opus-4.8) ≠ STANDARD (sonnet-4.6); CHEAP=haiku-4.5; `.env.example` + 3 testy; serwer zrestartowany.
- [x] US-T5: scope dziedziczy `project_id` w follow-upie; test `test_dispatcher_context.py`.
- [x] US-T6: stopka provenance budowana i doklejana (`executor.py:438`); test `test_provenance.py`.
- [x] Regresja: pełna pytest **358 passed, 2 skipped, 0 failed** (`-m 'not e2e'`).
- [x] **/qa LIVE (2026-06-25):** scenariusz RMO na żywej bazie Odoo 19 przez czat (sonnet-4.6). Tura 1: „RMO [zamaskowane]" (T1), nazwy zadań „Audtyt Hinduskich modułów"/„Price list possibility" widoczne (T2), 2 zadania, stopka „Odoo 19 · 1 rekordów · 1 zamaskowanych" (T3+T6). Tura 2 (follow-up „opisy?"): został w projekcie 136 → **2 zadania, NIE 2920** (T5), „Klient [zamaskowane]" w opisie. Wszystkie 6 zadań działają end-to-end.

### Close Checklist
- [ ] Zadania Sekcji B = ✅, status → `DONE`, `closed`.
- [ ] Lessons Learned (Sekcja F) + ewentualne instynkty.
- [ ] Zmergowane do `main`; wpis w roadmap.

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa po realizacji)

### Recon /arch (TRUST-01, 2026-06-25)
- **Diagnoza musi iść na ground-truth.** Odpowiedzi modelu (102 projekty, 2 zadania, 2920 łącznie) były liczbowo OK — błąd ujawniło dopiero porównanie NAZW z żywą bazą. Instynkt: weryfikuj nazwy własne osobno od agregatów.
- **PII + LLM = dwa źródła błędu naraz.** Przekłamane nazwy to (1) presidio over-masking + (2) model zgadujący maski. Rozdziel oba — naprawa jednego nie wystarczy.
- **Wykrywanie wersji już istniało, ale w złej ścieżce** (`recon.py`, nie connector czatu). Instynkt: zanim dodasz feature, sprawdź czy nie jest „osierocony" w innej warstwie (jak WIRE-01).

---

### Handoff
```
/arch (ten artefakt) — DO AKCEPTACJI USERA
   → /dev (T2 allow-lista → T1 confab-guard → T3 version-aware → T5 dispatcher → T4 ENV modeli → T6 provenance)
   → /sec (allow-lista nie osłabia PII osób; provenance bez wartości)
   → /qa (scenariusz RMO; PREMIUM≠STANDARD; fail-loud na polach; follow-up=2 nie 2920)
   → /gf-review (gate) → merge → roadmap
```

> Po TRUST-01: czat o Odoo jest wiarygodny — nazwy prawdziwe lub jawnie zamaskowane, zakres trzyma kontekst, zapytania respektują wersję, audyty idą mocniejszym modelem.
> SaaS/multi-tenant nadal POZA (ADR-008).
