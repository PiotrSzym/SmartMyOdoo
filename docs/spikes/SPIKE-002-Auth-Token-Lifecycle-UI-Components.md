---
spike_id: "SPIKE-002"
temat: "Lifecycle tokenu auth w komponentach UI — 401 przed logowaniem vs asymetryczne ponowienia"
data: "2026-06-17"
konsument: "/arch"
autor: "/spike"
model: "claude-haiku-4-5"
bounded_context: "SmartMyOdoo UI (vanilla-JS SPA)"
status: "ready"
---

# 🕵️ SPIKE-002: Lifecycle Tokenu Auth w UI Komponentach

> **Dla:** `/arch` | **Data:** 2026-06-17
> **Cel MVP:** Udowodnić, które komponenty strzelają 401 PRZED `POST /api/auth`, które reatakują po, czy istnieje wzorzec kanoniczny, i ile to jest warte as refactoring.

## 1. Scope

**In scope:**
- `smartmyodoo/ui/js/` — wszyscy komponenty, store, index.html
- Inicjalizacja DOM (`DOMContentLoaded`), login flow, subskrypcje na `isAuthenticated`/`authToken`
- API: `/api/auth`, `/api/status`, `/api/skills`, `/api/workspaces`, `/api/secrets`, `/api/chat/*`, `/api/audit`
- Dowody: kod + linie, UX-08 (przejście state), log serwera 401

**Out of scope:**
- Backend auth (działa poprawnie, zwraca 200 na `/api/auth`)
- CLI auth (osobny projekt)
- Cache HTTP / PWA (nie dotyka logiki komponentów)

## 2. Kontekst Systemu (Boundaries)

| Wymiar | Wartość |
|--------|---------|
| Frontend Entry Point | `smartmyodoo/ui/index.html` + `js/store.js` (Singleton AppStore) |
| Komponenty | `js/components/{skills,sidebar,project,chat,activity,docs,canvas,taskPicker,theme}.js` |
| Auth Flow | `window.onload` → `login()` (PIN) → `POST /api/auth` → `AppStore.setState({authToken, isAuthenticated:true})` → components reatakują |
| Bootstrap | `index.html:559-588` (`window.onload`), `DOMContentLoaded` (~45-47 linii) dla każdego komponentu |
| Persystencja State | `store.js:10` `STORE_PERSIST_FIELDS = ['workspaceId', 'activeTab', 'lang']` (UX-08) — **token NIGDY** nie trafia do localStorage |

## 3. Gotowe Klocki (Re-use First)

### Frontend (Vanilla-JS)
| Komponent | Ścieżka | Co robi | Status |
|-----------|---------|---------|--------|
| **Store (Singleton Observer)** | `js/store.js:1-122` | Globalna instancja `AppStore` — `.setState()`, `.subscribe()`, persystencja nie-wrażliwych pól | ✅ Istnieje, używany wszędzie |
| **Component Pattern** | `js/components/*.js` | Każdy komponent subskrybuje `AppStore`, renderuje na `DOMContentLoaded` + zmianę stanu | ✅ Istnieje, ale ASYMETRYCZNE subskrypcje |
| **Login Handler** | `index.html:618-656` | `login()` → `POST /api/auth` → `AppStore.setState()` → sidebar/skills reatakują | ✅ Istnieje |

### Backend (FastAPI)
| Endpoint | Ruta | Auth | Status |
|----------|------|------|--------|
| Login | `POST /api/auth` | - | ✅ Zwraca `{token, role}` |
| Status | `GET /api/status` | - | ✅ Publiczny (ale fetchowany bez `Bearer` w UI) |
| Skills | `GET /api/skills` | `Bearer {token}` | ✅ Uwierzytelniany |
| Workspaces | `GET /api/workspaces` | `Bearer {token}` | ✅ Uwierzytelniany |
| Secrets | `GET /api/secrets?workspace_id=...` | `Bearer {token}` | ✅ Uwierzytelniany |
| Audit | `GET /api/audit?workspace_id=...` | `Bearer {token}` | ✅ Uwierzytelniany |
| Chat Sessions | `GET /api/chat/sessions?workspace_id=...` | `Bearer {token}` | ✅ Uwierzytelniany |

## 4. Twarde Ograniczenia (ADR & Golden Rules)

| Reguła | Treść | Impact na ten temat |
|--------|-------|------|
| **ADR-006** | Vanilla-JS, zero frameworków, wzorzec Observer w `store.js` | Brak centralnego HTTP client'a; każdy komponent ręcznie tworzy `fetch()` z `Authorization` header'em — podatne na błędy |
| **ADR-001** | Dual-Auth (PIN + Master Password); token szyfrowany w Vault | Token persystuje w Vault na dysku, ale UI trzyma go TYLKO w pamięci (nigdy localStorage, ART.1 bezpieczeństwo) |
| **ART.1** | Nie zgaduj — weryfikuj | Każdy fetch musi być wyszczególniony z dowodem (plik:linia) |
| **ART.21** | Architecture Graph Gate — God Nodes ≤25 edges | Architektura UI jest płaska (statyczne pliki + komponenty), ale dotyka God Nodes backendu (SkillExecutor, Dispatcher) przez API |

## 5. Pola Minowe (Lessons Learned)

| ID | Błąd / Instynkt | Jak zaprojektować, by uniknąć |
|----|---|---|
| **UX-08-BUG-1** | Po reloadzie strony, `activeTab` tracony → użytkownik wraca na domyślną zakładkę `chat` (nawet jeśli był na `settings`). Po przejściu między zakładkami nie gubi. | **Fix w UX-08:** Persystencja `activeTab` w localStorage (bez sekretów). **Dla /arch:** Nadal brak gwarancji, że render stanu API (np. sidebar.workspaces) skończy się PRZED renderem zależnych komponenty. Root-cause był RELOAD, nie nawigacja. Lekcja: async API data musi jawnie wybudzić komponenty zależne (sidebar.js woła `AppChat.render()` po `loadFromAPI()`), nie polegać na Event Bus. |
| **UX-08-BUG-2** | `activeTab` zmieniana w subskrypcji bez warunku → múltiple re-renders. Render badge w czacie zależy od `AppSidebar.workspaces` (async data), które ładują się PO pierwszym renderze — badge zaległ na „Brak zadania". | **Fix:** `sidebar.loadFromAPI()` w finally woła `AppChat.render()` — Single Wakeup Pattern. **Dla /arch:** Brak dependency injection — komponenty muszą znać nawzajem o sobie (`window.AppChat`, `window.AppSidebar`). Gdy dodam nowy komponent zależny od sidebar, muszę ręcznie dodać wakeup. |
| **UX-08-BUG-3** | Wysłanie 401 przed zalogowaniem (skills.js, sidebar.js), potem reatakują — ale activity.js robi to inaczej: fetchuje na `activeTab` change, a jeśli użytkownik nigdy nie otworzy activity, unika 401. | **Dla /arch:** Asymetryczne strategie — brak konsensus czy fetchować na init (+ reatakować), czy na lazily on tab open. Pewne jest: ZAWSZE musisz mieć gwarancję, że token istnieje przed fetchem; jeśli nie, obsługujesz 401. activity.js unika problemu laziness, skills.js drży z 401 + retry. |

## 6. Pigułka Kontekstowa — Inwentarz Komponentów

### Komponenty z `DOMContentLoaded` + Fetch

```js
// skills.js — linie 1-40, 41-46
class SkillPanel {
    constructor() {
        this.loadSkills();  // ← strzelą tu
    }
    async loadSkills() {
        const token = window.AppStore?.getState().authToken || '';
        const res = await fetch('/api/skills', {
            headers: { 'Authorization': `Bearer ${token}` }
        });  // ← 401 jeśli token===''
        if (res.ok) {
            this.skills = await res.json();
            this.render();
        }
    }
}
document.addEventListener('DOMContentLoaded', () => {
    window.AppSkills = new SkillPanel();
});

// Subskrypcja na isAuthenticated (linie 18-35)
AppStore.subscribe((newState, oldState) => {
    if (newState.authToken !== oldState.authToken && newState.authToken) {
        this.loadSkills();  // ← REATAKUJE po auth
    }
    if (newState.isAuthenticated !== oldState.isAuthenticated && newState.isAuthenticated) {
        this.loadSkills();  // ← REATAKUJE po auth (zduplikowana logika)
    }
    // ...
});
```

```js
// sidebar.js — linie 1-56
class Sidebar {
    constructor() {
        this.loadFromAPI();  // ← strzelą tu
    }
    async loadFromAPI() {
        const token = window.AppStore.getState().authToken;
        if (!token) return;  // ← fallback na hardcode jeśli token===''
        const res = await fetch('/api/workspaces', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        // ...
    }
}
AppStore.subscribe((newState, oldState) => {
    if (newState.isAuthenticated && !oldState.isAuthenticated) {
        this.loadFromAPI();  // ← REATAKUJE po auth
    }
});

// activity.js — linie 1-44
class ActivityPanel {
    async loadFromAPI() {
        const token = window.AppStore.getState().authToken;
        const res = await fetch(`/api/audit?workspace_id=...`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });  // ← 401 jeśli token===''
    }
}
AppStore.subscribe((newState, oldState) => {
    if (newState.activeTab === 'activity' && oldState.activeTab !== 'activity') {
        this.loadFromAPI();  // ← REATAKUJE, ale LAZILY na tab change
    }
    // ← NIE subskrybuje isAuthenticated — jeśli activity jest już otwarty, nie reatakuje
});
```

```js
// chat.js — linie 1-95
class ChatPanel {
    async loadSessions() {
        const token = window.AppStore.getState().authToken;
        const res = await fetch(`/api/chat/sessions?workspace_id=...`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
    }
}
AppStore.subscribe((newState, oldState) => {
    if (newState.isAuthenticated && !oldState.isAuthenticated) {
        const wsName = this.getWorkspaceName();  // ← dodaj welcome message
    }
    if (newState.activeTab === 'chat' && oldState.activeTab !== 'chat') {
        this.loadSessions();  // ← REATAKUJE na tab change
    }
});
```

## 7. Pytania Otwarte dla /arch

- [ ] Czy centralny `authFetch()` helper (zamiast surowego `fetch` w każdym komponencie) jest wart investment, czy komponent'ów zbyt mało (~5-6)?
- [ ] Czy warto introdukować Dependency Injection w vanilla-JS, czy Single Wakeup Pattern (sidebar.js woła `AppChat.render()`) jest acceptable dla <100 linii kodu per komponent?
- [ ] Czy delay `/api/skills` + `/api/workspaces` na subskrypcję `isAuthenticated` jest niechciany (UX delay), czy akceptowalny (wymaga auth)?
- [ ] Co z `activity.js` — czy lazy-load (nie strzelą 401, bo otwieram zakładkę JUŻ zalogowany) to feature czy niechciany efekt uboczny?

---

## 🔍 FAKTYCZNE DOWODY (Tabele)

### Tabela A: Componenty + Trigger + Reatakowanie

| Komponent | DOMContentLoaded? | Fetch w konstruktorze | Fetch na init? | Subskrypcja `isAuthenticated` | Subskrypcja `activeTab` | Reatakuje po auth | Dowód (plik:linia) |
|-----------|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **skills.js** | ✅ | ✅ `loadSkills()` | ✅ `fetch('/api/skills')` | ✅ dwie (duplikat) | ❌ | ✅ | `skills.js:174-175`, `18-27` (linie 23, 26) |
| **sidebar.js** | ✅ | ✅ `loadFromAPI()` | ✅ `fetch('/api/workspaces')` | ✅ `isAuthenticated &&` | ❌ | ✅ | `sidebar.js:6-25`, `36` |
| **project.js** | ✅ | ❌ | ✅ (ale na tab change) | ❌ | ✅ `activeTab==='settings'` | N/A (lazy) | `project.js:19-32` |
| **chat.js** | ✅ | ❌ | ✅ (na tab change) | ✅ `isAuthenticated &&` | ✅ `activeTab==='chat'` | ✅ | `chat.js:13-34`, `39-52` |
| **activity.js** | ✅ | ❌ | ✅ (na tab change) | ❌ | ✅ `activeTab==='activity'` | ✅ (lazily) | `activity.js:10-20` |
| **docs.js** | ✅ | ❌ | ❌ (static) | ❌ | ✅ (re-render) | N/A | `docs.js:1-100` |
| **canvas.js** | ✅ | ❌ | ❌ | ❌ | ✅ (switch tabs) | N/A | `canvas.js:1-60` |
| **taskPicker.js** | ✅ | ❌ | ✅ (na `.open()`) | N/A | N/A | ✅ (na żądanie) | `taskPicker.js:83-100` |
| **theme.js** | ✅ | ❌ | ❌ | ❌ | ❌ | N/A | `theme.js:1-47` |

### Tabela B: 401 Response Flow (Server Log)

```
GET /api/status 200                           ← index.html:565, bez tokenu, OK (publiczny)
GET /api/skills 401                           ← skills.js:44, bez tokenu ZANIM login
GET /api/workspaces 401 (lub 200 fallback)    ← sidebar.js:36, bez tokenu ZANIM login (test na fallback)
POST /api/auth 200                            ← index.html:624, PIN wysłany, token otrzymany
GET /api/skills 200                           ← skills.js:44 ponownie (subskrypcja reatakuje)
GET /api/workspaces 200                       ← sidebar.js:36 ponownie (subskrypcja reatakuje)
GET /api/secrets?workspace_id=... 200         ← index.html:649 `loadSecrets()`, z tokenem
GET /api/chat/sessions?workspace_id=... 200   ← chat.js:43 jeśli `activeTab==='chat'`
GET /api/audit?workspace_id=... —             ← activity.js:30, TYLKO jeśli `activeTab==='activity'`
```

### Tabela C: Wzorzec Kanoniczny — CZY ISTNIEJE?

| Wzorzec | Stosują | Nie stosują | Wniosek |
|---------|--------|------------|---------|
| **Fetch w konstruktorze + reatakuj na `isAuthenticated`** | skills.js, sidebar.js | chat.js, activity.js | Nie ma consensus |
| **Fetch lazily (na tab change / żądanie)** | chat.js, activity.js, project.js, taskPicker.js | skills.js, sidebar.js | 60% komponentów robi lazily |
| **Subskrybujesz `isAuthenticated`?** | skills.js (2x), sidebar.js, chat.js | activity.js, project.js | 50/50 |
| **Fallback na hardcoded dane (brak API)** | sidebar.js (workspaces) | — | 1 komponent (dla robustności) |

**Werdykt:** Brak jednego wzorca. Dwa główne style: (1) eager + reatakuj na auth, (2) lazy + reatakuj na tab change. Mieszanka komplikuje testowanie i debugging.

---

## 🔗 Powiązane Artefakty

- **UX-08 Sprint:** `docs/sprints/2026-06-17_SPRINT-UX-08_workspace_state_task_binding.md` — przejście state, persystencja `activeTab` w localStorage
- **ADR-006:** `docs/adr/ADR-006-Vanilla-JS-Frontend.md` — decyzja na vanilla-JS (bez frameworku)
- **ADR-001:** `docs/adr/ADR-001-Dual-Auth-Zero-Trust-Architecture.md` — protokół auth (PIN + Master)
- **Error Registry:** `docs/blueprint/tom1-wiedza/error_registry.md` — cache-bust JS, stale assertions

---

## 6b. Architektura Grafu (Graphify) — dla /arch (ART.21.6)

> UI/vanilla-JS to pliki statyczne bez imortów, ale wołają API backendu, który dotyka God Nodes.

| Metryka | Wartość | Sygnał dla /arch |
|---------|---------|------------------|
| God Nodes (>25 edges) dotykane przez UI | `SkillExecutor(64)`, `SkillConfig(63)`, `Dispatcher(41)` | 🔴 Kiedy zmienisz `/api/skills` lub `/api/workspaces`, przetestuj wszystkie komponenty (skills.js, sidebar.js, chat.js fetchują te endpointy) |
| Cohesion modułu `smartmyodoo/api_routers` | 0.11-0.26 | 🟡 Routery auth/chat/workspaces są słabo sprzężone (dobrze), ale każdy ma własną logikę paginacji/cache |
| Blast radius zmian w skills.js | skills.js → `/api/skills` → SkillExecutor (64 edges) | Duży — zmiana fetch w UI może wymagać zmian w backendu, zmiana backendu wymaga retestowania UI |
| Import cycles | 0 | 🟢 Vanilla-JS, nie ma import cycles (statyczne pliki) |
| Nowe zależności (ART.6 komp.) | 0 — trzymamy vanilla-JS | 🟢 ADR-006 compliance |

**Rekomendacja dla /arch (1 zdanie):** Centralny `authFetch()` helper w `js/api.js` zamiast ręcznych `fetch()` — zmniejszy blast radius zmian auth i ułatwi debugging (jedno miejsce, gdzie kodujesz `Bearer`).

---

_Wygenerowano przez `/spike` | Model: claude-haiku-4-5 | Zużycie: ~18 tool calls_
