---
sprint_id: "WRITE-01"
workspace: "SmartMyOdoo"
status: "IN_PROGRESS"
created: 2026-06-25
closed: null
goal: "Domknąć BEZPIECZNY ZAPIS z czata na Odoo wg best-practice (supervised-by-default + arm/disarm + step-up auth). Dziś: zapis = propozycja Shadow Mode (pending), approve wymaga PIN, ALE execute_approved_proposals() NIGDY nie jest wołane (luka E-W003) i sandbox fail-closed blokuje (brak ODOO_MASTER_PASSWORD). Dowieźć: (1) endpoint APPLY (PIN step-up) faktycznie wykonujący propozycję na Odoo; (2) widoczny tryb 🟢 tylko-odczyt ↔ 🔴 edycja (auto-wygasa); (3) popup PIN przy zapisie z cache step-up ~15 min; (4) tiery (read/write/delete) + audyt każdej akcji."
prefix: "WRITE"
complexity: 7
roadmap_ref: "SPIKE-004 (Safe Write Mode) + research best-practice 2026-06-25 (HITL approval, step-up auth, arm/disarm)."
parent_sprint: null
spike_ref: "SPIKE-004-Safe-Write-Mode-PIN-Auth"
tags: ["write", "shadow-mode", "step-up-auth", "proposals", "odoo", "gdpr", "adr-013", "adr-008"]
---

# 🧱 Sprint: WRITE-01 — Bezpieczny tryb zapisu (Shadow Mode → Odoo)

> **Architekt:** /arch | **Konsumuje:** SPIKE-004 | **Data:** 2026-06-25 | **ADR:** 005, 008, 010, 013

## 📋 Sekcja A — Discovery & Decyzje (/arch)

### 0A. Business Discovery
- **Dla kogo?** Operator, który chce, by czat NIE tylko czytał, ale i ZAPISYWAŁ do Odoo — pod świadomą kontrolą.
- **Problem:** zapis dziś nie dochodzi do skutku (propozycja powstaje, approve zmienia status, ale nic nie wykonuje; sandbox blokuje). Brak widocznego trybu i jasnej autoryzacji per-zapis.
- **Metryka sukcesu:** w trybie 🔴 + PIN realna propozycja zostaje WYKONANA na Odoo 19 (rekord powstaje/zmienia się), zalogowana w audit_log; w 🟢 zapis nie dotyka prod. Step-up nie pyta o PIN przy każdym zapisie (cache ~15 min).
- **Zakres:** cel LOKALNY (ADR-008) — PIN+execute nie wysyłają danych do chmury, tylko na lokalne/self-hosted Odoo.

### 0B. Fakty (SPIKE-004, plik:linia)
| Fakt | Dowód |
|---|---|
| Zapis → propozycja `pending` (Shadow Mode) | `mcp/shadow_mode.py:38-82` |
| **execute_approved_proposals() NIGDY nie wołane (luka)** | `mcp/server.py:330-370`, GREP: 0 callsites (E-W003) |
| approve wymaga PIN (require_auth), tylko zmienia status | `api_routers/proposals.py:50-71`, `api_deps.py:38-47` |
| Sandbox fail-closed bez `ODOO_MASTER_PASSWORD` = RuntimeError | `swarm/sandbox.py`, `.env.example` (E-W002) |
| Karta propozycji w UI (Approve/Reject) | `ui/js/components/chat.js:289-399` |
| Proposal: status pending/approved/executed/rejected, workspace_id | `core/models.py` Proposal |

### 0B-bis. RESEARCH best-practice → decyzje
| Wzorzec (źródło) | Decyzja |
|---|---|
| Write supervised-by-default, read autonomiczny (StackAI/Agno) | **D5** — 🟢 (Shadow) domyślny; istnieje |
| Approval = blocking gate, stan do decyzji człowieka; challenge-response (intent/blast-radius) | **D6** — karta pokazuje CO się zmieni przed apply |
| Tryb = arm/disarm; mody niebezpieczne → bardzo widoczny + auto-expire (NN/g) | **D2** — toggle 🟢/🔴, auto-wygasa |
| Step-up auth (nie pełne przelogowanie); **cache 15-30 min**; loguj każdą próbę (Ping/SecurityBoulevard) | **D3** — PIN popup, cache ~15 min, audyt |
| Tiery: read/write/delete różne wymagania | **D4** — read auto / write step-up / delete mocniejsze potwierdzenie |

### ⚖️ Decyzje /arch (odpowiedzi na Q1–Q5 SPIKE-004)
- **D1 (Q2 — trigger execute):** **NOWY endpoint `POST /api/proposals/{id}/apply`** (require_auth = PIN step-up). Po walidacji woła `execute_approved_proposals()` dla TEJ propozycji → realny zapis na live Odoo → status `executed`. Per-propozycja (nie batch), jawna autoryzacja człowieka.
- **D2 (Q1 — toggle):** Tryb edycji = **efemeryczny stan UI** (NIE migracja DB — wbrew SPIKE §4; prostsze i bezpieczniejsze). Przełączenie 🟢→🔴 wymaga PIN (step-up). **Auto-wygasa** (np. 15 min bezczynności / zmiana zakładki → powrót 🟢).
- **D3 (step-up cache):** Po wpisaniu PIN-u — „sesja edycji" ważna ~15 min (cache po stronie klienta + ew. krótki znacznik serwerowy). Kolejne apply w oknie nie pytają o PIN. Każde wpisanie (i błąd) → `audit_log`.
- **D4 (Q4 — audyt):** Reużyj `audit_log` (jest) — wpis na każde apply (kto/co/model/method/proposal_id/wynik). BEZ nowej tabeli w MVP.
- **D5 (sandbox):** Ścieżka APPLY (człowiek+PIN+🔴) **wykonuje przez `execute_approved_proposals()` BEZPOŚREDNIO na live Odoo — z pominięciem sandboxa** (PIN+jawny tryb = bramka). Sandbox zostaje dla autonomicznych prób agenta (defense-in-depth). To usuwa blokadę fail-closed dla świadomego zapisu. [potwierdzić w /sec]
- **D6 (Q5 — revert):** Status **one-way** (pending→approved→executed) w MVP. Reject tylko z pending/approved.
- **D7 (Q3 — refresh):** Manualny / polling w MVP (WebSocket poza zakresem).
- **D8 (GDPR ADR-013):** Propozycje (w tym executed) — retencja 30 dni, `workspace_id`, kasowane przy purge workspace. Bez zmian (już objęte).

## 0C. User Stories
| ID | JAKO | CHCĘ | KIEDY → TO |
|----|------|------|-----------|
| US-1 | operator | by domyślnie nic nie szło na prod | KIEDY 🟢 TO zapis = propozycja, zero zmian w Odoo |
| US-2 | operator | widoczny przełącznik 🟢/🔴 u góry | KIEDY patrzę na czat TO wiem w jakim jestem trybie |
| US-3 | operator | by wejście w 🔴 wymagało PIN | KIEDY przełączam na 🔴 TO popup PIN (ten co przy logowaniu) |
| US-4 | operator | by zapis faktycznie trafił na Odoo | KIEDY apply w 🔴 z ważnym PIN TO `execute_approved_proposals` wykonuje na live Odoo, status=executed |
| US-5 | operator | by nie pytało o PIN przy każdym zapisie | KIEDY wpisałem PIN <15 min temu TO apply bez ponownego PIN |
| US-6 | operator | by 🔴 samo wygasało | KIEDY 15 min bezczynności / zmiana zakładki TO powrót do 🟢 |
| US-7 | bezpieczeństwo | by każdy realny zapis był zalogowany | KIEDY apply TO wpis w audit_log (kto/co/wynik) |
| US-8 | operator | mocniejsze potwierdzenie dla usuwania | KIEDY method=delete TO dodatkowe potwierdzenie (challenge) |

## 🧱 Sekcja B — Zadania (/dev)
| # | Zadanie | Pliki | Testy | Status |
|---|---------|-------|-------|--------|
| T1 | **Endpoint APPLY (PIN step-up)** — `POST /api/proposals/{id}/apply` (require_auth) → `execute_proposal_by_id` (per-propozycja, bypass sandbox D5) → status=executed + audit_log. Idempotencja (`proposal_lock`). | `api_routers/proposals.py`, `mcp/server.py` | `test_apply_proposal.py` (6) | ✅ DONE (BACKEND; domyka lukę E-W003; create/update/delete + idempotencja + guardy; mock — bez prod write. LIVE/UI = T2-T5) |
| T2 | **Toggle 🟢/🔴 (górny pasek)** — efemeryczny stan UI, mocny wskaźnik; 🟢→🔴 odpala popup PIN; auto-expire (timer + zmiana zakładki). | `ui/index.html`, `ui/js/*` | (manual/e2e) toggle widoczny; 🔴 wymaga PIN; auto-powrót | ⬜ TODO |
| T3 | **Popup PIN (step-up) + cache 15 min** — modal z PIN, walidacja przez `/api/auth`; po sukcesie „sesja edycji" 15 min; kolejne apply bez PIN. Audyt prób. | `ui/js/*`, ew. `api_routers/auth.py` | popup; cache; audyt prób | ⬜ TODO |
| T4 | **Tiery + challenge (D4/D6)** — karta apply pokazuje CO się zmieni (model/method/values); delete = dodatkowe potwierdzenie. | `ui/js/components/chat.js`, `proposals.py` | delete wymaga 2. potwierdzenia; karta pokazuje diff | ⬜ TODO |
| T5 | **Regresja + /qa LIVE + GDPR** — pełna pytest; LIVE: 🔴+PIN→apply→rekord w Odoo 19→executed→audit; 🟢→brak zmian; retencja/workspace OK. | testy | 0 failed; LIVE apply realny | ⬜ TODO |

> **Kolejność:** T1 (backend — domyka lukę E-W003) → T3 (step-up) → T2 (toggle) → T4 (tiery) → T5. /qa LIVE na końcu na bezpiecznym, testowym rekordzie.

## 🛡️ Sekcja D — Security (/sec)
- [ ] APPLY wymaga ważnego PIN (require_auth); bez/zły PIN → 401, zero zapisu.
- [ ] D5 (bypass sandbox w trybie 🔴) zatwierdzony — PIN+jawny tryb to wystarczająca bramka; sandbox zostaje dla agenta. [WYMAGA AKCEPTACJI /sec]
- [ ] Każdy apply (sukces/błąd) + każda próba PIN w `audit_log` (ADR-013).
- [ ] ADR-008: apply tylko na lokalne/self-hosted Odoo, zero chmury.
- [ ] Delete (unlink) = mocniejsze potwierdzenie (blast radius).
- [ ] PII: `reason`/`values` anonimizowane w logach zgodnie z ADR-011/013.

## 🔬 Sekcja C — DoD (/qa + /gf-review)
- [ ] US-1/US-4: 🟢 brak zmian; 🔴+PIN→apply→rekord realnie w Odoo 19, status=executed.
- [ ] US-3/US-5/US-6: 🔴 wymaga PIN; cache 15 min; auto-expire.
- [ ] US-7: apply zalogowany w audit_log.
- [ ] US-8: delete wymaga dodatkowego potwierdzenia.
- [ ] Regresja 0 failed; /qa LIVE na testowym rekordzie.

### Otwarte (do potwierdzenia przed /dev)
- D5 (bypass sandbox) — akceptacja /sec. Alternatywa: wymusić `ODOO_MASTER_PASSWORD` i robić dry-run w sandboxie PRZED apply (bezpieczniejsze, ale cięższe). /arch rekomenduje D5 dla MVP + dry-run jako faza 2.

> Po WRITE-01: czat potrafi BEZPIECZNIE zapisywać na Odoo — domyślnie tylko-odczyt (🟢), świadome 🔴+PIN (step-up, cache 15 min, auto-expire), realny apply przez execute_approved_proposals, pełny audyt. Zgodne z best-practice (supervised-by-default + arm/disarm + step-up).
