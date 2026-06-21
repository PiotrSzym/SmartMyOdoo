---
sprint_id: "KEY-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-15
closed: 2026-06-21
goal: "Typowany rejestr kluczy (odoo_data/odoo_timesheet/llm_provider) + routing modeli LLM per skill z poziomami kosztów — koniec rozpoznawania po magicznej nazwie"
prefix: "KEY"
complexity: 4
roadmap_ref: "DESIGN-credentials-and-model-routing.md (K1-K6)"
epic_ref: "FIX-02 → S5.1 (rozszerzenie)"
tags: ["credentials", "vault", "llm", "routing", "cost-optimization", "tdd"]
---

# 🔑 Sprint: KEY-01 — Typowany Rejestr Kluczy + Routing Modeli LLM

> **Architekt:** /arch | **Tryb:** Sequential (klucze → modele → UI) | **Data:** 2026-06-15
> **Projekt:** [DESIGN-credentials-and-model-routing](../architecture/DESIGN-credentials-and-model-routing.md) | **Bazuje na:** main po FIX-02

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Dziś klucze rozpoznawane są po **magicznej nazwie** (`OPENROUTER_KEY`, `{ws}_ODOO`) — literówka = klucz niewidoczny; brak wyboru modelu; brak kontroli kosztów per zadanie. KEY-01 wprowadza **typy kluczy** i **routing modeli z poziomami kosztów**, by: (1) 100 dowolnie nazwanych kluczy po prostu działało, (2) tanie modele robiły proste rzeczy (niższy koszt AI), (3) rozdzielić Odoo klienta (dane) od Odoo rozliczeniowego (czas pracy).

### User Stories
| ID | As a... | I want... | So that... |
|----|---------|-----------|------------|
| US-KEY-01-1 | Admin | dodawać klucze z **typem** (Odoo dane / Odoo czas / LLM), nie magiczną nazwą | nazwa to tylko etykieta; system trafia po typie |
| US-KEY-01-2 | Agent | osobne połączenie Odoo do **danych klienta** i do **logowania czasu** | dane czytam z Odoo klienta, godziny loguję do własnego/rozliczeniowego |
| US-KEY-01-3 | Operator | wybierać **poziom modelu** (tani/standard/premium) per funkcja | proste zadania = tani model = niższy koszt |
| US-KEY-01-4 | System | **fallback + budżet** (degradacja do tańszego) | błąd providera/wyczerpany budżet nie wywala zadania |

### Metryka sukcesu (DoD)
`pytest` ≥ obecny baseline + 0 regresji; nowe testy K1-K6 zielone; pokrycie `vault`/resolver/routing ≥ 85%.

### ⚖️ ZASADY SPRINTU
- **Kompatybilność wsteczna 🔴:** istniejące sekrety (`OPENROUTER_KEY`, `*_ODOO`) działają dalej (auto-tag), zero migracji ręcznej.
- **Evidence Before Claims 🟠:** każdy task RED→GREEN (test pada przed, przechodzi po).
- **Sequential gate 🔴:** modele (K4-K5) po kluczach (K1-K3); UI (K6) na końcu.

---

## 🧱 Sekcja B — Podział Zadań (RED → GREEN)

### FAZA I — Typowany rejestr kluczy (owner /dev, sec review /sec)
| # | Zadanie | Pliki | Test dowodowy | Status |
|---|---------|-------|---------------|--------|
| K1 | Model `Credential` + enum `CredentialType` (`odoo_data`/`odoo_timesheet`/`llm_provider`) + walidacja (LLM wymaga provider+api_key; Odoo wymaga url/db/login) | `vault/schemas.py` / `core/models.py` | RED: konstrukcja LLM bez provider→błąd; GREEN po walidatorze | ⬜ |
| K2 | `resolve_credential(type, workspace_id, provider=None)` + **auto-tag legacy** (`OPENROUTER_KEY`→llm_provider/openrouter; `*_ODOO`→odoo_data) | `vault/resolver.py` (NEW) | RED: 2 klucze llm różnych providerów → wybór po provider; `*_ODOO` auto-otagowany; nieotagowany legacy nadal działa | ⬜ |
| K3 | Rozdział `odoo_timesheet` vs `odoo_data`: timesheet flow używa `odoo_timesheet`, CRUD/ETL używa `odoo_data` | `api_routers/workspaces.py`, `_get_odoo_connector` | RED: timesheet sięga po `odoo_timesheet`; gdy brak → fallback `odoo_data` z ostrzeżeniem | ⬜ |
| — | **BRAMKA I:** resolver + legacy + 3 typy zielone | — | ✅ start FAZY II | ⬜ |

### FAZA II — Routing modeli LLM + koszty (owner /dev)
| # | Zadanie | Pliki | Test dowodowy | Status |
|---|---------|-------|---------------|--------|
| K4 | `ModelTier` (CHEAP/STANDARD/PREMIUM) + `SKILL_TIER` (mapowanie skill→tier) + resolver modelu (per skill, override per request/workspace) | `swarm/model_policy.py` (NEW), `dispatcher.py` | RED: `classify_intent`→CHEAP; `software_architecture`→PREMIUM; override wymusza model | ⬜ |
| K5 | `litellm.Router` retry/backoff + fallback provider + cache (Redis); **spójne ID** (`openrouter/<provider>/<model>`, walidacja); **governor: degradacja tier** zamiast twardego bloku gdy budżet niski | `swarm/llm_client.py`, `mcp/token_governor.py` | RED: 429→retry sukces; budżet niski→tier↓ (nie block); złe ID→walidacja | ⬜ |

### FAZA III — UI (owner /dev + /front, review /gf-review)
| # | Zadanie | Pliki | Test dowodowy | Status |
|---|---------|-------|---------------|--------|
| K6 | Formularz „Dodaj Sekret": **dropdown Typ** + pola dynamiczne (LLM: provider+api_key; Odoo: url/db/login; timesheet: +projekt/zadanie). Sekcja **„Modele AI"**: wybór modelu per tier + budżet | `ui/index.html`, `ui/js/*` | e2e: dodanie klucza LLM i Odoo **przez typ** (nie nazwę); lista pokazuje typ/przeznaczenie | ⬜ |

---

## 🔬 Sekcja C — Weryfikacja & Wyjście

### Bramki wyjścia (DoD)
- [ ] 3 typy kluczy + resolver po typie; legacy auto-tagowane (kompatybilność)
- [ ] timesheet używa `odoo_timesheet` (rozdział od `odoo_data`)
- [ ] routing modeli per skill (CHEAP/STANDARD/PREMIUM) + override; Dispatcher zawsze CHEAP
- [ ] `litellm.Router` retry/fallback/cache; spójne ID; governor degraduje tier przy niskim budżecie
- [ ] UI: dropdown Typ + sekcja Modele AI; koniec wymogu magicznych nazw
- [ ] `pytest` 0 regresji; pokrycie krytycznych ≥ 85%
- [ ] /doc: CHANGELOG [KEY-01]; aktualizacja [DESIGN](../architecture/DESIGN-credentials-and-model-routing.md) (status: WDROŻONE)

### Handoff
```
/arch (ten artefakt + DESIGN) → /dev (K1→K5) → /front (K6) → /qa → /gf-review → /doc → Release
```

> **Pierwszy krok wykonawczy:** K1 (model `Credential` + typy) — fundament dla resolvera i reszty.
