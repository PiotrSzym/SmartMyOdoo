---
sprint_id: "ERR-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-26
closed: 2026-06-26
goal: "Narzędzia Odoo mają zwracać KONKRETNY, actionable błąd, a nie generyczne „Wystąpił błąd… Szczegóły w logach systemowych”. Dziś prawdziwa przyczyna (Błąd autoryzacji / Odoo nieosiągalne / brak uprawnień do modelu) zostaje TYLKO w logu → model jej nie widzi → ZGADUJE przyczyny (zrzut usera: „może połączenie, może uprawnienia, może chwilowo”) = konfabulacja. Cel: klasyfikator wyjątek→komunikat + reguła „cytuj błąd, nie zgaduj” + retry zimnego startu staging."
prefix: "ERR"
complexity: 4
roadmap_ref: "Zgłoszenie usera 2026-06-26 („nie mamy konkretnego błędu jeżeli nie mogę się połączyć lub że źle stoją środowiska”). Diagnoza: log pokazał „Błąd autoryzacji do Odoo”, a czat zgadywał. Powiązane: TRUST (anty-konfabulacja), WRITE-02/03."
parent_sprint: null
tags: ["errors", "anti-confabulation", "odoo", "resilience", "trust"]
---

# 🧱 Sprint: ERR-01 — Prawda o błędach Odoo

> **Architekt:** /arch | **Data:** 2026-06-26

## 0A. Problem (1 zdanie)
Narzędzia Odoo zwracają generyczne „Szczegóły w logach”, więc model nie zna przyczyny i ZGADUJE (konfabuluje awarie), zamiast podać konkretny błąd i następny krok.

## 0B. Fakty (kod + DOWODY)
| Fakt | Dowód |
|---|---|
| `search_odoo_records`/`read_odoo_schema`/`resolve_person_records` zwracały „Wystąpił błąd… Szczegóły w logach” | `mcp/server.py:131,198,232` (przed fixem) |
| OdooClient rzuca konkretne wyjątki: `ValueError`(brak konfig.), `PermissionError`(auth), `OdooFieldError`, `Fault`, sieć | `mcp/odoo_client.py:80,86,139` |
| Realny log: „Błąd autoryzacji do Odoo”, a czat userowi: „może połączenie / może uprawnienia / chwilowo” | `/tmp/smartmyodoo_8001.log`, zrzut usera |
| Staging odoo.sh hibernuje → 1. authenticate pada (False/timeout), 2. po pauzie działa | diagnoza LIVE („traktory” padło, sekundę później OK) |

## ⚖️ Decyzje (/arch)
- **D1 — Klasyfikator wyjątek→komunikat.** Nowy `mcp/odoo_errors.py::classify_odoo_error(exc, workspace_id)` mapuje typ wyjątku na „❌ …” z przyczyną + sugestią: brak konfig. / autoryzacja (staging budzi się / odśwież creds) / timeout / AccessError / walidacja / nieosiągalne / fallback z typem. Bez sekretów (tylko nazwa przestrzeni).
- **D2 — Podpięcie w narzędziach odczytu.** `read_odoo_schema`, `search_odoo_records`, `resolve_person_records` zwracają `classify_odoo_error(e, workspace_id)`. Koniec „szczegóły w logach”.
- **D3 — Reguła „cytuj, nie zgaduj”.** `ERROR_REPORT_RULE` w `build_system_prompt`: gdy narzędzie zwróci `error` (❌…), model przekazuje DOKŁADNIE tę przyczynę, NIE wymyśla alternatyw.
- **D4 — Retry zimnego startu.** `OdooClient.connect()` ponawia RAZ przy błędzie przejściowym (timeout/sieć/auth-False) po krótkiej pauzie — staging wybudza się i druga próba działa. Stałe False (złe creds) → po retry `PermissionError` (jasny komunikat).

## 🧱 Sekcja B — Zadania (/dev)
| # | Zadanie | Pliki | Testy | Status |
|---|---------|-------|-------|--------|
| T1 | **Klasyfikator** `classify_odoo_error` (7 kategorii, zero „szczegóły w logach”) | NEW `mcp/odoo_errors.py` | unit: każdy typ → trafny komunikat | ✅ DONE |
| T2 | **Retry zimnego startu** w `connect()` (1×, błąd przejściowy) | `mcp/odoo_client.py` | unit: ponawia raz; stałe False→PermissionError | ✅ DONE |
| T3 | **Podpięcie + reguła** w 3 narzędziach odczytu + `ERROR_REPORT_RULE` | `mcp/server.py`, `swarm/executor.py` | unit: reguła w prompcie; LIVE | ✅ DONE |
| T4 | **Regresja + LIVE** | testy | 0 failed; LIVE: błąd → konkret, bez zgadywania | ✅ DONE |

## 🛡️ Sekcja D — Security/Trust
- [x] Komunikat nie ujawnia sekretów (tylko nazwa przestrzeni + kategoria).
- [x] Model nie konfabuluje przyczyn (reguła + test).
- [x] Retry nie maskuje realnego błędu (stałe auth-False → jasny PermissionError).

## 🔬 DoD
- [x] Brak „szczegóły w logach” w sklasyfikowanych błędach (test + LIVE).
- [x] LIVE: błąd Odoo → konkretny komunikat, model cytuje (zero „może połączenie…”).
- [x] Retry: zimny start staging self-heal (unit).
- [x] Regresja 0 failed.

> Po ERR-01: gdy coś pada, SmartMyOdoo mówi PRAWDĘ — konkretną przyczynę i następny krok, zamiast zgadywać. Domyka motyw TRUST po stronie awarii (po WRITE-02/03 = prawda o zapisie).
