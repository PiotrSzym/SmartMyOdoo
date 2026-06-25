---
sprint_id: "TRUST-04"
workspace: "SmartMyOdoo"
status: "IN_PROGRESS"
created: 2026-06-25
closed: null
goal: "Poprawnie rozpoznawać OSOBĘ w zapytaniach o dane Odoo (CRM/zadania) mimo że (a) połączenie idzie zwykle przez konto ADMINA (nie konkretną osobę) i (b) nazwiska są zamaskowane PII dla LLM. Rozwiązanie wg decyzji usera: (1) TOŻSAMOŚĆ OPERATORA per workspace — ustawiana raz, mapuje 'moje/przypisane do mnie'→uid; (2) ROZPOZNANIE OSOBY PO STRONIE SERWERA — gdy nazwiesz osobę, serwer (ma realne nazwy) szuka w res.users i przy wielu dopasowaniach pokazuje LISTĘ realnymi nazwami do wyboru. Do LLM trafia tylko uid + reguła, NIGDY nazwisko."
prefix: "TRUST"
complexity: 7
roadmap_ref: "/qa LIVE 2026-06-25 (CRM): połączenie=admin≠osoba; PII maskuje nazwiska. Korekta założenia TRUST-04. Po TRUST-03."
parent_sprint: "TRUST-03"
tags: ["operator-identity", "entity-resolution", "server-side", "pii", "crm", "trust", "adr-008"]
---

# 🧱 Sprint: TRUST-04 — Tożsamość operatora + rozpoznanie osoby po stronie serwera

> **Architekt:** /arch | **Data:** 2026-06-25 | **ADR:** ADR-008, ADR-011 (PII)
> **KOREKTA:** pierwotne założenie (zalogowany user = osoba pytająca) BŁĘDNE — połączenie idzie zwykle przez ADMINA. Sprint przepisany wg decyzji usera (2026-06-25).

## 0A. Problem (1 zdanie)
„ile szans dla piotr sz / przypisanych do mnie" → model wybrał złego Piotra (id=114, 0 szans) zamiast właściwego (id=42, 7 szans), bo: (a) połączenie to **admin**, nie wie kim jest „ja"; (b) **nazwiska zamaskowane PII** → LLM nie dopasuje „sz"→„Szymełyniec".

## 0B. Fakty (żywa baza Odoo 19)
- Piotr Szymełyniec uid=42 → **7 szans**; Piotr Hrebieniuk id=114 (wybrany przez model) → 0; **5 różnych Piotrów**.
- Połączenie API zwykle = konto admin/serwisowe (decyzja/uwaga usera) → „ja" nieokreślone.
- Nazwiska maskowane w kontekście LLM (PERSON_x/[zamaskowane]).

## ⚖️ Decyzje (/arch — wg wyboru usera 2026-06-25)
- **D1 — Tożsamość OPERATORA ≠ tożsamość POŁĄCZENIA.** Operator (człowiek) deklarowany osobno, per workspace.
- **D2 — Operator per workspace, ustawiany RAZ, persystentny.** „moje/przypisane do mnie/dla mnie" → `user_id=<operator_uid>`. Gdy nieustawiony → przy pierwszym „moje" system PYTA „kim jesteś?" (raz), rozwiązuje nazwisko→uid serwerowo, zapisuje.
- **D3 — Rozpoznanie osoby PO STRONIE SERWERA.** Gdy wiadomość nazywa osobę, serwer szuka w `res.users` (REALNE nazwy, nie zamaskowane). 1 dopasowanie → użyj uid; wiele → pokaż userowi LISTĘ pełnymi nazwami (lokalnie, ma dostęp) do wyboru.
- **D4 — Do LLM tylko `uid` + reguła filtra.** Nazwisko NIGDY nie opuszcza serwera (Sekcja D). `uid` to nie PII.
- **D5 — Admin domyślnie widzi wszystko.** Brak nazwanej osoby + brak „moje" → bez filtra user_id (raport ogólny).
- **D6 — Persystencja operatora:** kolumna w tabeli `workspaces` (`operator_uid`, `operator_name`) — wymaga migracji (ADR-010). [OTWARTE: alternatywa = wpis w vaultcie. Do potwierdzenia w /dev.]

## 0C. User Stories
| ID | JAKO | CHCĘ | KIEDY → TO |
|----|------|------|-----------|
| US-T1 | konsultant | by „moje/przypisane do mnie" działało | KIEDY operator ustawiony TO filtr `user_id=<operator_uid>` |
| US-T2 | konsultant | by ustawić „kim jestem" raz | KIEDY pierwsze „moje" bez operatora TO system pyta i zapisuje (per workspace) |
| US-T3 | konsultant | by „dla [nazwisko]" trafiało we właściwą osobę | KIEDY nazwę osobę TO serwer rozwiązuje res.users; >1 dopasowanie → lista realnymi nazwami do wyboru |
| US-T4 | bezpieczeństwo | by nazwisko nie szło do chmury | KIEDY rozpoznaję osobę TO do LLM idzie tylko `uid` + reguła |

## 🧱 Sekcja B — Zadania (/dev)
| # | Zadanie | Pliki | Testy | Status |
|---|---------|-------|-------|--------|
| T1 | **Serwerowy resolver osób** — `resolve_person_records(name_query)` (res.users ilike po REALNYCH nazwach → {uid REALNE, name ZAMASKOWANE}); narzędzie `resolve_person` + reguła w prompcie + podpięcie do 11 skili. | `mcp/server.py`, `swarm/tools.py`, `swarm/executor.py` (`PEOPLE_RESOLVE_RULE`), 11×`skills/*.py` | `test_resolve_person.py` (4) | ✅ DONE (regresja 391/0; LIVE: „dla piotr sz" → **7 szans** zamiast 0) |
| T2 | **Tożsamość operatora per workspace** — persystencja (D6: kolumna w `workspaces` + migracja) + ustawianie (flow „kim jesteś?" przy 1. „moje"). | `core/models.py`, migracja, `api_routers/workspaces.py` lub chat | set/get operatora; brak → trigger pytania | ⬜ TODO |
| T3 | **Detekcja referencji + wstrzyknięcie reguły** (serwerowo): „moje/mnie"→operator_uid; nazwa→resolver; >1 → lista do wyboru. Do LLM TYLKO `uid` + reguła (bez nazwiska). | `executor.py`, `api_routers/chat.py` | self→operator; „piotr sz"→1 uid; „piotr"→pick; blok bez nazwiska | ⬜ TODO |
| T4 | Regresja + /qa LIVE | testy | „przypisane do mnie"→uid=42→7 szans; „dla piotr”→lista 5 | ⬜ TODO |

## 🛡️ Sekcja D — Security
- [ ] Nazwiska osób (w tym lista wyboru) NIE trafiają do LLM — tylko `uid`. Lista pełnych nazw renderowana LOKALNIE userowi (ma dostęp).
- [ ] `operator_uid`/`uid` to identyfikatory techniczne (nie PII).
- [ ] Migracja D6 zgodna z ADR-010 (test downgrade).

## 🔬 Sekcja C — DoD
- [ ] US-T1/T3: „przypisane do mnie"→uid=42→7 szans; „dla piotr sz"→Szymełyniec (LIVE).
- [ ] US-T2: pierwsze „moje" bez operatora → pyta i zapisuje; kolejne już nie.
- [ ] US-T4: blok do LLM zawiera uid, NIE zawiera nazwiska (test).
- [ ] Regresja 0 failed (+ downgrade migracji).

> Po TRUST-04: „ja/moje" = ustawiony operator (nie admin połączenia); „dla [osoby]" rozwiązywane serwerowo z listą realnych nazw; chmura widzi tylko uid. Rozdziela tożsamość połączenia od operatora i omija kolizję PII↔rozpoznanie osoby.

---
### Uwaga wdrożeniowa
To **wieloczęściowy feature** (backend + migracja DB + flow „kim jesteś?" + ew. UI listy wyboru), nie szybki fix. Rekomendacja: wdrażać T1→T2→T3→T4 etapami, z /qa LIVE na końcu.
