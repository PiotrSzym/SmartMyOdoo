---
sprint_id: "WRITE-03"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-26
closed: 2026-06-26
goal: "Naprawić REALNĄ mechanikę zapisu (apply), która była złamana od WRITE-01. Diagnoza (log + baza): (1) endpoint /api/proposals/{id}/apply NIE wstrzykuje poświadczeń Odoo ze Skarbca → execute_proposal_by_id → get_odoo_client → „Brak konfiguracji Odoo” → 500 (user klikał 💾 Zapisz 4× — za każdym 500, nazwa się nie zmieniała); (2) narzędzia zapisu hardkodują workspace_id='default' (LLM go nie przekazuje, wrappery go nie forwardują) → propozycja celuje w Odoo 16 (default), a user patrzy na Odoo 19 (myodooTest). Cel: apply wstrzykuje creds (koniec 500) + propozycje noszą REALNY workspace (zapis trafia w bazę, na którą patrzysz)."
prefix: "WRITE"
complexity: 5
roadmap_ref: "Po WRITE-02 (prawda o zapisie). Diagnoza usera 2026-06-26: „nazwa się nie zmieniła pomimo prawidłowej reakcji”. WRITE-02 naprawił RAPORTOWANIE, WRITE-03 naprawia samą MECHANIKĘ apply."
parent_sprint: "WRITE-02"
tags: ["write", "apply", "credentials", "workspace-routing", "bugfix", "trust"]
---

# 🧱 Sprint: WRITE-03 — Naprawa pętli apply (creds + routing workspace)

> **Architekt:** /arch | **Data:** 2026-06-26

## 0A. Problem (1 zdanie)
Zatwierdzenie (💾 Zapisz) nigdy nie zmieniało rekordu: apply zwracał 500 (brak wstrzykniętych credów), a nawet przy sukcesie zapis trafiał w złą instancję Odoo (propozycja tagowana „default”).

## 0B. Fakty (kod + DOWODY runtime)
| Fakt | Dowód |
|---|---|
| apply 4× → 500; `execute_proposal_by_id 1759a778: Brak konfiguracji Odoo` | log `/tmp/smartmyodoo_8001.log`, `server.py:431` |
| Endpoint apply NIE wołał `_inject_odoo_creds` (czat woła) | `proposals.py:120` (przed fixem) vs `chat.py:253` |
| Wrappery `odoo_create/update/delete` nie przyjmują/forwardują `workspace_id` → twarde „default” | `swarm/tools.py:130,138,152` (przed fixem) |
| Wszystkie propozycje crm.lead tagowane `workspace_id='default'` | baza `proposals` (d6daeff3, ac894347, 1759a778) |
| Skutek: 1207 w Odoo16(`default`)=„Traktory 200”, w Odoo19(`myodooTest`)=„Traktory” | XML-RPC read obu instancji |
| `_generate_schema` pomija `workspace_id` → dodanie param do wrappera NIE pokazuje go LLM | `swarm/tools.py:57` |

## ⚖️ Decyzje (/arch)
- **D1 — apply wstrzykuje creds.** Endpoint apply replikuje bramę `_inject_odoo_creds` (KEY-02-3/ADR-007) dla `prop.workspace_id`, korzystając z klucza Skarbca z `require_auth` (`auth_data[0]`). Bez tego `get_odoo_client` nie ma URL/DB → 500.
- **D2 — propozycje noszą realny workspace.** Executor wstrzykuje `self.workspace_id` do argumentów narzędzi `WRITE_TOOLS` (LLM go nie podaje). Wrappery `odoo_*` przyjmują i forwardują `workspace_id` do `*_odoo_record` (`_generate_schema` go pomija → schemat LLM bez zmian).
- **D3 — pusty workspace = brak nadpisania.** Gdy `self.workspace_id` puste (testy jednostkowe), nie wstrzykujemy — zostaje domyślny „default” narzędzia.

## 🧱 Sekcja B — Zadania (/dev)
| # | Zadanie | Pliki | Testy | Status |
|---|---------|-------|-------|--------|
| T1 | **apply wstrzykuje creds** ze Skarbca dla `prop.workspace_id` przed `execute_proposal_by_id` | `api_routers/proposals.py` | LIVE: get_odoo_client(myodooTest) OK po injekcji → koniec 500 | ✅ DONE |
| T2 | **realny workspace w propozycji** — executor wstrzykuje `workspace_id` do WRITE_TOOLS; wrappery `odoo_*` forwardują go | `swarm/executor.py`, `swarm/tools.py` | unit: write-tool dostaje realny ws; pusty ws nie nadpisuje | ✅ DONE |
| T3 | **Regresja + LIVE** | testy | 0 failed; LIVE: 🔴 w myodooTest → propozycja tagowana myodooTest, get_odoo_client→Odoo19 | ✅ DONE |

## 🛡️ Sekcja D — Security/Trust
- [x] Realny zapis nadal tylko przez apply+PIN (`require_auth`) — bez zmian bramki.
- [x] Brak wycieku credów: injekcja per-żądanie, nic nie trafia do logów/PII.
- [x] Apply celuje w jawnie otagowaną instancję (koniec „default” jako ślepy alias).

## 🔬 DoD
- [x] apply nie zwraca już „Brak konfiguracji Odoo” (LIVE: get_odoo_client(myodooTest) OK).
- [x] Propozycja z czatu w `myodooTest` ma `workspace_id='myodooTest'` (LIVE: prop 94609572).
- [x] Regresja 0 failed.
- [ ] *(po stronie usera)* 💾 Zapisz+PIN w UI → rekord realnie zmieniony w Odoo 19 (apply blokowany dla agenta — wykonuje człowiek).

> Po WRITE-03: pętla zapisu działa naprawdę — 💾 Zapisz zapisuje (koniec 500) i trafia w bazę, na którą patrzysz. Domyka WRITE-01/02: prawda o zapisie (W-02) + działająca mechanika (W-03).
