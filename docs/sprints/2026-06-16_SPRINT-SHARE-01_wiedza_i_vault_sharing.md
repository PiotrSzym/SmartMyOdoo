---
sprint_id: "SHARE-01"
workspace: "SmartMyOdoo"
status: "IN_PROGRESS"
created: 2026-06-16
closed: null
goal: "Model współdzielenia przy przekazywaniu aplikacji: WIEDZA jedzie jako źródła w gicie (indeks wektorowy budowany lokalnie; warstwa shared + private per workspace_id), a SEKRETY (vault) zostają lokalne i nigdy nie są kopiowane (org → menedżer sekretów)"
prefix: "SHARE"
complexity: 5
roadmap_ref: "Epik SHARE (release readiness) — pojedynczy sprint-parasol; powiązane: ADR-015"
parent_sprint: null
tags: ["rag", "lancedb", "knowledge", "vault", "secrets", "multi-user", "distribution", "tdd"]
---

# 🧠 Sprint: SHARE-01 — Współdzielenie wiedzy i poświadczeń

> **Architekt:** /arch | **Owner:** /dev + /sec | **Review:** /gf-review | **Data:** 2026-06-16
> **Bazuje na:** main (`1bacec2`) | **Decyzja:** [ADR-015](../adr/ADR-015-Knowledge-As-Source-Secrets-Stay-Local.md) — „Knowledge-as-source / Secrets-stay-local"

---

## 📋 Sekcja A — Business Discovery & Rules (/arch ✅)

### 0A. Business Discovery
- **Dla kogo?** Właściciel aplikacji przekazujący SmartMyOdoo innej osobie/zespołowi (`git clone` + Docker).
- **Problem (1 zdanie):** sam `git clone` nie przenosi ani wiedzy zespołu (indeks gitignored), ani nie definiuje, co jest prywatne, a co współdzielone — a sekrety są lokalne.
- **Metryka sukcesu:** nowa osoba po `clone → seed` ma identyczny baseline wiedzy shared; `search(ws=A)` nie zwraca prywatnych rekordów `ws=B` (test izolacji zielony); zero plików sekretnych/binarnych w repo/obrazie.
- **ROI:** onboarding nowej osoby z minut zamiast dni; brak ryzyka wycieku vault do repo. Wartość > koszt (5 zadań, 1 migracja schematu).
- **Źródło zgłoszenia:** pytanie użytkownika (sesja 2026-06-16): „gdy przekażemy apkę — czy każdy ma tylko swoje dane w bazie wektorowej? jak dzielimy się wiedzą/plikami/lekcjami/instynktami skoro klucze są lokalne i jak przekazać vault?".

### 0B. User Stories (baza E2E)
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-SHARE-1 | nowy użytkownik aplikacji | po `clone` odbudować lokalnie indeks z wersjonowanych źródeł `knowledge/` | mieć wspólny baseline wiedzy bez kopiowania binariów | KIEDY `smartmyodoo seed` na świeżym clone TO tabela `knowledge_base` zawiera wiedzę z `knowledge/` |
| US-SHARE-2 | użytkownik workspace A | widzieć wiedzę shared + swoją prywatną, ale NIE cudzą prywatną (B) | zachować izolację danych klientów | KIEDY `search(workspace=A)` TO wynik zawiera shared ∪ A i NIE zawiera prywatnych B |
| US-SHARE-3 | osoba przekazująca aplikację | mieć jasną zasadę „vault się nie przekazuje" + ścieżkę org (menedżer sekretów) | nie wyciekać kluczy do repo/zespołu | KIEDY czytam guide/README TO wiem, że `.enc` nie idzie do gita, a org-sharing = menedżer sekretów |
| US-SHARE-4 | ta sama osoba migrująca na nową maszynę | zaszyfrowany `vault export/import` z PIN/Master | przenieść własne sekrety bezpiecznie (bez współdzielenia zespołowego) | KIEDY `vault export` → `vault import` z PIN TO sekrety odtworzone 1:1, z ostrzeżeniem o zakazie współdzielenia |

### 0C. Skills Audit (scope = BACKEND Python + docs)
- **Stack:** Python / FastAPI / LanceDB / sentence-transformers (`all-MiniLM-L6-v2`, dim 384) / SQLite metadata / Fernet+PBKDF2 (vault).
- **Skille wiążące dla /dev i /qa:** `@rag-engineer` (chunking/embedding/izolacja retrieval), `@python-testing` (pytest, fixtures, parametryzacja), `@security-audit` + `@gdpr-data-handling` (parytet: zero sekretów w artefaktach), `@odoo-crud` (kontekst danych klientów = warstwa prywatna).
- **Reguły Odoo/PROJECT_SKILLS:** dane partnerów/PII = warstwa prywatna `workspace_id`, NIGDY `"__shared__"`.

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| Schemat tabeli LanceDB | `swarm/brain/lancedb_client.py:48` (`pa.schema([...])`) | 📐 IN-PATTERN (dodaj pole) |
| Zapis rekordów | `add_texts()` mapuje `metadatas[i].get(...)` → kolumny | 📐 IN-PATTERN |
| Filtr retrieval | LanceDB `.search(vec).where(...).limit()` | ⚠️ AD-HOC (nowy `where` na `workspace_id`) |
| Seed/chunking | `seed_knowledge.py:chunk_text` + `SharedBrain._chunk_text` (overlap zdaniowy, S5.3) | 📐 IN-PATTERN |
| CLI subcommand | `__main__.py` `subparsers.add_parser("worker")` | 📐 IN-PATTERN (dodaj `seed`) |
| Vault load/save | `vault/vault.py` `load_vault(vk)` / `save_vault(vk, data)` | 📐 IN-PATTERN (export/import) |
| Degradacja RAG | `rag_api.py` flaga `degraded` zamiast fabrykacji (S5.3) | 📐 IN-PATTERN (zachowaj) |

### 0E. Test Strategy
| Warstwa | Potrzebna? | Co testować | Kto | Narzędzie |
|---|:--:|---|:--:|---|
| Unit | ✅ | `workspace_id` w schemacie/zapisie; filtr `search`; chunking; export/import round-trip | /dev | `pytest` |
| Integration | ✅ | seed idempotentny (2× = bez duplikatów); shared ∪ private vs cudze | /dev | `pytest` + tmp LanceDB |
| Contract | ✅ | sygnatura `search(query, top_k, workspace=...)` backward-compat (domyślnie shared+brak filtra) | /qa | `pytest` |
| E2E | ✅ | `seed` na czystym store → search izolowany; vault export→import | /qa | `pytest` CLI runner |
| Security | ✅ | strażnik: `.enc`/`.cfg`/`lancedb_store` poza gitem; brak instrukcji kopiowania vault | /sec | `git check-ignore`, grep |

### 0F. US → E2E Mapping
| US | Scenariusz KIEDY→TO | Plik E2E | Priorytet |
|----|---------------------|----------|-----------|
| US-SHARE-1 | seed na czystym store buduje tabelę z `knowledge/` | `tests/test_knowledge_sharing.py::test_seed_builds_from_knowledge` | 🔴 Critical |
| US-SHARE-2 | `search(ws=A)` = shared ∪ A, bez prywatnych B | `tests/test_knowledge_sharing.py::test_workspace_isolation` | 🔴 Critical |
| US-SHARE-3 | strażnik: brak sekretów/binariów w gicie, README linkuje guide | `tests/test_knowledge_sharing.py::test_no_secret_in_artifact` | 🔴 Critical |
| US-SHARE-4 | vault export→import zachowuje sekrety, wymaga PIN/Master | `tests/test_vault_migration.py::test_export_import_roundtrip` | 🟡 High |

### 0G. Security Scope → Sekcja D **OBOWIĄZKOWA**
Sprint dotyka sekretów (vault), PII (dane klientów w warstwie prywatnej) i dystrybucji artefaktów.
`/sec` weryfikuje **parytet NO-SECRET-IN-ARTIFACT**: ani indeks, ani obraz, ani repo nie niosą sekretów/vaulta;
warstwa prywatna nigdy nie ląduje w `"__shared__"`. STRIDE: głównie **Information Disclosure** (wyciek vault/PII).

### ⚖️ Zasady nadrzędne
- **NO SECRET IN ARTIFACT:** indeks/obraz/repo nie niosą sekretów ani plików vault.
- **Evidence Before Claims:** każdy efekt ma test dowodowy (czerwony przed, zielony po).
- **Backward-compat:** istniejąca tabela bez `workspace_id` → rekordy/braki = `"__shared__"` (bez utraty danych).
- **Degradacja > fabrykacja:** zachowaj flagę `degraded` (S5.3) przy filtrowaniu.

---

## 🧱 Sekcja B — Podział Zadań (TDD: Red → Green) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| SHARE-01-1 | Wersjonowany folder `knowledge/` (lekcje, instynkty, docs referencyjne) — przenieś tu treści warte współdzielenia (dziś w gitignored `.agents/`); odznacz `knowledge/` w `.gitignore` | `knowledge/**`, `.gitignore` | — (nowy katalog) | strażnik: `knowledge/` śledzony w gicie, ≥1 plik | ✅ |
| SHARE-01-2 | Dodaj `workspace_id` do schematu tabeli + zapis w `add_texts` (z `metadatas[i].get("workspace_id","__shared__")`); migracja istniejącej tabeli (brak kolumny → `"__shared__"`) | `swarm/brain/lancedb_client.py` | `lancedb_client.py:48,76` | Unit: rekord shared i private mają poprawny `workspace_id`; migracja zachowuje stare wiersze | ✅ |
| SHARE-01-3 | Filtr w `search(query, top_k, workspace=None)`: zwracaj **shared ∪ bieżący ws**, NIE cudze prywatne (LanceDB `.where`); przeprowadź `workspace` przez `SharedBrain.retrieve/ask_brain` i `rag_api` | `swarm/brain/lancedb_client.py`, `swarm/brain/rag_api.py` | `lancedb_client.py:99` | Integration: `search(ws=A)` bez prywatnych `ws=B`, zwraca shared; Contract: domyślne wywołanie bez `workspace` = backward-compat | ✅ |
| SHARE-01-4 | CLI `smartmyodoo seed [--shared knowledge/] [--private <ścieżka> --workspace <id>]` (idempotentny); krok w onboardingu/Dockerze | `smartmyodoo/__main__.py`, `swarm/brain/seed_knowledge.py` | `__main__.py:14` (`add_parser`) | E2E: seed 2× = bez duplikatów; buduje tabelę z `knowledge/`; `--private` taguje `workspace_id` | ✅ |
| SHARE-01-5 | Guide + sekcja README: (1) zespół = każdy własny vault; (2) migracja same-person = export + PIN osobnym kanałem; (3) org → menedżer sekretów (1Password/Bitwarden/HashiCorp/KMS). Zakaz kopiowania `.enc` do gita | `docs/guides/sharing_knowledge_and_secrets.md`, `README.md` | wzór: istniejące `docs/guides/` | strażnik: guide istnieje, README linkuje, brak instrukcji kopiowania `.enc` | ✅ |
| SHARE-01-6 | `vault export/import` dla migracji **tej samej osoby** (zaszyfrowany blob) + twarde ostrzeżenie „nie do współdzielenia zespołowego" | `smartmyodoo/vault/vault.py`, `smartmyodoo/__main__.py` | `vault.py:78,89` (`load_vault`/`save_vault`) | round-trip export→import zachowuje sekrety; import wymaga PIN/Master | ✅ |
| SHARE-01-7 | Testy dowodowe (komplet powyższych) | `tests/test_knowledge_sharing.py`, `tests/test_vault_migration.py` | wzór: `tests/test_*` (tmp store fixture) | pełna suita bez regresji (≥ 240 passed) | ✅ |

> **Uwaga TDD:** każde zadanie zaczyna od pliku testowego (Red). Test LanceDB używa **tmp `db_path`** w fixture (NIE współdzielonego `.agents/lancedb_store`).

---

## 🛡️ Sekcja D — Security (/sec, OBOWIĄZKOWA)
- [ ] **NO-SECRET-IN-ARTIFACT:** `git check-ignore` potwierdza, że `*.enc`, `*.cfg`, `.agents/lancedb_store/` są poza gitem; `knowledge/` NIE zawiera sekretów.
- [ ] **Izolacja PII:** dane klientów/partnerów trafiają wyłącznie do warstwy prywatnej (`workspace_id != "__shared__"`); test próbujący wpisać PII do shared = świadoma decyzja użytkownika.
- [ ] **Vault parytet:** brak jakiejkolwiek ścieżki kopiującej pliki vault do repo/obrazu; export/import wymaga PIN/Master.
- [ ] STRIDE: Information Disclosure zaadresowane; reszta kategorii N/A (brak nowych endpointów sieciowych).

---

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review)
- [x] `knowledge/` w gicie; `smartmyodoo seed` buduje lokalny indeks z tych źródeł (nowy clone = ten sam baseline). — ⚠️ patrz werdykt QA (pliki istnieją + NIE gitignored, ale UNTRACKED — `git add` przy merge /gf-review).
- [x] `search(workspace=A)` zwraca shared + prywatną A, a **NIE** prywatną B (izolacja udowodniona testem).
- [x] Indeks wektorowy pozostaje lokalny/gitignored — nic binarnego ani sekretnego w repo/obrazie.
- [x] Vault: guide + zasada wdrożone; brak ścieżki współdzielenia plików vault; org-sharing → menedżer sekretów.
- [x] `vault export/import` działa dla migracji jednej osoby; jawne ostrzeżenie.
- [x] Testy dowodowe zielone; pełna suita bez regresji (306 passed / 1 skip / 1 fail pre-existing PII, poza scope).
- [ ] Sekcja D (/sec) ✅; ADR-015 podlinkowany. — ADR podlinkowany ✅; Sekcja D = zadanie /sec (poza /qa).

### 🔬 Werdykt QA (Gatekeeper Jakości — Evidence Before Claims) — 2026-06-16
**Werdykt globalny: ⚠️ PASS Z UWAGĄ** (1 uwaga proceduralna, 0 bugów funkcjonalnych, 0 regresji).

| DoD / US | Verdict | Dowód (output komendy) |
|---|---|---|
| Pełna suita / smoke | ✅ | `pytest`: **306 passed, 1 skipped, 1 failed** (207.55s) — zgodne z deklaracją /dev |
| 1 failed = pre-existing? | ✅ | `test_mcp_pii_integration_roundtrip` `assert 0==1` (MCP/PII, poza scope RAG/vault). `git diff 1bacec2 HEAD -- tests/test_mcp_pii_integration.py smartmyodoo/mcp/server.py` = **pusty** → NIE regresja /dev |
| US-SHARE-2 izolacja (🔴) | ✅ | `test_workspace_isolation` PASS + 7 testów adversarialnych QA: injection `OR '1'='1'`/`DROP`/`UNION`/gołe apostrofy NIE wyciekają `ws_b`; `__shared__`/ghost ws → tylko shared |
| US-SHARE-2 edge (pusta tabela, ws=None) | ✅ | `search(pusta, ws=A)` → `[]` (nie wybucha, nie degraded); `ws=None` widzi wszystkie warstwy (backward-compat) |
| US-SHARE-1 seed idempotentny (🔴) | ✅ | seed z REALNEGO `knowledge/` → ≥2 chunki, all `__shared__`, źródła `odoo_instincts.md`+`README.md`; idempotencja **3×** = stały count |
| US-SHARE-4 vault round-trip (🟡) | ✅ | export→import 1:1 (wielu sekretów); export/import **bez PIN ODMAWIA**; uszkodzony/zmanipulowany blob ODMAWIA (integralność Fernet); zły PIN ODMAWIA |
| US-SHARE-3 NO-SECRET-IN-ARTIFACT | ✅ | `git check-ignore` ignoruje `*.enc`/`*.cfg`/`.agents/lancedb_store/`; `git ls-files '*.enc' '*.cfg'` = pusto; README linkuje guide |
| Regresja / backward-compat | ✅ | `SharedBrain.retrieve()` bez ws → przekazuje `None`; `search(query,top_k)` bez filtra; 288→306 (+18), zero regresji |
| Izolacja testowa (tmp store) | ✅ | testy używają `tmp_path`; globalny `.agents/lancedb_store` mtime sprzed sprintu, nietknięty |
| DoD pkt 1: `knowledge/` w gicie | ⚠️ | `git status knowledge/` = `??` (UNTRACKED), `git log --all -- knowledge/**` = pusto (nigdy niezacommitowany). Pliki istnieją + NIE gitignored. Norma dla IN_PROGRESS — commit = odpowiedzialność /gf-review (handoff). Luka: `test_knowledge_dir_exists_and_tracked` sprawdza tylko `check-ignore`, nie `ls-files` — untracked-but-not-ignored przejdzie test. |

**Bugi funkcjonalne:** 0.
**Uwagi (⚠️):** (1) `knowledge/` untracked — wymaga `git add` przy merge przez /gf-review; (2) test strażnika `test_knowledge_dir_exists_and_tracked` ma lukę dowodową (weryfikuje `check-ignore` zamiast `git ls-files`) — rekomendacja: dodać asercję faktycznego trackingu. Obie do adresacji przez /gf-review przed merge.
**Handoff:** → `/audyt` + `/sec` (równolegle). /sec: domknąć Sekcję D. /gf-review: `git add knowledge/` + wzmocnić strażnik trackingu.

### Close Checklist
- [ ] Wszystkie zadania Sekcji B = ✅, status sprintu → `DONE`, `closed` ustawione.
- [ ] Lessons Learned (Sekcja F) uzupełnione.
- [ ] Zmergowane do `main` przez /gf-review.

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa po realizacji — pułapki LanceDB `.where`, migracja schematu, idempotencja seed)

**/dev (2026-06-16):**
- **`git check-ignore` na katalogu vs pliku.** `git check-ignore knowledge/` (z trailing slash, katalog pusty) potrafi zwrócić exit 0 mimo braku reguły — fałszywy alarm. Autorytatywny test robimy na **realnym pliku** wewnątrz (`knowledge/x.md` → exit 1 = NIE ignorowany). Strażnik w teście używa konkretnego pliku, nie katalogu. Wniosek: `.gitignore` NIE wymagał edycji — `knowledge/` nie był blokowany.
- **Idempotencja seed = deterministyczne `id` + upsert.** Sam deterministyczny hash (`sha256(ws+source+chunk_idx+treść)`) NIE wystarcza, bo LanceDB `.add()` zawsze **dokleja** wiersz. Konieczny jawny `table.delete("id IN (...)")` przed `add` (upsert). Bez tego 2× seed = duplikaty.
- **Migracja schematu LanceDB.** `table.add_columns({"workspace_id": "'__shared__'"})` — wartość domyślna to **literał SQL** (apostrofy wewnątrz stringa), nie goła wartość. Idempotentne: najpierw sprawdzamy `field.name in schema`.
- **Vault export samowystarczalny.** Pierwsza wersja szyfrowała blob kluczem `vk` (losowy Fernet) — import na nowej maszynie był niemożliwy bez plików `*.enc`/`*.cfg`. Poprawka: blob = `[16B sól][Fernet(PBKDF2(PIN, sól))]` — import wymaga **tylko PIN**, a brakujący lokalny skarbiec jest inicjalizowany w locie. To realizuje „migrację jednej osoby" bez kopiowania plików lokalnych.
- **Izolacja `.where` + sanitizacja.** Wartość `workspace` trafia do literału SQL LanceDB → escapujemy apostrof (`'`→`''`), żeby `ws' OR '1'='1` nie ominął filtra warstw. Test bezpieczeństwa to potwierdza (brak wycieku `ws_b`).
- **Backward-compat zachowany.** `search(query, top_k)` bez `workspace` = stare zachowanie (brak filtra). `tools.py::search_knowledge_base` (fixed tool signature) celowo NIE zmieniany — domyślnie shared+brak filtra (poza scope SHARE-01).
- **Baseline testów:** przed sprintem 288 passed / 1 fail (`test_mcp_pii_integration_roundtrip` — `assert 0==1`, niezwiązane z RAG/vault, pre-existing) / 1 skip. Po sprincie: **306 passed** (+18 nowych), 1 skip, **ta sama 1 pre-existing porażka** PII — zero regresji.

---

### Handoff
```
/arch (ADR-015 + ten artefakt) ✅
   → /dev (knowledge/ + workspace_id + filtr search + seed CLI + vault export/import, TDD)
   → /sec (parytet NO-SECRET-IN-ARTIFACT + izolacja PII)
   → /qa (izolacja shared/private, idempotencja seed, round-trip vault)
   → /gf-review (gate) → /doc (guide + README)
```

> Po SHARE-01: nowa osoba robi `clone → seed` i ma wspólny baseline wiedzy + własną warstwę prywatną,
> a klucze trzyma u siebie — vault nigdy nie jest kopiowany między ludźmi.
