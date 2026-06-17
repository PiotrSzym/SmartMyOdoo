---
sprint_id: "SHARE-02"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-17
closed: 2026-06-17
goal: "Domknięcie follow-upów po SHARE-01: vault import nie osłabia Master Password po cichu (Master=PIN), CLI import przyjmuje --master, guard-rail przeciw PII w warstwie __shared__, oraz naprawa/izolacja pre-existing czerwonego testu MCP-PII"
prefix: "SHARE"
complexity: 3
roadmap_ref: "Follow-upy /sec z SHARE-01 (3× Low) + pre-existing red test_mcp_pii; powiązane: ADR-015"
parent_sprint: "SHARE-01 (2026-06-16_SPRINT-SHARE-01_wiedza_i_vault_sharing.md)"
tags: ["vault", "secrets", "pii", "hardening", "test-fixing", "tdd"]
---

# 🧱 Sprint: SHARE-02 — Hardening / domknięcie follow-upów

> **Architekt:** /arch | **Owner:** /dev + /sec | **Review:** /gf-review | **Data:** 2026-06-17
> **Bazuje na:** main (`f17e87c`) | **Część:** follow-upy [SHARE-01](2026-06-16_SPRINT-SHARE-01_wiedza_i_vault_sharing.md), [ADR-015](../adr/ADR-015-Knowledge-As-Source-Secrets-Stay-Local.md)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch ✅)

### 0A. Business Discovery
- **Dla kogo?** Użytkownik vaulta (migracja na nową maszynę) + zespół deweloperski (czysta, zielona suita).
- **Problem (1 zdanie):** SHARE-01 zostawił 3 drobne luki bezpieczeństwa/UX (Low) i 1 pre-existing czerwony test — dług, który psuje „zielony baseline" i osłabia recovery vaulta.
- **Metryka sukcesu:** pełna suita **0 failed** (dziś 1 failed); `vault import` bez `--master` NIE ustawia po cichu słabego Mastera; PII trafiające do `__shared__` jest sygnalizowane.
- **ROI:** mały koszt (4 zadania, brak nowych zależności), realne domknięcie długu bezpieczeństwa + odzyskanie wiarygodności suity (zielony = naprawdę zielony).
- **Źródło:** findings /sec ze SHARE-01 (F-1, F-2, F-3) + nota /qa o pre-existing `test_mcp_pii_integration_roundtrip`.

### 0B. User Stories (baza E2E)
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-S2-1 | osoba migrująca vault na nową maszynę | by `import` nie ustawiał po cichu `Master = PIN` (niska entropia) | nie osłabić ścieżki odzyskiwania Masterem | KIEDY `import` bez `--master` na czystej maszynie TO Master NIE jest milcząco = PIN — jest jawne ostrzeżenie + instrukcja ustawienia silnego Mastera |
| US-S2-2 | użytkownik CLI | podać własny Master przy imporcie (`--master`) | zachować silny Master od razu | KIEDY `vault import plik --master <silny>` TO recovery-init używa podanego Mastera, nie PIN-u |
| US-S2-3 | właściciel danych | ostrzeżenie, gdy seed do warstwy **shared** wygląda na PII (NIP/email/osoba) | nie wyciekać danych klientów do wspólnej warstwy | KIEDY `seed --shared` z treścią zawierającą PII TO głośne ostrzeżenie (i pominięcie/`--allow-pii-shared`), bo shared = współdzielone |
| US-S2-4 | deweloper | zieloną, wiarygodną suitę | „308 passed" znaczyło „wszystko działa", nie „1 znany czerwony" | KIEDY `pytest` TO 0 failed — test MCP-PII albo naprawiony (realny bug), albo warunkowo pominięty (brak zależności Presidio), z jawnym uzasadnieniem |

### 0C. Skills Audit (scope = BACKEND Python)
- **Skille wiążące:** `@security-audit` (model Mastera, entropia), `@gdpr-data-handling` (rozpoznanie PII), `@python-testing` + `@test-fixing` (root-cause czerwonego testu, `importorskip`), `@systematic-debugging` (T4 evidence-first).
- **Reguła:** żadnych nowych zależności (PII guard używa istniejącego recognizera/regex, nie nowego pakietu).

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| `import_vault` recovery-init | `vault/vault.py:180-182` (`recovery_master = master if ... else pin`) | ⚠️ AD-HOC (fix: ostrzeżenie/jawny master) |
| CLI argparse subcommand z flagą | `vault/vault.py:main()` export/import parser + `add_argument` | 📐 IN-PATTERN (dodaj `--master`) |
| Warunkowy skip testu (brak zależności) | `tests/test_knowledge_sharing.py:20` (`pytest.importorskip`) | 📐 IN-PATTERN (zastosuj w T4 jeśli to env) |
| Rozpoznanie PII | `security/pii/` (kanon, Presidio) / istniejący recognizer NIP | 📐 IN-PATTERN (re-use, nie nowy pakiet) |
| `_safe_print` / ostrzeżenia CLI | `vault/vault.py:106` (`_safe_print`) | 📐 IN-PATTERN (użyj do ostrzeżeń) |

### 0E. Test Strategy
| Warstwa | Potrzebna? | Co testować | Kto | Narzędzie |
|---|:--:|---|:--:|---|
| Unit | ✅ | import bez `--master` → ostrzeżenie + Master≠cichy-PIN; import z `--master` → użyty; PII recognizer na sample | /dev | `pytest` |
| Integration | ✅ | CLI `import --master` end-to-end (round-trip z silnym Masterem); `seed --shared` z PII → ostrzeżenie/pominięcie | /dev | `pytest` + tmp vault/store |
| Regresja | ✅ | round-trip vault (SHARE-01) nadal zielony; pełna suita **0 failed** | /qa | `pytest` |

### 0F. US → E2E Mapping
| US | Scenariusz | Plik testu | Priorytet |
|----|------------|------------|-----------|
| US-S2-1 | import bez `--master` → ostrzeżenie, brak cichego Master=PIN | `tests/test_vault_migration.py::test_import_warns_on_master_equals_pin` | 🔴 |
| US-S2-2 | `import --master <silny>` → recovery-init z Masterem | `tests/test_vault_migration.py::test_import_with_explicit_master` | 🔴 |
| US-S2-3 | `seed --shared` z PII → ostrzeżenie / pominięcie | `tests/test_knowledge_sharing.py::test_pii_guard_on_shared_seed` | 🟡 |
| US-S2-4 | suita 0 failed (test MCP-PII zielony lub świadomie skip) | `tests/test_mcp_pii_integration.py` | 🔴 |

### 0G. Security Scope → Sekcja D **OBOWIĄZKOWA**
Dotyka modelu Mastera (entropia recovery) i PII. `/sec` weryfikuje: brak cichego osłabienia Mastera; guard-rail PII faktycznie wykrywa NIP/email/osobę; brak nowej powierzchni ataku. STRIDE: Information Disclosure + Elevation (słaby Master).

### ⚖️ Zasady
- **NO SILENT WEAKENING:** żadne osłabienie sekretu nie może być ciche — zawsze głośne ostrzeżenie + ścieżka naprawy.
- **Evidence Before Claims:** T4 zaczyna od ROOT-CAUSE (dlaczego czerwony), nie od zgadywania fixa.
- **NO NEW DEPS:** guard PII re-używa istniejącego kodu/regex.
- **Backward-compat:** `import_vault(pin, master=None)` sygnatura zachowana; `--master` opcjonalny.

---

## 🧱 Sekcja B — Podział Zadań (TDD: Red → Green) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| S2-1 | `import_vault`: gdy recovery-init i brak `master` → NIE ustawiaj po cichu `Master=PIN`; wypisz głośne ostrzeżenie (`_safe_print`) „Master = PIN (niska entropia), ustaw silny Master" + (preferowane) ustaw flagę/log. Jeśli `master` podany → użyj go. | `smartmyodoo/vault/vault.py` | `vault.py:180-182,106` | Unit: import bez master → ostrzeżenie obecne; z master → recovery-init z master | ✅ |
| S2-2 | CLI `vault import`: dodaj `--master` (argparse), przekaż do `import_vault`. Prompt interaktywny o Master gdy czysta maszyna i brak flagi (opcjonalnie). | `smartmyodoo/vault/vault.py` (`main()`) | `vault.py:main()` import parser | Integration: `import --master <silny>` → round-trip, Master działa | ✅ |
| S2-3 | Guard-rail PII przy `seed --shared`: jeśli treść chunku wygląda na PII (NIP/email/os.) → **głośne ostrzeżenie** + pomiń wpis do shared, chyba że `--allow-pii-shared`. Re-use recognizer z `security/pii/` lub prosty regex (NIP/email). | `smartmyodoo/swarm/brain/seed_knowledge.py`, `smartmyodoo/__main__.py` | `security/pii/`, `__main__.py` seed parser | Unit: sample z NIP/email → ostrzeżenie/pominięcie; czysty tekst → przechodzi | ✅ |
| S2-4 | **INVESTIGATE-FIRST** `test_mcp_pii_integration_roundtrip`: ustal root-cause (mock `search_count` zwraca MagicMock? brak Presidio/spacy? wyjątek łapany w `server.py:192`). Następnie: realny bug → fix; brak zależności → `pytest.importorskip`/skip warunkowy z uzasadnieniem. Cel: suita **0 failed**. | `tests/test_mcp_pii_integration.py`, ewent. `smartmyodoo/mcp/server.py` | `test_knowledge_sharing.py:20` (importorskip) | suita 0 failed; jeśli skip — jawny powód | ✅ |
| S2-5 | Testy dowodowe (komplet) + aktualizacja Sekcji C/F | `tests/test_vault_migration.py`, `tests/test_knowledge_sharing.py` | wzór: istniejące testy SHARE-01 | pełna suita bez regresji | ✅ |

> **TDD:** każde zadanie zaczyna od czerwonego testu. T4 = najpierw diagnoza (log/repro), potem decyzja fix vs skip — bez zgadywania.

---

## 🧩 Sekcja B½ — Pattern/Architecture Audit (/audyt)
> Mikro-sprint hardeningowy — pełny `/audyt` **N/A** (brak nowych wzorców/modułów; complexity 3).
> Spójność architektoniczną zweryfikował `/gf-review` (fresh-eyes, FAZA 3): layer separation ✅
> (guard PII w warstwie seed, nie przecieka do domeny), SOLID/DRY/KISS ✅ (`detect_pii` mała/czysta,
> `_safe_print` re-used), bounded contexts vault/knowledge/mcp rozdzielone, zero nowych zależności.

---

## 🛡️ Sekcja D — Security (/sec, OBOWIĄZKOWA)
- [x] **Brak cichego osłabienia Mastera:** import bez `--master` wypisuje głośne ostrzeżenie (`_safe_print`, cp1250-safe) „Master = PIN (niska entropia)" + instrukcję naprawy. Test: `test_import_warns_on_master_equals_pin`. /dev ✅ — czeka na weryfikację /sec.
- [x] **Guard PII shared:** lekki regex `detect_pii` wykrywa email + NIP (10 cyfr `1234563218` oraz z myślnikami `123-456-32-18`). Tylko warstwa `__shared__` jest filtrowana; prywatne PII przechodzi. Testy: `test_pii_guard_detects_nip_and_email`, `test_pii_guard_on_shared_seed`. ⚠️ Uwaga dla /sec: NIE wykrywa „imię+nazwisko" (osoba) — to wymaga Presidio/spacy (ciężkie, NO-NEW-DEPS); świadome zawężenie do NIP/email, decyzja /arch.
- [x] **Brak nowej powierzchni ataku / nowych zależności.** `detect_pii` = stdlib `re`; bandit bez nowych findings (2 Low pre-existing w `run_wrapped_command`).
- [x] STRIDE: Elevation (słaby Master) + Information Disclosure (PII w shared) zaadresowane (no-silent-weakening + pominięcie PII).
- [x] **/sec: APPROVE** (2026-06-17) — F-1/F-2/F-3 ze SHARE-01 ZAMKNIĘTE kodem + testami; zawężenie PII do NIP+email akceptowalne (Low residual, ADR-015 + NO-NEW-DEPS); guard nie wycieka PII do logów (loguje tylko nazwę pliku + nr chunku); 0 nowych deps, 0 sekretów w artefakcie.

---

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review)
- [x] `vault import` bez `--master` → głośne ostrzeżenie, brak cichego Master=PIN (`test_import_warns_on_master_equals_pin`).
- [x] `vault import --master <silny>` → recovery-init używa podanego Mastera (`test_import_with_explicit_master`: Master odblokowuje vk, PIN≠Master).
- [x] `seed --shared` z PII → ostrzeżenie/pominięcie; `--allow-pii-shared` świadomie pozwala (`test_pii_guard_on_shared_seed`).
- [x] **Pełna suita 0 failed** — `313 passed, 1 skipped, 2 deselected` (baseline: 308 passed / 1 failed). Test MCP-PII: realny bug w MOCKU (nie env) — fix opisany w Sekcji F.
- [x] **/qa: brak regresji SHARE-01** — round-trip vault / workspace-isolation / seed-idempotency / search-backward-compat / private-tagging / legacy-migration = 7/7 PASSED (osobny przebieg). Backward-compat sygnatur potwierdzony: `import_vault(in_path, pin=None, master=None)` i `seed_knowledge_base(docs_dir, workspace_id=None, allow_pii_shared=False)` — wszystkie nowe parametry opcjonalne, stare wywołania bindują.
- [ ] Sekcja D (/sec) ✅ — czeka na /sec.

### 🔬 Verdykt /qa (Evidence-Based) — 2026-06-17, baza `f17e87c`
| DoD / US | Verdykt | Dowód (output) |
|---|:--:|---|
| Pełna suita 0 failed | ✅ | `313 passed, 1 skipped, 2 deselected, 0 failed in 186.92s`. 1 skip = `importorskip` (RAG offline guard), 2 deselected = `-m 'not e2e'` (Playwright `test_chat_e2e`/`test_project_tab_e2e`) — NIE ukryty stary red. MCP-PII test JEST kolekcjonowany i PASSED. |
| US-S2-1 no-silent-weakening | ✅ | `test_import_warns_on_master_equals_pin` PASS; CLI/integration: import bez `--master` → głośne `[!] OSTRZEŻENIE ... Master ... TYMCZASOWO = PIN (niska entropia)`, import nadal odtwarza dane (nie blokuje). |
| US-S2-2 `--master` | ✅ | `test_import_with_explicit_master` PASS: `get_vault_key_from_master(silny)` odblokowuje vk, `get_vault_key_from_master("1234")`→ValueError (Master≠PIN), brak ostrzeżenia o entropii. |
| US-S2-3 guard PII | ✅⚠️ | E2E CLI: `seed --shared` → `pii.md 0/1 chunków` POMINIĘTY + głośne `[!] OSTRZEŻENIE PII`; `--allow-pii-shared` → `1/1`, 2 chunki dodane; private (`workspace_id`) → PII NIE pomijane (test `test_pii_guard_on_shared_seed` PASS). NIP z myślnikami `123-456-32-18` łapany przez pełny CLI. ⚠️ Znana, świadoma over-aggressiveness — patrz niżej. |
| US-S2-4 mock-only fix | ✅ | `git diff smartmyodoo/mcp/server.py` = PUSTY (kod produkcyjny nietknięty). Fix wyłącznie w teście: `mock_client.search_count.return_value = 1`. `test_mcp_pii_integration_roundtrip` PASSED. |

**⚠️ Znane ograniczenie (nie blokuje — świadoma decyzja /arch, NO-NEW-DEPS):** `detect_pii` flaguje jako PII KAŻDY izolowany ciąg 10 cyfr. Dowód (atak /qa, 18 prób, 0 niezgodności z regexem): `5012345678` (telefon), `1000000042` (ID zamówienia), `1700000000` (epoch ts), `1234567890` (kwota), `raport_v2@2x.png` (nazwa pliku) → wszystkie `True`. Skutek: czysta wiedza zespołowa zawierająca dowolny 10-cyfrowy identyfikator/timestamp/kwotę bez separatorów zostanie POMINIĘTA w `__shared__` (z ostrzeżeniem i obejściem `--allow-pii-shared`). Stanowisko: zgodne z zasadą „lepiej pominąć niż wyciec"; brak false-NEGATIVE na realnym NIP/email. Rekomendacja na przyszłość: walidacja sumy kontrolnej NIP, by ograniczyć szum.

### Close Checklist
- [x] Wszystkie zadania Sekcji B = ✅ (statusy ⏳→✅).
- [x] Lessons Learned (Sekcja F) uzupełnione.
- [x] status → `DONE`, `closed` ustawione (/sec ✅ + /qa ✅ + /gf-review APPROVE).
- [x] Zmergowane do `main` (po review gate).

### 🏆 Verdykt /gf-review — 2026-06-17, baza `f17e87c`
**APPROVE (kod)** — 9/9 faz, zero 🔴. Zweryfikowane adversarialnie: no-silent-weakening Mastera szczelne; `--master` daje niezależny silny Master; fix mocka S2-4 nie maskuje buga produkcyjnego (`server.py` diff pusty, `int<int` poprawne). Warunki proceduralne domknięte **po review**: Sekcja B½ (N/A + ocena /gf-review) i Sekcja E (/doc) uzupełnione; **F1/F2 (false-positive 10-cyfr + NIP ze spacjami) NAPRAWIONE** — patrz L-S2-4.

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa — root-cause testu MCP-PII, wybór fix-vs-skip, model Mastera)

### L-S2-1 — Root-cause `test_mcp_pii_integration_roundtrip` (Evidence Before Claims)
- **Dowód (nie zgadywanie):** uruchomienie `pytest -s` ujawniło log z `server.py:193`:
  `Błąd w search_odoo_records ... '<' not supported between instances of 'int' and 'MagicMock'`.
- **Przyczyna:** to **bug w teście (niekompletny mock)**, NIE brak zależności. Presidio/spacy
  ładuje się poprawnie (anonimizował nawet `res.partner` → `<URL_1>rtner`). Test ustawiał
  `mock_client.search_read`, ale NIE `search_count`. W `server.py` `total = search_count(...)`
  zwracał `MagicMock`, a `if len(embed) < total:` rzucało `TypeError` → łapany w `server.py:192`
  → `{"error":...}` → `records=[]` → `assert len==1` padał na `0`.
- **Decyzja (fix, NIE skip):** poprawka w teście — `mock_client.search_count.return_value = 1`.
  Kod produkcyjny jest poprawny (`search_count` zwraca `int` w realu). `pytest.importorskip`
  byłby BŁĘDNY — Presidio jest dostępne, problem był deterministyczny i naprawialny. Dodany
  komentarz w teście tłumaczy, dlaczego mock musi odwzorować `int`.
- **Instynkt do error_registry:** *MagicMock-as-return na metodzie użytej w porównaniu/arytmetyce
  cicho psuje wynik przez wyjątek łapany w szerokim `except` — zawsze ustaw konkretne
  `return_value` dla każdej metody mocka, która wchodzi w `<`/`len`/arytmetykę.*

### L-S2-2 — NO SILENT WEAKENING (model Mastera przy imporcie)
- `import_vault` na czystej maszynie bez `--master` nadal robi recovery-init z `Master=PIN`
  (samowystarczalność migracji zachowana — nie blokujemy), ale TERAZ z głośnym `_safe_print`
  ostrzeżeniem o niskiej entropii + instrukcją. Z `--master <silny>` używamy go od razu, bez
  ostrzeżenia. Sygnatura `import_vault(pin, master=None)` zachowana (backward-compat).
- Ostrzeżenie idzie przez `_safe_print` (cp1250-safe) — lekcja z SHARE-01 Finding B: kontrola
  bezpieczeństwa nie może zniknąć w `UnicodeEncodeError` na konsoli Windows.

### L-S2-3 — Guard PII shared: lekki regex zamiast Presidio (NO NEW DEPS)
- Pełna warstwa PII (`security/pii/`, Presidio+spacy `pl_core_news_md`) jest ciężka i wymaga
  modelu — nieadekwatna do strażnika seedowania CLI. Użyto `detect_pii` (stdlib `re`):
  email + NIP (10 cyfr i z myślnikami). Świadome zawężenie: NIE wykrywa „osoby" (imię+nazwisko)
  — to wymaga NER. Filtr działa TYLKO dla `__shared__`; prywatne PII przechodzi (dane klienta
  w jego workspace są OK). `--allow-pii-shared` = świadomy override.

### L-S2-4 — Redukcja false-positive guarda PII (follow-up /qa+/gf-review, ten sam sprint)
- **Problem (znaleziony przez /qa, potwierdzony /gf-review):** pierwsza wersja `detect_pii`
  flagowała KAŻDY izolowany ciąg 10 cyfr (telefon/timestamp/kwota/ID) oraz nazwy plików retina
  (`raport@2x.png` — email-regex łapał `@2x.png`). Skutek: czysta wiedza zespołowa była
  pomijana w `__shared__`.
- **Fix (tani, NO-NEW-DEPS):** (1) **walidacja sumy kontrolnej NIP** (wagi `6,5,7,2,3,4,5,6,7`,
  mod 11) — losowy 10-cyfrowy ciąg nie przechodzi; (2) email-regex pomija asset-extensions
  (`png/svg/js/md/...`) i sufiks retina `@\d+x`; (3) bonus: NIP **ze spacjami** (`123 456 32 18`)
  teraz łapany (domknięty follow-up /sec F-S2-A). Testy: `test_pii_guard_no_false_positive_on_plain_numbers`
  + rozszerzony `test_pii_guard_detects_nip_and_email`.
- **Lekcja:** „lepiej pominąć niż wyciec" NIE musi znaczyć „zalej szumem" — tania walidacja
  domenowa (checksum) usuwa większość false-positive bez dodawania zależności ani NER.

### Sekcja E — Knowledge Map & Changelog (/doc)
- **Changelog:** wpis `[SHARE-02]` w `CHANGELOG.md` (Added/Fixed/Follow-up).
- **UI/panel:** brak zmian — sprint czysto CLI/backend (vault + seed guard). Centrum Dokumentacji
  (panel) nietknięte; sekcja „Współdzielenie & Przekazanie" ze SHARE-01 nadal aktualna.
- **Dług dokumentacyjny projektu (poza scope):** brak pliku `docs/blueprint/00_lessons_learned.md`
  (lekcje żyją w §F sprintów + ADR-014); instynkt L-S2-1 wart dopisania do `error_registry.md`.

### Handoff
```
/arch (ten artefakt) ✅
   → /dev (S2-1..S2-5, TDD; T4 investigate-first)
   → /sec (model Mastera + guard PII)
   → /qa (suita 0 failed, brak regresji SHARE-01)
   → /gf-review (gate) → /doc (changelog + ewent. panel)
```

> Po SHARE-02: zielony baseline jest wiarygodny (0 failed), recovery vaulta nie osłabia Mastera po cichu,
> a PII nie wpada przypadkiem do warstwy współdzielonej.
