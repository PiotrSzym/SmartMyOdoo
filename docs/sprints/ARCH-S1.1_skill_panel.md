# ARCH-S1.1: Panel Wyboru Skilli dla Czatu AI
> **Roadmap Context:** SmartMyOdoo → Phase S1 — Swarm Integration
> Date: 2026-06-07
> Status: ✅ Done

---

## 📊 PROGRESS BAR (Omnidirected)
| # | Block (Task Name) | Arch | Dev | QA | Doc | Status |
|---|-------------------|:----:|:---:|:--:|:---:|:------:|
| 1 | UI: Zakładka Skille + SkillPanel | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | Backend: GET /api/skills + ChatRequest | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | Backend: Dispatcher bypass / feedback | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | Integracja: UI ↔ API full-stack wire | ✅ | ✅ | ✅ | ✅ | ✅ |

**Status Summary:** 4/4 ✅ Done | 0/4 🟡 In Dev | 0/4 🔵 Planned

> **Legend:** Arch=Planned, Dev=Coded, QA=Audited, Doc=Documented. A block is only DONE once all 4 agent columns are marked ✅.

---

## SEKCJA A — ARCHITECT (/arch, /plan)
> **Active Skills:** `architecture`, `plan-writing`, `ui-skills`

### A1. User Story & Acceptance Criteria
| ID | As a... | I want... | So that... | E2E Test Link |
|----|---------|-----------|------------|---------------|
| US-001 | Użytkownik Hub | wybrać ręcznie skille przed wysłaniem pytania | mogę kontrolować, jakiej wiedzy użyje Agent | `tests/e2e/test_skill_panel.py` |
| US-002 | Użytkownik Hub | kliknąć program "Analiza bazy" i zobaczyć auto-zaznaczone checkboxy | nie muszę pamiętać, które skille są potrzebne | `tests/e2e/test_skill_panel.py` |
| US-003 | Użytkownik Hub | zobaczyć w panelu, które skille Dispatcher wybrał automatycznie | mam transparentność decyzji AI | `tests/e2e/test_skill_panel.py` |

### A2. L1-L5 Decision Matrix
| Level | Key Decision | Rationale | Skill Used |
|-------|--------------|-----------|------------|
| **L1** | Nowa zakładka "🧠 Skille" w tab-bar obok "⚙️ Projekt" | Użytkownik wyraźnie wskazał umiejscowienie; skill panel = osobna sekcja, nie overlay | `ui-skills` |
| **L2** | 5 presetów (programów) mapowanych na grupy z 11 skilli | Pokrywa 90% use-case'ów; ręczne checkboxy na resztę | `architecture` |
| **L3** | `selected_skills: Optional[List[str]]` w `ChatRequest` | Minimalna zmiana kontraktu API; null = auto-dispatch | `api-patterns` |
| **L4** | Bypass Dispatchera gdy `selected_skills` niepuste; feedback `selected_skills` w `ChatResponse` | Dwukierunkowy kontrakt: UI→API i API→UI | `architecture` |
| **L5** | Nowy plik `skills.js`, endpoint `GET /api/skills`, modyfikacja `chat.js::sendToAPI()` | Scope isolation — brak ryzyka regresji w istniejących komponentach | `plan-writing` |

### A3. ADR / Complexity Score
- **Complexity Score:** 🟡3 (Medium — nowy UI + modyfikacja API kontraktu, bez zmian w Executorze)
- **ADR:** Nie wymagane (score < 4). Decyzja dokumentowana w tym sprint artefakcie.

### A4. Rejestr Skilli (Źródło Prawdy)

| # | SkillName (Enum) | Ikona | System Prompt | read_only | shadow | human_override |
|---|---|---|---|:---:|:---:|:---:|
| 1 | `ODOO_BUSINESS_ANALYST` | 📊 | Standard First — konfiguracja | ❌ | ❌ | ❌ |
| 2 | `ODOO_DEVELOPER` | 💻 | `_inherit` mandatory, no core mod | ❌ | ✅ | ❌ |
| 3 | `ODOO_DEVOPS_GITHUB` | 🚀 | Staging Isolation, Feature Branches | ❌ | ❌ | ❌ |
| 4 | `ODOO_SH_LOGS` | 📋 | Tracebacki bottom-up | ❌ | ❌ | ❌ |
| 5 | `ODOO_AUDIT_HISTORY` | 🔍 | Chatter tracking via mail.message | ✅ | ❌ | ❌ |
| 6 | `ODOO_CRUD` | 🗄️ | Magic Tuples `(0,0,{})` | ❌ | ✅ | ❌ |
| 7 | `ODOO_ETL_MANAGER` | 📦 | Batching 200 rek/req | ❌ | ✅ | ❌ |
| 8 | `FINANCIAL_AUDIT` | 💰 | Lock Dates, Credit Note | ✅ | ❌ | ❌ |
| 9 | `SECURITY_AUDIT` | 🔒 | PII Pseudonymization | ✅ | ❌ | ❌ |
| 10 | `ODOO_API_EXPERT` | 🔌 | API Keys, no auth='public' | ❌ | ❌ | ❌ |
| 11 | `MAGIC_FIX` | 🪄 | Force unlock, kryzysowe | ❌ | ✅ | ✅ |

### A5. Mapowanie Programów → Skille

| # | Program | Ikona | Zaznaczane Skille |
|---|---------|:-----:|-------------------|
| P1 | Analiza bazy danych i modułów | 🔍 | `ODOO_BUSINESS_ANALYST`, `ODOO_CRUD`, `ODOO_AUDIT_HISTORY` |
| P2 | Napisanie modułu / funkcjonalności | 💻 | `ODOO_DEVELOPER`, `ODOO_API_EXPERT`, `ODOO_DEVOPS_GITHUB` |
| P3 | Sprawdzenie błędu | 🐛 | `MAGIC_FIX`, `ODOO_SH_LOGS`, `ODOO_DEVELOPER` |
| P4 | Konfiguracja Odoo | ⚙️ | `ODOO_BUSINESS_ANALYST`, `ODOO_CRUD` |
| P5 | Analiza best practice | 📐 | `SECURITY_AUDIT`, `FINANCIAL_AUDIT`, `ODOO_API_EXPERT` |

### A6. L5 Execution Plan for Developer

| # | Task | Target File | Test File | Score | Status |
|---|------|------------|-----------|:-----:|:------:|
| 1 | Dodaj tab "🧠 Skille" + `<div id="skills-screen">` | `ui/index.html` | — | 🟢1 | ✅ |
| 2 | Zarejestruj tab w `canvas.js` | `ui/js/components/canvas.js` | — | 🟢1 | ✅ |
| 3 | Nowy plik `SkillPanel` klasa | `ui/js/components/skills.js` | — | 🟡3 | ✅ |
| 4 | Logika programów + checkboxów | `ui/js/components/skills.js` | — | 🟢2 | ✅ |
| 5 | `GET /api/skills` endpoint | `api.py` | `tests/test_api_skills.py` | 🟢2 | ✅ |
| 6 | `selected_skills` w `ChatRequest` | `swarm/models.py` | — | 🟢1 | ✅ |
| 7 | `selected_skills` w `ChatResponse` | `swarm/models.py` | — | 🟢1 | ✅ |
| 8 | Bypass Dispatchera w `POST /api/chat` | `api.py` | `tests/test_dispatcher_bypass.py` | 🟡3 | ✅ |
| 9 | `loadSkills()` z API | `ui/js/components/skills.js` | — | 🟢2 | ✅ |
| 10 | `sendToAPI()` + selected_skills | `ui/js/components/chat.js` | — | 🟢2 | ✅ |
| 11 | Dispatcher feedback → panel refresh | `ui/js/components/chat.js` | — | 🟢2 | ✅ |
| 12 | INTEGRATE: Full-stack smoke test | — | manual | 🟡3 | ✅ |

---

## SEKCJA B — DEVELOPER (/dev)
> **Active Skills:** `development`, `ui-skills`, `python-fastapi-development`

### Fazy Wykonania (Sequential Gate)

#### FAZA 1: UI — Nowa zakładka + SkillPanel
> **📁 Scope:** `smartmyodoo/ui/index.html`, `smartmyodoo/ui/js/components/skills.js`, `smartmyodoo/ui/js/components/canvas.js`

| # | Zadanie | DoD | Status |
| 1.1 | Dodaj `<button>` "🧠 Skille" w tab-bar (`index.html` linia ~100) z `activeTab: 'skills'` | Tab widoczny obok "⚙️ Projekt" | `[x]` |
| 1.2 | Dodaj `<div id="skills-screen">` w `index.html` pod `chat-screen` | Kontener istnieje w DOM | `[x]` |
| 1.3 | Dodaj `<script src="js/components/skills.js" defer>` w `<head>` | JS ładowany | `[x]` |
| 1.4 | Zarejestruj `skills-screen` w `canvas.js` toggle | Zakładka przełączalna | `[x]` |
| 1.5 | Zbuduj klasę `SkillPanel` z hardkodowaną listą 11 skilli + 5 programów | Panel renderuje grid 3-kolumnowy + przyciski | `[x]` |
| 1.6 | Logika `toggleProgram(id)` — zaznacza/odznacza grupę checkboxów | P1 → 3 checkboxy active | `[x]` |
| 1.7 | Getter `getSelectedSkills()` — zwraca `string[]` zaznaczonych skilli | Wynik czytelny z `chat.js` | `[x]` |
| | **BRAMKA 1:** Serwer startuje, tab "🧠 Skille" widoczny, checkboxy reagują | `python -m smartmyodoo.api` + manualna weryfikacja | `[x]` |

---

#### FAZA 2: Backend — API Skills + ChatRequest
> **📁 Scope:** `smartmyodoo/api.py`, `smartmyodoo/swarm/models.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|:------:|
| 2.1 | Dodaj `selected_skills: Optional[List[str]] = None` do `ChatRequest` w `models.py` | Pole parsowane przez Pydantic | `[x]` |
| 2.2 | Dodaj `selected_skills: Optional[List[str]] = None` do `ChatResponse` w `models.py` | Pole zwracane w JSON | `[x]` |
| 2.3 | Nowy endpoint `GET /api/skills` — iteruje `SKILL_REGISTRY`, zwraca JSON [{name, icon, description, read_only, shadow_mode, human_override}] | `curl localhost:8000/api/skills` → 11 wpisów | `[x]` |
| 2.4 | `POST /api/chat`: jeśli `req.selected_skills` niepuste → bypass `dispatcher.classify_intent()`, ustaw `selected_skills` w response | Request z `selected_skills` omija Dispatchera | `[x]` |
| 2.5 | `POST /api/chat`: jeśli `req.selected_skills` puste → Dispatcher wybiera normalnie, dodaj `selected_skills` z routingu do response | Auto-dispatch zwraca wybrane skille | `[x]` |
| | **BRAMKA 2:** `python -m pytest tests/ -v` PASS + `curl /api/skills` → 11 wpisów | Exit Code 0 | `[x]` |

---

#### FAZA 3: Integracja Full-Stack
> **📁 Scope:** `smartmyodoo/ui/js/components/skills.js`, `smartmyodoo/ui/js/components/chat.js`

| # | Zadanie | DoD | Status |
|---|---------|-----|:------:|
| 3.1 | `SkillPanel.loadSkills()` — `fetch('/api/skills')` → dynamiczny render zamiast hardkodu | Panel generowany z API response | `[x]` |
| 3.2 | `ChatPanel.sendToAPI()` — dołącz `window.AppSkills.getSelectedSkills()` do body | Body zawiera `selected_skills: [...]` | `[x]` |
| 3.3 | Po `fetch('/api/chat')` response → jeśli `data.selected_skills` → odśwież checkboxy w panelu | Panel odzwierciedla feedback Dispatchera | `[x]` |
| | **BRAMKA 3:** Full E2E: klik P1 → wyślij wiadomość → backend potwierdza skille → panel aktualny | Manualna weryfikacja | `[x]` |

### B1. Execution Log
| # | Task Ref | Status | Commit Hash | Time | Notes |
|---|----------|:------:|:-----------:|:----:|-------|
| — | — | — | — | — | *Wypełni /dev* |

### B2. Skip/Stub Log
| # | Reason for Skip | Error Log Snapshot | Stub? |
|---|-----------------|:------------------:|:-----:|
| — | — | — | — |

---

## SEKCJA C — QA TESTER (/qa, /test)
> **Active Skills:** `testing-qa`, `code-review-checklist`

### C1. Compliance Audit
| # | Design Check | Compliant? | Deviation/Action |
|---|--------------|:----------:|--------------------|
| 1 | Architect Plan adhered? | ⬜ | — |
| 2 | LOC Limit Check (`skills.js`) | ⬜ | Target: < 300 LOC |
| 3 | Scope Isolation per Phase | ⬜ | No cross-phase file edits |

### C2. Clean Code Sweep Report
*Wypełni /qa po zakończeniu Fazy 3.*

### C3. Phase-Exit Evidence Table (ART.19)
| Phase | Required Evidence | Executor | Verifier | Status |
|-------|-------------------|:--------:|:--------:|:------:|
| FAZA 1 (UI) | Screenshot: tab "Skille" widoczny, checkboxy reagują | `/dev` | `/qa` | ✅ |
| FAZA 2 (Backend) | `curl /api/skills` → 11 wpisów + pytest PASS | `/dev` | `/qa` | ✅ |
| FAZA 3 (Wire) | Pełny flow: P1 → wyślij → backend potwierdza → panel updated | `/dev` | `/qa` | ✅ |

---

## SEKCJA D — DOCUMENTARIAN (/doc)
> **Active Skills:** `documentation`

### D1. Documentation Updates
| File | Action | Description |
|------|:------:|-------------|
| `CHANGELOG.md` | ⬜ UPDATE | Dodaj wpis ARCH-S1.1 — Skill Panel |
| `README.md` | ⬜ UPDATE | Sekcja "Skill Panel" w opisie UI |

---

## SEKCJA E — LESSONS LEARNED (Mandatory)
> *Required before sprint closure. Entries never deleted.*

| # | Agent | Logic / PITFALL | Future Action / Pattern |
|---|:-----:|-----------------|-------------------------|
| — | — | *Wypełnione po zamknięciu sprintu* | — |

> **Final Recommendation:** ✅ DONE
