---
sprint_id: "UX-07"
workspace: SmartMyOdoo
status: BACKLOG          # BACKLOG → IN_PROGRESS → DONE → ARCHIVED
created: 2026-06-06
closed: null
goal: "Przebudowa Premium GUI: Theme Engine (Light/Dark), Agent Status Live Panel, Demo Tab z ECharts, dopracowany Task Picker Odoo."
prefix: UX               # PM | ARCH | FIX | QA | UX
complexity: 5             # 1-10 (≥7 = Research Gate obowiązkowy)
roadmap_ref: "Faza 7.0: Premium GUI & Observability"
epic_ref: null
tags: [#ui, #ux, #theming, #observability, #echarts, #vanilla-js, #fastapi]
---

# UX-07: Premium GUI Redesign & Agent Observability

> 📍 Roadmapa: Faza 7.0: Premium GUI & Observability
> 📅 Data: 2026-06-06
> 🎯 Cel: Theme Engine (Light/Dark), Agent Status Live Panel, Demo Tab (ECharts), dopracowanie Task Picker i ogólne UX polish.
> 🔄 Flow: /arch → /dev → /qa → /audyt → /doc → Release

---

## 📊 PROGRESS BAR

> Aktualizowany przez KAŻDEGO agenta. Klocek = DONE dopiero gdy WSZYSTKIE kolumny ✅.

| # | Klocek | /arch | /dev | /qa | /audyt | /sec | /doc | Status |
|---|--------|:-----:|:----:|:---:|:------:|:----:|:----:|:------:|
| 1 | Theme Engine (CSS Vars + JS + Toggle) | ✅ | ⬜ | ⬜ | ⬜ | N/A | ⬜ | ⬜ |
| 2 | Agent Status Panel (API + Widget) | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 3 | Task Picker UX Redesign | ✅ | ⬜ | ⬜ | ⬜ | N/A | ⬜ | ⬜ |
| 4 | Demo Tab (ECharts + Canvas) | ✅ | ⬜ | ⬜ | ⬜ | N/A | ⬜ | ⬜ |
| 5 | UX Polish (favicon, toast, markdown) | ✅ | ⬜ | ⬜ | ⬜ | N/A | ⬜ | ⬜ |

**Podsumowanie:** 0/5 ✅ Done | Blokujący: /dev

> Statusy: 🔵 Plan | 🟡 Dev | 🟢 QA | 🔍 Audyt | ✅ Done
> Kolumna /sec: `N/A` jeśli Security Scope (A.10) = Pominięta dla tego klocka

---

## SEKCJA A — ARCHITEKT (/arch)

> Wypełnia: `/arch` | Skille: @ui-skills, @piekne-wykresy, @frontend-design

### 🟢 WARIANT 1: PM / ARCH (Budowa Feature'a / Architektury)

| # | Pytanie | Odpowiedź |
|---|---------|-----------|
| 1 | **Dla kogo?** | Użytkownik końcowy SmartMyOdoo HUB (admin / deweloper Odoo). |
| 2 | **Jaki problem?** | GUI ma tylko ciemny motyw, brak widoczności co robi agent w czasie rzeczywistym, brak panelu wizualizacji, ubogi Task Picker. |
| 3 | **Jak zmierzymy sukces?** | Przełączanie motywów przeżywa F5; floating widget odpytuje `/api/agent/status`; zakładka Demo renderuje wykres ECharts; Task Picker pokazuje rich-cards z projektem i statusem. |

**User Stories:**

**US-1:** JAKO użytkownik HUB CHCĘ przełączać interfejs między trybem jasnym a ciemnym ŻEBY komfortowo pracować o każdej porze dnia.
- KIEDY klikam ikonę ☀️/🌙 TO cały UI natychmiast zmienia kolory i wybór przeżywa odświeżenie (localStorage).

**US-2:** JAKO użytkownik HUB CHCĘ widzieć co agent aktualnie robi ŻEBY mieć pewność, że moje polecenie jest przetwarzane i wiedzieć na jakim jest etapie.
- KIEDY agent przetwarza polecenie TO floating widget w rogu ekranu pokazuje status (THINKING / TOOL_CALL / IDLE) z animacją.

**US-3:** JAKO użytkownik HUB CHCĘ mieć panel Demo z wizualizacjami ŻEBY widzieć statystyki użycia tokenów i stanu workspace'ów.
- KIEDY klikam zakładkę "Demo" TO widzę wykres tokenów i kafelki statusu połączeń.

**US-4:** JAKO użytkownik HUB CHCĘ widzieć szczegóły zadania Odoo przy bindowaniu ŻEBY wybrać właściwe zadanie ze świadomością projektu, statusu i osoby.
- KIEDY otwieram modal szukania zadań TO każdy wynik to karta z projektem, statusem, priorytetem.

---

### A.3 Pattern Registry

> Wzorce, które /dev MUSI naśladować. Kod musi wyglądać JAK referencja.

| Wzorzec | Plik referencyjny | Opis |
|---------|-------------------|------|
| 📐 Observer Store | `ui/js/store.js` | Nowe komponenty MUSZĄ subskrybować stan przez `AppStore.subscribe()` |
| 📐 Component Class | `ui/js/components/chat.js` | Każdy nowy komponent to klasa z `constructor()` → `this.container = document.getElementById(...)` → `render()` |
| 📐 Global Registration | `ui/js/components/activity.js:164-166` | `DOMContentLoaded` → `window.AppXxx = new XxxPanel()` |
| 📐 Escape HTML | `chat.js:342-346` | Zawsze `_escapeHtml()` przed wstawieniem user-data do innerHTML |

### A.4 Skills Audit

> Narzędzia obowiązkowe per agent. /dev NIE wymyśla własnych.

| Agent | Skille bazowe | Skille dodatkowe | Uzasadnienie |
|-------|---------------|------------------|--------------|
| /dev  | @ui-skills, @piekne-wykresy | @powershell-windows | Frontend Vanilla JS + ECharts CDN, serwer FastAPI na Windows |
| /qa   | @systematic-debugging | @find-bugs | Manualna weryfikacja UI (brak Playwright dla Vanilla JS SPA) |

### A.5 Complexity Assessment

> Trudność 1-10. Jeśli ≥7 → STOP → Research Gate (konsultacja /anal).

**Complexity:** 5
**Research Gate:** ⏭️ Nie wymagany (complexity < 7)

**Uzasadnienie oceny:**
- (+) Vanilla JS = brak frameworkowego boilerplate, prosta logika DOM
- (+) Backend stub = endpoint zwraca mock, nie wymaga pipeline integration
- (-) `index.html` monolith (62KB, 1078 linii) = ryzyko regresji przy edycjach
- (-) CSS Variables vs. Tailwind CDN = konieczność ostrożnej koegzystencji
- (-) ECharts CDN = nowa zależność do osadzenia i skonfigurowania

### A.6 Test Strategy

| Warstwa | Potrzebna? | Co testować? | Kto? | Narzędzie |
|---------|:----------:|--------------|:----:|-----------|
| Unit | ❌ | N/A (Vanilla JS, brak bundlera/testu) | — | — |
| Integration | ❌ | — | — | — |
| E2E | ⚠️ | Manualna weryfikacja UI (kliknięcia, F5, nawigacja) | /qa | Przeglądarka (DevTools) |
| API | ✅ | `GET /api/agent/status` zwraca poprawny JSON | /qa | cURL / DevTools Network |
| Visual | ✅ | Screenshot porównanie Light vs Dark | /qa | Manual + screenshot |

### A.7 US→E2E Mapping

> Każda User Story MUSI mieć powiązaną weryfikację. Brak E2E → Weryfikacja manualna.

| US | Scenariusz KIEDY→TO | Test | Priorytet |
|----|---------------------|------|:---------:|
| US-1 | KIEDY toggle → F5 TO motyw zachowany | Manual: klik + F5 + inspekcja `data-theme` | 🔴 Critical |
| US-2 | KIEDY agent idle TO widget pokazuje IDLE | Manual: DevTools Network → 200 + widget visible | 🔴 Critical |
| US-3 | KIEDY tab Demo TO wykres widoczny | Manual: klik zakładka → canvas renderuje ECharts | 🟡 High |
| US-4 | KIEDY Task Search TO rich-card widoczny | Manual: modal → inspekcja renderowanych kart | 🟡 High |

### A.8 Per-Task Test Types

> Dla KAŻDEGO zadania z Sekcji B — jakie testy wymagane.

| Zadanie | Unit | Integration | E2E/Manual | Plik/narzędzie testowe |
|---------|:----:|:-----------:|:----------:|------------------------|
| B1 (CSS Variables) | — | — | ✅ | Inspekcja DevTools: Computed Styles |
| B2 (Theme JS) | — | — | ✅ | F5 test + localStorage check |
| B3 (Agent Status API) | — | — | ✅ | `curl http://127.0.0.1:8000/api/agent/status` |
| B4 (Agent Widget) | — | — | ✅ | DevTools Network: polling requests |
| B5 (Task Picker) | — | — | ✅ | Modal: wizualna inspekcja kart |
| B6 (Demo Tab) | — | — | ✅ | Zakładka Demo: wykres renderuje się |
| B7 (UX Polish) | — | — | ✅ | Favicon widoczny, toast kolorowy |

### A.9 Error Registry Check

> Sprawdzenie znanych pułapek.

| ID Błędu | Ryzyko w tym sprincie | Mitygacja |
|----------|-----------------------|-----------|
| P-05 (Monolith HTML) | 🔴 Wysoki — edycja 1078-liniowego pliku bez frameworka | Bramki sekwencyjne: FAZA 1 (theme) → test → FAZA 2 (widget) → test → FAZA 3. Backup index.html przed edycją. |
| P-04 (Chat wydmuszka) | 🟡 Średni — Agent Status widget pokaże IDLE na stałe (stub) | Jawna dokumentacja: "stub endpoint, prawdziwe FSM w Fazie 7.1" |

### A.10 Security Scope

> Decyzja: czy sprint wymaga audytu /sec (Sekcja D).

| Pytanie | Odpowiedź |
|---------|-----------|
| Dotyka auth/login/session? | NIE |
| Dotyka API endpoints? | TAK — nowy `GET /api/agent/status` |
| Nowe zależności npm/go? | NIE (ECharts via CDN `<script>`) |
| Dane osobowe / PII / RODO? | NIE |
| **Wniosek** | **Sekcja D: CZĘŚCIOWA** — /sec sprawdza tylko nowy endpoint (czy wymaga auth). Reszta pominięta. |

### A.11 ADR (jeśli complexity > 5)

Nie wymagane — complexity = 5. Decyzje architektoniczne udokumentowane w Implementation Plan UX-07.

---

## SEKCJA B — DEVELOPER (/dev)

> Wypełnia: `/dev` (SingleDev)
> Skille użyte: [@ui-skills, @piekne-wykresy, @powershell-windows]

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Każdy nowy komponent dodajemy po kolei. Phase N+1 cannot start until Phase N Gate is Green.

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Zmiany w API testujemy cURL lub DevTools przed wdrożeniem do JS.

#### Zasada 3: SAFE REFACTORING 🔴
Podczas zmian w `index.html` (1078 linii) — nie psujemy inicjalizacji Vaulta ani nasłuchów modalów.

### Graf zależności między Fazami

```
┌──────────────────────────────────────┐
│  FAZA 1 (Styling)                    │
│  [Theme Engine & CSS Vars]           │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Przycisk zmienia motyw, przeżywa F5
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Agent Observability)        │
│  [API Endpoint + Floating JS Widget] │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Widget odpytuje /api/agent/status, 200 w Network
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (UX Polish & Demo)           │
│  [Demo Tab + Task Picker Redesign]   │
└──────────────────────────────────────┘
```

### B.1 Zadania (checkboxy + Evidence)

> Reguły:
> - `[ ]` = do zrobienia | `[/]` = w trakcie | `[x]` = gotowe
> - Każdy `[x]` MUSI mieć Evidence (plik → sygnatura)

#### FAZA 1: Theme Engine (Light/Dark)

> **📁 Scope:** `ui/index.html`, `ui/css/theme.css`, `ui/js/components/theme.js`

- [x] **B1 (CSS Variables):** Utworzenie `ui/css/theme.css` z design tokenami (`--bg-primary`, `--bg-card`, `--text-primary`, `--accent`, itp.) w wariantach `:root[data-theme="dark"]` i `:root[data-theme="light"]`.
      📐 Wzorzec: Standalone Analytics Standard (KI)
      📝 Evidence: `ui/css/theme.css`
- [x] **B2 (Theme JS Logic):** Utworzenie `ui/js/components/theme.js` z klasą `ThemeEngine`: `toggle()`, `setTheme()`, `getTheme()`, `localStorage('smo-theme')`.
      📐 Wzorzec: Component Class (A.3)
      📝 Evidence: `ui/js/components/theme.js`
- [x] **B3 (HTML Integration):** Zamiana kluczowych hardkodowanych kolorów w `index.html` na `var()`. Dodanie przycisku ☀️/🌙 w Tab Bar. Linkowanie `theme.css` i `theme.js`.
      📐 Wzorzec: Istniejący Tab Bar w index.html
      📝 Evidence: `ui/index.html` (lines 41-48, 90-95)
- [ ] **BRAMKA F1:** ✅ Kliknięcie na ☀️/🌙 natychmiast zmienia kolory. F5 → motyw zachowany. Wszystkie ekrany poprawne w obu motywach.

#### FAZA 2: Agent Observability (Live Status)

> **📁 Scope:** `api.py`, `ui/js/components/agent-status.js`, `ui/index.html`

- [ ] **B4 (FastAPI Endpoint):** Nowy endpoint `GET /api/agent/status` w `api.py` zwracający mock JSON: `{"status": "idle", "task": null, "step": null, "elapsed_s": 0}`. Endpoint wymaga auth (Depends require_auth).
      📐 Wzorzec: Istniejące endpointy w api.py (np. `/api/audit`)
      📝 Evidence: —
- [ ] **B5 (Status Widget JS):** Utworzenie `ui/js/components/agent-status.js` z klasą `AgentStatusPanel`: polling co 3s, stany `IDLE|THINKING|TOOL_CALL|ERROR|WAITING_APPROVAL`, minimalizacja/maksymalizacja.
      📐 Wzorzec: Component Class (A.3), Observer Store (A.3)
      📝 Evidence: —
- [ ] **B6 (Widget UI):** Floating widget w prawym dolnym rogu: pulsujący dot + label statusu + czas trwania. CSS: `position: fixed; bottom: 1rem; right: 1rem; z-index: 40`. Obsługa motywu (jasny/ciemny).
      📐 Wzorzec: Toast w index.html (z-index, fixed position)
      📝 Evidence: —
- [ ] **BRAMKA F2:** ✅ Widget widoczny na ekranie. DevTools Network: `GET /api/agent/status` co 3s → 200. Widget reaguje na zmianę motywu.

#### FAZA 3: Task Picker UX & Demo Tab

> **📁 Scope:** `api.py`, `ui/js/components/demo.js`, `ui/index.html`, `ui/js/components/canvas.js`

- [ ] **B7 (Extended Odoo API):** Zmiana pól `search_read` w `/api/workspaces/{id}/tasks/search`: dodanie `stage_id`, `user_id`, `priority`, `date_deadline` do fields.
      📐 Wzorzec: Istniejący endpoint w api.py:393-429
      📝 Evidence: —
- [ ] **B8 (Task Picker UI):** Przebudowa `task-search-modal` w `index.html`: każdy wynik = karta z nazwą zadania, badge projektu, chip statusu, priorytetem (kolorowe gwiazdki), przypisaną osobą.
      📐 Wzorzec: Shadow Mode Proposal Card (chat.js:267-321)
      📝 Evidence: —
- [ ] **B9 (Demo Tab Setup):** Dodanie 5. zakładki "🎨 Demo" w Tab Bar. Nowy `<div id="demo-screen">` w index.html. Rejestracja w `canvas.js`.
      📐 Wzorzec: Istniejące zakładki w Tab Bar + canvas.js
      📝 Evidence: —
- [ ] **B10 (ECharts Integration):** Utworzenie `ui/js/components/demo.js` z klasą `DemoPanel`. Import ECharts CDN. Wykres bar/line z dummy danymi (tokeny per dzień). Kafelki statusu workspace'ów.
      📐 Wzorzec: Standalone Analytics Standard (KI)
      📝 Evidence: —
- [ ] **B11 (UX Polish):** Favicon (SVG inline lub emoji). Meta `<title>` i `<description>`. Toast system z typami (success ✅ / error ❌ / warning ⚠️). Podstawowy markdown rendering w chat.js (`**bold**`, `` `code` ``, listy).
      📐 Wzorzec: Istniejący `showToast()` w index.html
      📝 Evidence: —
- [ ] **BRAMKA F3:** ✅ Demo renderuje wykres ECharts. Task Modal wyświetla rich-cards. Favicon widoczny w tab przeglądarki. Toast ma kolory per typ.

### B.2 Skipnięte Zadania

| # | Powód Skip | Stub z TODO? |
|---|------------|:------------:|
| Markdown rendering (P-12) | Jeśli zbyt skomplikowane — skip z TODO komentarzem | ✅ |
| Keyboard shortcuts (P-08) | Poza scope sprintu UX-07 | ❌ |
| Responsywność mobilna (P-09) | Poza scope sprintu UX-07 | ❌ |
| Refactoring index.html monolith (P-05) | Osobny sprint, zbyt ryzykowne łączenie | ❌ |

---

## SEKCJA B½ — AUDYTOR (/audyt)

> Wypełnia: `/audyt` (RÓWNOLEGLE z /sec, PO /qa)
> Skille: @kaizen, @verification-before-completion

### Ocena

| Wymiar | Ocena | Uwagi |
|--------|:-----:|-------|
| Pattern Consistency | [-] | |
| Architecture Compliance | [-] | |
| ADR-to-Code Traceability | [-] | |
| Tech Debt | [-] | |
| Skill Usage | [-] | |
| **OVERALL GRADE** | **[-]** | |

---

## SEKCJA C — TESTER (/qa)

> Wypełnia: `/qa` (PO Sekcji B)
> Skille: @systematic-debugging, @find-bugs

### C.1 Zgodność z Planem

| # z B | Zgodne? | Odchylenie | Akcja |
|-------|:-------:|------------|-------|
| B1-B3 (Theme) | ⬜ | | |
| B4-B6 (Agent Status) | ⬜ | | |
| B7-B8 (Task Picker) | ⬜ | | |
| B9-B10 (Demo) | ⬜ | | |
| B11 (UX Polish) | ⬜ | | |

### C.3 Wyniki Testów

| Typ | Narzędzie | Wynik | Pokrycie |
|-----|-----------|-------|----------|
| API | cURL `/api/agent/status` | —/— | — |
| Visual (Dark) | Manual screenshot | —/— | — |
| Visual (Light) | Manual screenshot | —/— | — |
| UI Regression | Manual navigation all tabs | —/— | — |

### C.4 Verdykty per zadanie

| Zadanie | Verdict | Dowód |
|---------|:-------:|-------|
| B1-B3 (Theme) | ⬜ | |
| B4-B6 (Agent Status) | ⬜ | |
| B7-B8 (Task Picker) | ⬜ | |
| B9-B10 (Demo) | ⬜ | |
| B11 (UX Polish) | ⬜ | |

### C.6 Rekomendacja końcowa

- [ ] ✅ AKCEPTACJA — wszystkie weryfikacje manualne przechodzą
- [ ] ⚠️ WARUNKOWO — drobne uwagi do naprawy
- [ ] ❌ ODRZUCENIE — root cause analysis + odesłanie do /dev

---

## SEKCJA D — SECURITY (/sec)

> Status: ⚠️ CZĘŚCIOWA (Zgodnie z A.10)
> Scope: Wyłącznie nowy endpoint `GET /api/agent/status`

### Sprawdzenia

| # | Pytanie | Wynik | Uwagi |
|---|---------|:-----:|-------|
| D1 | Endpoint wymaga auth (`Depends(require_auth)`)? | ⬜ | |
| D2 | Czy zwraca wrażliwe dane? | ⬜ | Powinien zwracać tylko: status, task name, step, elapsed_s |
| D3 | Rate limiting potrzebny (polling co 3s)? | ⬜ | |

---

## SEKCJA E — DOKUMENTACJA (/doc)

> Wypełnia: `/doc` (PO /audyt i /sec)

### E.1 Pliki zaktualizowane

| Plik | Typ | Co zmieniono |
|------|-----|-------------|
| | | |

### E.2 Changelog

```markdown
## [2026-06-06] - UX-07: Premium GUI Redesign & Agent Observability

### Added
- Theme Engine (Light/Dark) z CSS Variables i localStorage persistence.
- Agent Status Panel (floating widget, polling `/api/agent/status`).
- Demo Tab z wizualizacjami ECharts.
- Rozbudowany Task Picker z rich-cards (projekt, status, priorytet).
- Favicon, meta tags, typed toasts.

### Changed
- Tab Bar: 5 zakładek (dodano Demo).
- `api.py`: nowy endpoint `GET /api/agent/status`.
- Task search endpoint: rozszerzone pola Odoo search_read.

### Removed
- (brak)
```

---

## SEKCJA F — LESSONS LEARNED

| # | Agent | Co poszło źle / dobrze | Co zmieniamy |
|---|-------|------------------------|-------------|
| 1 | | | |

---

## ✅ CLOSE CHECKLIST

- [ ] Sekcja F (Lessons Learned) ma min. 1 wpis
- [ ] Progress Bar — wszystkie klocki mają Status ✅
- [ ] Roadmap SmartMyOdoo zaktualizowana
- [ ] Oba motywy (jasny + ciemny) zweryfikowane wizualnie na każdym ekranie
- [ ] Endpoint `/api/agent/status` chroniony auth (Sekcja D potwierdzona)
