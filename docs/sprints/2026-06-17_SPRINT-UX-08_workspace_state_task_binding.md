---
sprint_id: "UX-08"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-17
closed: 2026-06-17
goal: "Workspace pamięta swój stan między zakładkami/odświeżeniem (BUG-1) oraz w nagłówku czatu widać, do jakiego projektu/zadania logują się godziny — z możliwością zmiany zadania bez wchodzenia w zakładkę Projekt"
prefix: "UX"
complexity: 3
roadmap_ref: "SPIKE-001 (Workspace State & Task Picker); helpdesk = osobny sprint UX-09 (Enterprise potwierdzony)"
parent_sprint: null
tags: ["ux", "frontend", "vanilla-js", "workspace", "timesheet", "task-binding", "bugfix"]
---

# 🧱 Sprint: UX-08 — Stan workspace + zadanie w nagłówku czatu

> **Architekt:** /arch | **Owner:** /dev | **Review:** /gf-review | **Data:** 2026-06-17
> **Bazuje na:** main (`131e5e6`) | **Recon:** [SPIKE-001](../spikes/SPIKE-001-Workspace-State-Task-Picker.md) | **ADR:** ADR-006 (Vanilla-JS-Frontend)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch ✅)

### 0A. Business Discovery
- **Dla kogo?** Użytkownik pracujący w wielu workspace'ach (każdy = inny projekt Odoo), logujący czas pracy.
- **Problem (1 zdanie):** nawigacja między zakładkami / odświeżenie gubi aktywny workspace, a użytkownik nie widzi w czacie, do jakiego zadania logują się jego godziny ani nie może go tam zmienić.
- **Metryka sukcesu:** po przejściu do innej zakładki i powrocie (oraz po reloadzie) aktywny workspace zachowany (test); w nagłówku czatu widoczne `Projekt › Zadanie`; zmiana zadania z czatu zapisuje się (PUT `/task_bind`) bez wchodzenia w zakładkę Projekt.
- **ROI:** mniej frustracji i błędów (logowanie godzin do złego zadania); szybszy flow. Niski koszt — backend już gotowy.
- **Źródło:** zgłoszenie użytkownika (sesja 2026-06-17) + SPIKE-001.

### 0B. User Stories (baza E2E)
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-UX8-1 | użytkownik wielu workspace'ów | by aplikacja pamiętała aktywny workspace między zakładkami i po odświeżeniu | nie tracić kontekstu pracy | KIEDY wejdę w „Projekt" i wrócę (lub odświeżę stronę) TO nadal jestem w tym samym workspace |
| US-UX8-2 | osoba logująca czas | widzieć w nagłówku czatu, do jakiego **projektu › zadania** pójdą godziny | mieć pewność, gdzie loguję | KIEDY jestem w workspace z przypisanym zadaniem TO nagłówek czatu pokazuje `Projekt X › Zadanie Y` |
| US-UX8-3 | osoba logująca czas | zmienić zadanie bezpośrednio z czatu | nie przełączać się do zakładki Projekt | KIEDY kliknę „Zmień" przy zadaniu w czacie TO otwiera się Task Picker i wybór zapisuje się w workspace (PUT `/task_bind`) |

### 0C. Skills Audit (scope = FRONTEND vanilla-JS + lekki backend read)
- **Stack:** vanilla-JS micro-SPA (Observer `Store`), FastAPI (router workspaces gotowy), Tailwind (CDN), Lucide. **Bez frameworka** (ADR-006).
- **Skille:** `@webapp-testing` / `@playwright-e2e` (testy UI), `@systematic-debugging` (BUG-1 root-cause).
- **Reguła ADR-006:** zero nowych zależności frontendowych; trzymać wzorzec Observer + komponenty `js/components/`.

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| Globalny stan | `ui/js/store.js` `Store` (Observer, in-memory) | ⚠️ AD-HOC (dodać persystencję localStorage) |
| Górne zakładki | `index.html` `onclick="AppStore.setState({activeTab:'…'})"` | 📐 IN-PATTERN |
| Subskrypcja re-render | `components/*.js` `AppStore.subscribe((new,old)=>…)` | 📐 IN-PATTERN |
| Task Picker | `components/project.js` STAN 3 (`loadProjectTasks`, `bindProjectToWorkspace`, `active-task-name`) | 📐 IN-PATTERN (wyekstrahować do reużycia) |
| Bind zadania | PUT `/api/workspaces/{ws}/task_bind` + GET `/tasks/search` | 📐 IN-PATTERN (gotowe API) |
| Nagłówek czatu | `components/chat.js` `render()` | 📐 IN-PATTERN (dodać badge) |

### 0E. Test Strategy
| Warstwa | Potrzebna? | Co testować | Kto | Narzędzie |
|---|:--:|---|:--:|---|
| E2E | ✅ | persystencja ws (nav+reload); badge pokazuje project/task; zmiana zadania z czatu zapisuje bind | /qa | Playwright (wzór: `tests/*_e2e.py`, marker `e2e`) |
| Unit (JS, jeśli infra) | ✅/➖ | `Store.setState/getState` roundtrip localStorage | /dev | jeśli brak runnera JS → pokryć E2E |
| Regresja | ✅ | istniejące e2e (`test_chat_e2e`, `test_project_tab_e2e`) zielone; pełna pytest bez regresji | /qa | pytest |

### 0F. US → E2E Mapping
| US | Scenariusz | Plik E2E | Priorytet |
|----|------------|----------|-----------|
| US-UX8-1 | wybierz ws → zakładka Projekt → powrót/reload → ws zachowany | `tests/test_workspace_persistence_e2e.py` | 🔴 |
| US-UX8-2 | ws z task_ref → nagłówek czatu pokazuje `project_name › task_name` | `tests/test_chat_task_badge_e2e.py` | 🔴 |
| US-UX8-3 | „Zmień" w czacie → Task Picker → wybór → PUT task_bind → badge zaktualizowany | `tests/test_chat_task_change_e2e.py` | 🟡 |

### 0G. Security Scope → Sekcja D (lekka)
Brak nowych endpointów/sekretów (reużycie istniejących, uwierzytelnionych `Bearer`). `localStorage` trzyma TYLKO `workspaceId`/`activeTab`/`lang` — **NIE** token ani sekrety (token zostaje w pamięci jak dziś). `/sec` weryfikuje: zero PII/sekretów w localStorage; XSS przy wstrzykiwaniu `project_name`/`task_name` do DOM (escaping).

### ⚖️ Zasady
- **ADR-006:** vanilla-JS, zero nowych zależności frontu, wzorzec Observer.
- **Evidence Before Claims:** BUG-1 zaczyna od **czerwonego E2E** reprodukującego utratę stanu (ustal: nav czy reload czy oba).
- **NO SECRET IN localStorage:** persystujemy tylko nie-wrażliwy stan UI.
- **DRY:** Task Picker z `project.js` wyekstrahowany, nie skopiowany.

---

## 🧱 Sekcja B — Podział Zadań (TDD: Red → Green) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| T1 (BUG-1) | Persystencja stanu UI: `Store.setState` zapisuje `workspaceId`/`activeTab`/`lang` do `localStorage`; konstruktor czyta fallback z `localStorage` (NIE token/sekrety). Najpierw czerwony E2E reprodukujący utratę (nav→powrót i reload). | `ui/js/store.js`, `tests/e2e/test_workspace_persistence_e2e.py` | `store.js:8-18,31-36` | E2E: po nav i po reload ws zachowany | ✅ |
| T2 | Badge w nagłówku czatu: `📋 {project_name} › {task_name}` (z workspace; gdy brak zadania → „Brak zadania"); aktualizacja na zmianę `workspaceId`. Escaping wartości (XSS). | `ui/js/components/chat.js`, `ui/js/components/sidebar.js`, `ui/js/i18n.js` | `chat.js:render()`, `project.js:63` | E2E: badge pokazuje project/task dla ws z bindem | ✅ |
| T3 | Przycisk „Zmień" w nagłówku → otwiera **wyekstrahowany Task Picker** (z `project.js` STAN 3) → wybór → PUT `/task_bind` → badge i workspace zaktualizowane. | `ui/js/components/chat.js`, `ui/js/components/project.js` (extract), nowy `ui/js/components/taskPicker.js` | `project.js:215-253` (`bindProjectToWorkspace`, `loadProjectTasks`) | E2E: zmiana zadania z czatu zapisuje bind, badge odświeżony | ✅ |
| T4 | Testy dowodowe (komplet) + brak regresji istniejących e2e | `tests/e2e/*_e2e.py` | wzór: `test_project_tab_e2e.py` | pełna suita bez regresji | ✅ |

> **Uwaga /dev:** najpierw przypnij **dokładny** punkt utraty stanu (czerwony E2E) — czy to reload, czy reset przy nav. `localStorage` pokrywa reload pewnie; jeśli istnieje też reset przy nav, napraw źródło. Task Picker **wyekstrahuj** (DRY) — nie duplikuj logiki z `project.js`.

---

## 🛡️ Sekcja D — Security (/sec, lekka)
- [x] `localStorage` zawiera TYLKO `workspaceId`/`activeTab`/`lang` — **nie** `authToken` ani sekrety. Egzekwowane whitelistą `STORE_PERSIST_FIELDS` w `store.js` (zarówno `_persist()` jak i `_loadPersisted()` filtrują pola → nawet zatruty storage nie wstrzyknie obcych kluczy). /dev potwierdza; finalna weryfikacja → /sec.
- [x] `project_name`/`task_name` wstrzykiwane do DOM z **escapingiem** — badge w `chat.js` używa `_escapeHtml` (textContent→innerHTML); `taskPicker.js` używa `_escape` (ten sam wzorzec). Argumenty `onclick` dodatkowo neutralizują apostrof (jak w `project.js`).
- [x] Brak nowych endpointów; reużycie uwierzytelnionych (`Bearer`) — GET `/api/workspaces`, GET `/projects/{id}/tasks`, PUT `/task_bind`.

---

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review)
- [x] US-UX8-1: po nav między zakładkami i po reloadzie aktywny workspace zachowany (E2E). ✅
- [x] US-UX8-2: nagłówek czatu pokazuje `Projekt › Zadanie` z workspace (E2E). ✅
- [x] US-UX8-3: zmiana zadania z czatu zapisuje bind (PUT `/task_bind`) i odświeża badge (E2E). ✅
- [x] Brak regresji UX-08: pełna pytest 314 passed; 1 failed PRE-EXISTING poza scope (docs stale-assertion, identyczny na baseline). ⚠️
- [x] Sekcja D (/sec) ✅ zweryfikowana dowodowo (XSS/poison/leak); zero nowych zależności frontu (ADR-006). ✅

### Verdykt /qa (2026-06-17) — Evidence-Based
> **WERDYKT: ✅ PASS (z 1 uwagą poza scope).** Wszystkie 5 nowych E2E uruchomione REALNIE (chromium, żywy serwer :8000) i zielone. Bug-hunt: 3/3 edge cases obronione. Jedyny failed test (`test_docs_tab_renders_content`) jest pre-existing, niezwiązany z UX-08 (dowód: `docs.js` identyczny na baseline `131e5e6`).

| Zadanie / US | Verdict | E2E Status | Dowody (output) | Uwagi |
|---|:--:|:--:|---|---|
| US-UX8-1 (persystencja: nav + reload) | ✅ | REAL PASS | `test_workspace_persistence_e2e.py`: **2 passed in 9.34s** (`test_..._across_tab_navigation` + `test_..._across_reload`) | Root-cause /dev potwierdzony: nav PASS przed fixem (żaden subskrybent nie resetuje wsId), reload był bugiem → naprawiony persystencją localStorage (`store.js:_persist/_loadPersisted`, whitelist `STORE_PERSIST_FIELDS`). |
| US-UX8-2 (badge `Projekt › Zadanie`) | ✅ | REAL PASS | `test_chat_task_badge_e2e.py`: **2 passed** (bound: separator `›` + project/task; unbound `dev`: „Brak zadania") | Render-race fix zweryfikowany: `sidebar.js:loadFromAPI()` woła `AppChat.render()` w `finally`. Badge zależy od `AppSidebar.workspaces` (SSoT). |
| US-UX8-3 (zmiana zadania z czatu) | ✅ | REAL PASS | `test_chat_task_change_e2e.py`: **1 passed** (klik „Zmień" → `#task-picker-overlay` → PUT `/task_bind` → `task_ref` zmienione → badge `›`) | DRY potwierdzone: `taskPicker.js` (`AppTaskPicker.loadTasks/bind/open`); `project.js:loadProjectTasks`/`bindTaskFromPicker` DELEGUJĄ (brak duplikacji fetch+PUT). |
| Regresja (pełna pytest bez e2e) | ⚠️ | — | `pytest -q`: **314 passed, 1 failed, 7 deselected** (217s). Failed: `test_ui_docs_render.py::test_docs_tab_renders_content` `assert 9 == 8`. | **POZA SCOPE UX-08.** `docs.js` IDENTYCZNY vs baseline `131e5e6` (`git diff` pusty); sekcja „share" (9. sekcja) z SHARE-01. Test failuje też na baseline. Koryguje raport /dev („0 failed" → realnie 1 failed). Wpis do error_registry. |
| Bug-hunt (edge cases) | ✅ | REAL PASS | skrypt `bughunt.py` na :8000 (chromium) | Patrz tabela bugów poniżej — 0 bugów, 3/3 obronione. |
| Sekcja D / Security | ✅ | REAL PASS | BH2: zatruty LS z `authToken`/`isAuthenticated`/`evilKey` → state po reloadzie czysty (`authToken=''`, `isAuthenticated=false`, brak `evilKey`) — whitelist działa. BH3: `<img onerror>` / `<script>` w nazwie → `__XSS_FIRED=false`, brak `<img>` w DOM, encoded `&lt;img&gt;`. | Zero PII/sekretów w localStorage; escaping XSS skuteczny (`_escapeHtml`/`_escape` textContent→innerHTML). |

#### Bug-Hunt — repro i wynik (0 bugów)
| # | Atak | Repro | Oczekiwane | Wynik | Verdict |
|---|---|---|---|---|---|
| BH1 | Workspace w localStorage NIE istnieje (`ghost-ws-99999`) | set LS → login | App nie sypie się; sidebar renderuje; badge „Brak zadania" | `pageerrors=[]`, `sidebar_rendered=True`, badge=„📋 Brak zadania Zmień" | ✅ obroniony |
| BH2 | localStorage zatruty `authToken`/`isAuthenticated:true`/`evilKey` | set LS → reload | Tylko whitelist `workspaceId/activeTab/lang`; sekrety odrzucone | state=`{workspaceId:"dev",activeTab:"chat",authToken:"",isAuthenticated:false,lang:"pl"}` — leak=False | ✅ obroniony |
| BH3 | XSS przez `project_name`/`task_name` (`<img onerror>`,`<script>`) | inject ws → `AppChat.render()` | Brak wykonania JS; treść escaped | `__XSS_FIRED=false`, `<img> injected=False`, innerHTML=`&lt;img src=x onerror...&gt;` | ✅ obroniony |

### Close Checklist
- [x] Zadania Sekcji B = ✅, status → `DONE`, `closed` ustawione.
- [x] Lessons Learned (Sekcja F) uzupełnione (/dev + /qa + /sec + /gf-review + /doc).
- [x] Zmergowane do `main` (po /gf-review APPROVE).

### 🏆 Verdykt /gf-review — 2026-06-17, baza `131e5e6`
**APPROVE** — 9/9 faz, zero 🔴/🟡. Adwersarialnie potwierdzone: XSS-fix szczelny (delegation + `data-*`, `escapeAttr` koduje `"`), persystencja z whitelistą (token nie wyciekł), **cache-bust kompletny** (wszystkie 6 zmienionych JS zbumpowane). Suita 315 passed / 0 failed (docs stale-assertion naprawiony 8→9). 4 findings LOW poza scope: pliki untracked (git add przy mergu), PIN fixtures (1234 vs 1111), martwy `task-search-modal`/`bindTask()` w index.html, /doc pending.

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa — dokładny root-cause BUG-1, ekstrakcja Task Pickera, e2e dla vanilla-JS)

### /dev (2026-06-17)
- **BUG-1 root-cause = RELOAD, nie nawigacja (dowód E2E).** Czerwony E2E rozdzielił dwa scenariusze: `test_workspace_persists_across_tab_navigation` **PASSED** już przed naprawą (nawigacja chat↔Projekt NIE rusza `workspaceId` — żaden subskrybent go nie resetuje), a `test_workspace_persists_across_reload` **FAILED** z `assert 'default' == 'dev'`. Przyczyna: `window.AppStore = new Store()` przy każdym (prze)ładowaniu tworzy świeżą instancję z hardkodowanym `workspaceId:'default'` — zero persystencji. Fix: whitelistowana persystencja `workspaceId`/`activeTab`/`lang` w localStorage (`smartmyodoo.ui`), odczyt w konstruktorze. Hipoteza SPIKE o „race condition w renderze project.js" okazała się nietrafna — utrata jest czysto reload-driven.
- **Render-race badge (T2):** badge zależy od `AppSidebar.workspaces`, które ładują się async PO pierwszym renderze czatu. Klik na *już aktywny* workspace nie odpala re-renderu czatu (`workspaceId` bez zmiany), więc badge zostawał na „Brak zadania". Fix: `Sidebar.loadFromAPI()` po (prze)ładowaniu woła `window.AppChat.render()` — pojedynczy punkt odświeżenia, bez nowych subskrypcji. Lekcja: dane z API ładowane async muszą jawnie wybudzić komponenty zależne, nie polegać tylko na zdarzeniach zmiany stanu.
- **DRY Task Picker (T3):** wyekstrahowano wspólny `taskPicker.js` (`window.AppTaskPicker.loadTasks/bind/open`); `project.js` (`loadProjectTasks`, `bindTaskFromPicker`) deleguje doń zamiast duplikować fetch+PUT. Uwaga na przyszłość: stary inline `bindTask()` w `index.html` (modal `#task-search-modal`) wysyła niepełny payload (`task_ref`/`task_name` bez `project_ref`/`project_name`, wymaganych przez Pydantic) i odwołuje się do nieistniejących `#settings-task-ref` — **martwy/wadliwy kod, kandydat do usunięcia w osobnym sprincie** (poza scope UX-08, nie ruszany).
- **E2E vanilla-JS:** brak runnera JS unit → pokrycie przez Playwright (zgodnie z 0E). Wspólny `login_to_dashboard`/`select_workspace` w `tests/e2e/conftest.py` + `tests/e2e/__init__.py` (subpakiet) usuwa duplikację i wyścig „is_visible() przed renderem ekranu". Cache-busting JS przez bump `?v=` w `index.html`.

---

### /sec + /gf-review (2026-06-17)
- **Stored-XSS przez atrybut `onclick` (złapany przez /sec, przeoczony przez /qa).** Nazwa zadania/projektu z Odoo interpolowana do `onclick="fn('...')"` — `escape` (textContent→innerHTML) NIE koduje `"`, więc nazwa z `"` robi breakout z atrybutu i wstrzykuje handler. /qa testował tylko badge (text-node, bezpieczny), nie picker (atrybut). **Fix strukturalny > escaping:** porzucono inline `onclick` na rzecz **event delegation + `data-*`** (`dataset` zwraca zdekodowany string bez kontekstu HTML/JS — likwiduje całą klasę). Naprawiono w `taskPicker.js` i `project.js` (ta sama pre-existing słabość). Lekcja: dane zewnętrzne w atrybucie `onclick` to nested-context (HTML+JS) — escaping jest kruchy, delegacja przez `data-*` jest poprawna.
- **Cache-bust niekompletny = poprawka „niewidzialna" (złapane przez użytkownika, NIE przez e2e).** `store.js` (plik z całą poprawką persystencji) został pominięty przy bumpie `?v=` w `index.html` → realna przeglądarka serwowała STARY plik z cache, bug trwał mimo zielonych e2e. Playwright startuje świeży browser bez cache, więc tego NIE wykrył. **Lekcja:** (1) każdy zmieniony plik JS MUSI dostać bump `?v=` — to ręczne i podatne, kandydat na auto-cache-bust; (2) e2e ze świeżym browserem nie testują ścieżki cache — rozważyć test serwujący ze starym `?v=`. Objaw u usera (numery linii `store.js:34/45` ze starego pliku) był kluczowym dowodem.

### Handoff
```
/arch (ten artefakt + SPIKE-001) ✅
   → /dev (T1 persystencja, T2 badge, T3 zmiana zadania, E2E)
   → /sec (localStorage bez sekretów + XSS escaping)
   → /qa (persystencja nav+reload, badge, zmiana zadania, brak regresji)
   → /gf-review (gate) → /doc (changelog + ewent. panel)
```

> Następny sprint (UX-09, osobny): **helpdesk** — `task_source` (project_task | helpdesk_ticket), capability-check modułu, `helpdesk_ticket_id` na `account.analytic.line`. Enterprise potwierdzony przez użytkownika → wykonalne.
