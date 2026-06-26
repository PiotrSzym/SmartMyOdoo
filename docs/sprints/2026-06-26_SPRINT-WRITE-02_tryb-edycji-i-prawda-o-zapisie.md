---
sprint_id: "WRITE-02"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-26
closed: 2026-06-26
goal: "Domknąć pętlę zapisu z PRAWDĄ i AUTORYZACJĄ TRYBU. Dziś: (1) backend nie wie, w jakim trybie jest UI (editMode czysto frontendowy) → w trybie 🟢 read i tak powstaje propozycja; (2) narzędzie write zwraca „✅ Propozycja zapisana”, więc model melduje „✅ Gotowe, zmieniłem” = KONFABULACJA udanego zapisu; (3) propozycja z LLM nie wraca jako karta (action_type=CHAT), więc user nie ma jak jej zatwierdzić. Cel: tryb 🟢/🔴 świadomy end-to-end (w 🟢 zapis ZABLOKOWANY z prośbą o przełączenie = autoryzacja), jednoznaczny status PENDING (zero „gotowe”), inline karta z diffem + 💾 Zapisz (apply+PIN)."
prefix: "WRITE"
complexity: 6
roadmap_ref: "Po WRITE-01 (apply+PIN istnieje). Zgłoszenie usera 2026-06-26: „model powiniem rozumieć że jest w trybie read i poprosić o zmianę trybu, by user musiał autoryzować”. Powiązane: ERR-01 (prawda o błędach), TRUST (anty-konfabulacja)."
parent_sprint: "WRITE-01"
tags: ["write", "edit-mode", "anti-confabulation", "shadow-mode", "authorization", "trust"]
---

# 🧱 Sprint: WRITE-02 — Tryb edycji świadomy + prawda o zapisie

> **Architekt:** /arch | **Data:** 2026-06-26

## 0A. Problem (1 zdanie)
W trybie tylko-odczytu (🟢) zapis i tak tworzy propozycję, a model melduje „✅ Gotowe, zmieniłem”, choć nic nie zapisano i user nie ma jak tego zatwierdzić.

## 0B. Fakty (kod, plik:linia) — DOWODY
| Fakt | Dowód |
|---|---|
| `editMode` jest TYLKO we frontendzie (store, nieprzesyłany do API) | `ui/js/store.js` (editMode ephemeryczny), brak `edit_mode` w body `chat.js:498` |
| Backend NIE zna trybu — write tool odpala niezależnie od 🟢/🔴 | `executor.py:480` `_should_sandbox` patrzy tylko na sandbox, nie na tryb |
| Narzędzie write zwraca „✅ Propozycja (UPDATE) zapisana” → model myśli „sukces” | `mcp/server.py:286` (+254/+311) |
| Realny dowód konfabulacji: propozycja `d6daeff3` status `pending`, a czat: „✅ Gotowe, nazwa zmieniona” | baza `proposals`, zrzut usera; nazwa w Odoo nietknięta do apply |
| `/api/chat` (ścieżka LLM) zwraca `action_type="CHAT"` bez `proposal_data` → brak karty | `chat.py:381-388` |
| Frontend MA już kartę propozycji + 💾 Zapisz (apply+PIN) — czeka na dane z backendu | `chat.js:303,366-418,602` |
| Apply+PIN działa end-to-end (zweryfikowane LIVE: 1207 → „Traktory 200”) | `mcp/server.py:372` `execute_proposal_by_id`, endpoint `proposals/{id}/apply` |

## ⚖️ Decyzje (/arch)
- **D1 — Tryb jako autoryzacja.** `ChatRequest.edit_mode: bool`. Frontend wysyła stan kłódki. W trybie 🟢 (read) write-tool jest **blokowany w executorze** (przed inwokacją) — model dostaje komunikat „przełącz na 🔴”. Przełączenie 🔴 wymaga PIN (już jest, `chat.js:546`) = świadoma autoryzacja użytkownika. **Nie ufamy modelowi** — blok jest deterministyczny w backendzie, nie w prompcie.
- **D2 — Jednoznaczny wynik narzędzia.** Write tool zwraca tekst, który NIE wygląda na sukces: „📝 PROPOZYCJA UTWORZONA — NIE wykonano na Odoo. Status: OCZEKUJE. Nie mów „gotowe/zmieniłem”.” + reguła systemowa `WRITE_REPORT_RULE` (anty-„Gotowe”).
- **D3 — Propozycja z LLM wraca jako KARTA.** Executor przechwytuje propozycję utworzoną w pętli narzędzi (`proposal_id`, model, method, values, reason) i zwraca w wyniku; `handle_chat` mapuje to na `action_type="SHADOW_PROPOSAL"` + `proposal_data` → frontend renderuje diff + 💾 Zapisz.
- **D4 — Zero zmian w ścieżce read.** Odczyt (🟢) działa jak dziś; guard dotyczy wyłącznie `WRITE_TOOLS` (`odoo_create/update/delete`).

## 0C. User Stories
| ID | JAKO | CHCĘ | KIEDY → TO |
|----|------|------|-----------|
| US-1 | user | w trybie 🟢 nie tworzyć zmian przypadkiem | KIEDY proszę o zapis w 🟢 TO model mówi „przełącz na 🔴”, NIC nie powstaje |
| US-2 | user | by model nie kłamał „gotowe” | KIEDY powstaje propozycja TO model mówi „przygotowałem, zatwierdź” (nigdy „zmieniłem”) |
| US-3 | user | móc zatwierdzić zmianę z czatu | KIEDY model przygotuje zapis TO widzę kartę z diffem + 💾 Zapisz (apply+PIN) |
| US-4 | user | realny zapis po zatwierdzeniu | KIEDY klikam 💾 Zapisz + PIN TO rekord faktycznie się zmienia w Odoo |

## 🧱 Sekcja B — Zadania (/dev)
| # | Zadanie | Pliki | Testy | Status |
|---|---------|-------|-------|--------|
| T1 | **edit_mode w kontrakcie** — `ChatRequest.edit_mode`; `chat.js` wysyła `editMode`; `handle_chat` przekazuje do executora | `swarm/models.py`, `ui/js/components/chat.js`, `api_routers/chat.py` | unit: pole istnieje, domyślnie False | ✅ DONE |
| T2 | **Read-mode write-guard** — w executorze przed inwokacją write-toola: jeśli `not edit_mode` → blok + komunikat „przełącz na 🔴”, zero inwokacji | `swarm/executor.py` | unit: write w 🟢 nie woła toola, zwraca prośbę o tryb | ✅ DONE |
| T3 | **Prawda o wyniku** — jednoznaczny zwrot narzędzi write + `WRITE_REPORT_RULE` (anty-„gotowe”) | `mcp/server.py`, `swarm/executor.py` | unit: zwrot zawiera „OCZEKUJE”/„NIE wykonano”; prompt ma regułę | ✅ DONE |
| T4 | **Karta propozycji z LLM** — executor przechwytuje propozycję; `handle_chat` zwraca SHADOW_PROPOSAL + proposal_data | `swarm/executor.py`, `api_routers/chat.py` | unit: po write w 🔴 wynik ma proposal; e2e: action_type=SHADOW_PROPOSAL | ✅ DONE |
| T5 | **Regresja + LIVE** — pełna pytest; LIVE: 🟢„zmień”→prośba o tryb; 🔴„zmień”→karta→💾+PIN→rekord zmieniony | testy | 0 failed; LIVE pętla e2e | ✅ DONE |

## 🛡️ Sekcja D — Security/Trust
- [ ] Blok w 🟢 jest DETERMINISTYCZNY w backendzie (nie ufamy modelowi).
- [ ] Realny zapis tylko przez apply+PIN (bez zmian — bramka istnieje).
- [ ] Model nie może zaraportować zapisu jako wykonanego, gdy status ≠ executed.

## 🔬 DoD
- [ ] US-1: 🟢 + „zmień” → prośba o tryb, zero propozycji (LIVE).
- [ ] US-2: brak „gotowe/zmieniłem” gdy tylko propozycja (test + LIVE).
- [ ] US-3: karta z diffem + 💾 Zapisz w czacie (LIVE).
- [ ] US-4: 💾+PIN → rekord realnie zmieniony (LIVE).
- [ ] Regresja 0 failed.

> Po WRITE-02: tryb 🟢/🔴 to realna autoryzacja, model mówi PRAWDĘ o zapisie (propozycja ≠ wykonano), a user zatwierdza zmianę kartą z czatu. Domyka WRITE-01 i motyw TRUST po stronie zapisu.
