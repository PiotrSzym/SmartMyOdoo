---
sprint_id: "UX-10"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-17
closed: 2026-06-20
goal: "Panele danych (vault/secrets, audyt) ładują się niezawodnie po zalogowaniu i po reloadzie na dowolnej zakładce — koniec wyścigu load-before-auth bez retry; ujednolicony wzorzec auth-ready zamiast łatania per-komponent"
prefix: "UX"
complexity: 3
roadmap_ref: "SPIKE-002 (Auth Token Lifecycle UI); ujawnione przy UX-08 (persystencja activeTab)"
parent_sprint: null
tags: ["ux", "frontend", "vanilla-js", "auth", "race-condition", "bugfix", "dry"]
---

# 🧱 Sprint: UX-10 — Auth-ready loading (koniec 401-race)

> **Architekt:** /arch | **Owner:** /dev | **Review:** /gf-review | **Data:** 2026-06-17
> **Bazuje na:** main (`89fd8fc`) | **Recon:** [SPIKE-002](../spikes/SPIKE-002-Auth-Token-Lifecycle-UI-Components.md) | **ADR:** ADR-006 (Vanilla-JS)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch ✅)

### 0A. Business Discovery
- **Dla kogo?** Użytkownik aplikacji — po zalogowaniu / odświeżeniu oczekuje, że dane (Skarbiec, audyt) się pokażą.
- **Problem (1 zdanie):** komponenty strzelają po dane przed ustawieniem tokenu auth → 401 → `project.js` (vault) i `activity.js` (audyt) NIE ponawiają po zalogowaniu → puste panele; UX-08 (persystencja `activeTab`) wzmocnił to, bo reload ląduje wprost na zakładce, której render odpala się tylko na przejściu.
- **Metryka sukcesu:** reload będąc na Skarbcu → vault ładuje się (E2E); po `POST /api/auth` wszystkie panele danych populują się bez ręcznego klikania; zero osieroconych 401 (bez retry).
- **ROI:** usuwa „częsty" objaw psujący zaufanie do aplikacji; mały koszt (wzorzec, nie nowa architektura).
- **Źródło:** zgłoszenie użytkownika (2026-06-17) + SPIKE-002 (fakty zweryfikowane w kodzie).

### 0B. Fakty (z SPIKE-002, zweryfikowane plik:linia)
| Komponent | Ładuje | Retry po `isAuthenticated`? | Dowód |
|---|---|:--:|---|
| skills.js | `/api/skills` | ✅ | `skills.js:23-27` |
| sidebar.js | `/api/workspaces` | ✅ | `sidebar.js:18` |
| chat.js | `/api/chat/sessions` | ✅ | `chat.js:25` |
| **project.js (VAULT)** | `/api/secrets` | ❌ | `project.js:21-31` (tylko activeTab/workspaceId/lang) |
| **activity.js (audyt)** | `/api/audit` | ❌ | `activity.js:10-18` (brak isAuthenticated) |
- **Brak centralnego `authFetch`** — ręczny `Authorization: Bearer` w ~15 miejscach.
- **UX-08:** `activeTab` w `STORE_PERSIST_FIELDS` (localStorage); lazy-render na PRZEJŚCIU → przywrócona zakładka na starcie nie wyzwala renderu.

### 0C. User Stories
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-UX10-1 | użytkownik | by po zalogowaniu WSZYSTKIE panele danych same się załadowały | nie klikać ręcznie/odświeżać | KIEDY `POST /api/auth` zakończy się sukcesem TO vault (secrets) i audyt populują się bez interakcji |
| US-UX10-2 | użytkownik | by reload będąc na zakładce Skarbiec pokazał vault | nie tracić danych po odświeżeniu | KIEDY reload z przywróconą `activeTab='settings'` TO vault się renderuje (mimo braku zdarzenia przejścia) |
| US-UX10-3 | deweloper | jeden wzorzec auth-ready/`authFetch` | nie kopiować subskrypcji i nagłówków po komponentach | KIEDY dodaję nowy panel danych TO używam wspólnego helpera, a nie własnej logiki 401 |

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| Retry po auth (kanon) | `skills.js:23-27`, `sidebar.js:18`, `chat.js:25` | 📐 IN-PATTERN (rozszerzyć na project/activity) |
| Brak helpera fetch | ręczny `fetch(...,{headers:{Authorization}})` ×~15 | ⚠️ AD-HOC (wprowadzić `authFetch`) |
| Lazy render na przejściu | `project.js:22`, `activity.js` | ⚠️ AD-HOC (render też dla przywróconej zakładki po auth) |
| Store/Observer | `store.js` `setState/subscribe` | 📐 IN-PATTERN |

### 0E. Test Strategy
| Warstwa | Potrzebna? | Co testować | Kto | Narzędzie |
|---|:--:|---|:--:|---|
| E2E | ✅ | reload na Skarbcu → vault widoczny; login → panele populują; brak osieroconego 401 | /qa | Playwright (`tests/e2e/`, marker `e2e`) |
| Unit (jeśli infra) | ➖ | `authFetch` dokłada Bearer / obsługuje 401 | /dev | pokryć E2E |
| Regresja | ✅ | skills/sidebar/chat nadal ładują; pełna pytest 0 failed | /qa | pytest |

### 0F. US → E2E Mapping
| US | Scenariusz | Plik E2E | Priorytet |
|----|------------|----------|-----------|
| US-UX10-1 | login → secrets+audyt fetch po auth (200, nie osierocony 401) | `tests/e2e/test_auth_ready_loading_e2e.py` | 🔴 |
| US-UX10-2 | set activeTab=settings w localStorage → reload → vault state renderuje | `tests/e2e/test_vault_loads_on_reload_e2e.py` | 🔴 |
| US-UX10-3 | (kontrakt) data-loadery używają `authFetch`/retry-on-auth | review + e2e | 🟡 |

### 0G. Security Scope → Sekcja D (lekka)
Bez nowych endpointów. `authFetch` centralizuje `Authorization: Bearer` (token nadal tylko w pamięci, NIE localStorage — zgodnie z UX-08). `/sec` weryfikuje: helper nie loguje tokenu; brak osłabienia auth; 401 nie eksponuje danych.

### ⚖️ Zasady
- **ADR-006:** vanilla-JS, zero nowych zależności, wzorzec Observer.
- **Fix wzorca RAZ:** rozszerz kanon (retry-on-auth) na brakujące komponenty + wprowadź `authFetch` — NIE łataj punktowo bez wzorca.
- **Evidence Before Claims:** zacznij od czerwonego E2E reprodukującego pusty vault po reloadzie na Skarbcu.
- **NO SECRET IN localStorage / logach:** token w pamięci; `authFetch` go nie loguje.

---

## 🧱 Sekcja B — Podział Zadań (TDD: Red → Green) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| T1 | Centralny `authFetch(url, opts)` w NOWYM `ui/js/api.js`: dokłada `Authorization: Bearer` z `AppStore`, jednolita obsługa 401 (np. zwraca status do retry), NIE loguje tokenu. Załaduj w `index.html` PRZED komponentami (z `?v=`). | NEW `ui/js/api.js`, `ui/index.html` | wzór: ręczne fetch w komponentach | Unit/E2E: dokłada Bearer; 401 obsłużone | ✅ |
| T2 | **Retry-on-auth dla `project.js`** (vault): w subskrypcji dodać `if (newState.isAuthenticated && !oldState.isAuthenticated && activeTab==='settings') renderProjectTab()` (parytet ze `skills.js`/`sidebar.js`). | `ui/js/components/project.js` | `skills.js:23-27`, `sidebar.js:18` | E2E: login → secrets fetch 200, panel populuje | ✅ |
| T3 | **Retry-on-auth dla `activity.js`** (audyt): subskrypcja `isAuthenticated` → `loadFromAPI()` gdy zakładka aktywna. | `ui/js/components/activity.js` | `chat.js:25` | E2E: audyt ładuje po auth | ✅ |
| T4 | **Fix UX-08 interakcji:** po udanym auth wyrenderować PRZYWRÓCONĄ `activeTab` mimo braku zdarzenia przejścia (zrealizowane w T2/T3: retry-on-auth sprawdza `newState.activeTab` → render przywróconej zakładki bez zdarzenia przejścia; login handler bez zmian). | `ui/index.html` (login handler) lub komponenty | `project.js:22` (transition guard) | E2E: reload na Skarbcu → vault widoczny | ✅ |
| T5 | Migracja data-loaderów na `authFetch` (DRY) — project/activity w pełni zmigrowane (zero ręcznych `fetch(...,{Authorization})` w tych plikach) + brak osieroconych 401. | `ui/js/components/{project,activity}.js`, e2e | `api.js` (T1) | pełna suita bez regresji; e2e 0 osieroconych 401 | ✅ |

> **TDD /dev:** najpierw czerwony E2E „reload z `activeTab=settings` w localStorage → vault state NIE renderuje". Cache-bust: **zbumpuj `?v=` KAŻDEGO zmienionego JS** (lekcja UX-08 — pominięcie = poprawka niewidzialna w cache).

---

## 🛡️ Sekcja D — Security (/sec, lekka)
- [x] `authFetch` NIE loguje tokenu (console/logi); token nadal tylko w pamięci (nie localStorage). — zweryfikowane grepem: zero `console.*token/Bearer/authToken` w api.js/project.js/activity.js; `STORE_PERSIST_FIELDS` bez tokenu (UX-08).
- [x] Brak nowych endpointów; 401 nie eksponuje danych. — `authFetch` to wrapper na istniejące endpointy; e2e potwierdza 0 osieroconych 401.
- [x] Retry-on-auth nie tworzy pętli (guard na `!oldState.isAuthenticated`). — guard obecny w project.js i activity.js.

> ⚠️ Sekcja D oznaczona przez /dev jako self-check (Evidence). Formalna weryfikacja należy do `/sec` (handoff).

---

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review)
- [x] US-UX10-1: po `POST /api/auth` vault (secrets) i audyt populują się bez interakcji (E2E). — `test_auth_ready_loading_e2e.py` (secrets+audyt 200, 0 osieroconych 401).
- [x] US-UX10-2: reload na zakładce Skarbiec → vault renderuje (E2E). — `test_vault_loads_on_reload_e2e.py` + `test_audit_loads_on_reload_e2e.py` (marker `flex` = render JS).
- [x] US-UX10-3: project/activity używają wspólnego wzorca (`authFetch`/retry-on-auth); brak osieroconych 401. — zweryfikowane /sec + e2e.
- [x] Regresja: skills/sidebar/chat nadal ładują; pełna pytest 0 failed; cache-bust kompletny. — pytest **294 passed, 2 skipped, 0 failed**; e2e **11 passed, 0 failed**; cache-bust store v3/api v1/activity v2/project v8.
- [x] Sekcja D (/sec) ✅; ADR-006 (zero nowych zależności RUNTIME frontendu). — /sec 4/4; /gf-review potwierdził brak naruszenia ADR-006 (dodatki deps to korekta niedodeklarowanych manifestów backendu, nie nowy feature).

### Close Checklist
- [x] Zadania Sekcji B = ✅, status → `DONE`, `closed` (2026-06-20).
- [x] Lessons Learned (Sekcja F).
- [x] Zmergowane do `main`.

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa — wzorzec auth-ready, authFetch, interakcja z persystencją activeTab)

- **Wzorzec auth-ready RAZ, nie per-komponent.** Zamiast łatać 401-race punktowo, rozszerzono kanon retry-on-auth (`skills.js`/`sidebar.js`/`chat.js`) na `project.js`/`activity.js` + wprowadzono centralny `authFetch` (DRY, US-UX10-3). Guard `!oldState.isAuthenticated` jest obowiązkowy — bez niego subskrypcja `isAuthenticated` tworzy pętlę.
- **E2E muszą mierzyć EFEKT renderu JS, nie statyczny DOM.** Asercja `!hidden` była wydmuszką (`#project-state-1` startuje z `block`, więc `!hidden` spełnione bez renderu). Dowodowy marker to klasa `flex` dokładana wyłącznie przez `showState()` + network-spy (`401 not in statuses` ∧ `200 in statuses`).
- **Testy e2e nie mogą zakładać stanu danych dev-vaultu.** `test_project_tab_dual_state` twardo zakładał STAN 1, ale `default` jest związany z projektem (`project_ref='42'`) + globalny sekret `default_ODOO` → render = STAN 3. Naprawa: test inwariantu `showState` (dokładnie jeden stan `flex`), odporny na stan. UWAGA: `default_ODOO` jest GLOBALNY — STAN 1 nieosiągalny dopóki ten sekret istnieje.
- **Cold-start WSL2 na `/mnt/c` ≠ flaky produkt.** Pierwszy e2e w przebiegu odpala zimny start chromium+serwera (~44s cold start serwera); render-waity 8s i timeout LLM 10s były za ciasne → podbite do 12s/25s. To timing środowiska, nie regresja.
- **Token NIGDY do logów/localStorage.** `authFetch` zero `console.*`; `STORE_PERSIST_FIELDS` bez `authToken`; `store._redactedState()` maskuje token do `'***'` (ADR-011).

---

### Handoff
```
/arch (ten artefakt + SPIKE-002) ✅
   → /dev (authFetch + retry-on-auth project/activity + fix przywróconej zakładki, TDD, cache-bust!)
   → /sec (token nie w logach/localStorage)
   → /qa (reload-na-vault, login-populuje, brak osieroconych 401, regresja)
   → /gf-review (gate) → /doc (changelog)
```

> Po UX-10: „ładowanie przed auth bez retry" przestaje być klasą problemów — jeden wzorzec (`authFetch` +
> retry-on-auth) zamiast kopiuj-wklej; reload na dowolnej zakładce pokazuje dane.
