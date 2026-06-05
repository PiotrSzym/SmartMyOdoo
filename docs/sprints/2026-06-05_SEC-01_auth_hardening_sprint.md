# 🔒 Sprint: SEC-01 — Auth Hardening (Zamknięcie Luki Autoryzacji HUB-S3)

> **Architekt:** /arch | **Tryb:** Sequential | **Status:** "DONE"
> **Data:** 2026-06-05 | **Closed:** true | **Bazuje na:** Post-Review HUB-S3
> **Epic:** `docs/sprints/2026-06-05_EPIC-HUB_centrum_zarzadzania.md`
> **Wymaga:** ✅ HUB-S3 zakończone

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Zamknięcie luki bezpieczeństwa: 6 endpointów API (`/api/chat`, `/api/proposals/*`, `/api/workspaces`)
dodanych w HUB-S2 i HUB-S3 działa **bez autoryzacji**. Dowolny proces na localhost
może odpytać te endpointy nawet gdy sejf jest zablokowany. Frontend (`chat.js`, `sidebar.js`,
`index.html`) nie wysyła nagłówka `Authorization: Bearer ...` do tych endpointów.

### Root Cause Analysis

```
┌─────────────────────────────────────────────────────────┐
│  LUKA: 6 endpointów BEZ Depends(require_auth)          │
│                                                          │
│  Warstwa Backend (api.py):                               │
│  ├── POST /api/chat              — BRAK AUTH ❌          │
│  ├── GET  /api/proposals         — BRAK AUTH ❌          │
│  ├── POST /api/proposals/{id}/approve — BRAK AUTH ❌     │
│  ├── POST /api/proposals/{id}/reject  — BRAK AUTH ❌     │
│  ├── GET  /api/workspaces        — BRAK AUTH ❌          │
│  └── POST /api/workspaces        — BRAK AUTH ❌          │
│                                                          │
│  Warstwa Frontend (fetch bez headers):                   │
│  ├── chat.js:297    sendToAPI()          — BRAK ❌       │
│  ├── chat.js:333    handleProposalAction() — BRAK ❌     │
│  ├── sidebar.js:23  loadFromAPI()        — BRAK ❌       │
│  └── index.html:625 saveWorkspace()      — BRAK ❌       │
│                                                          │
│  Warstwa Testów (test_api.py):                           │
│  ├── L147-191  HUB-S2 testy czatu       — BRAK ❌       │
│  └── L207-319  HUB-S3 testy proposals/ws — BRAK ❌      │
│                                                          │
│  Endpointy POPRAWNE (z auth) — dla porównania:           │
│  ├── GET/POST/DELETE /api/secrets  ✅ Depends(require_auth)│
│  ├── POST /api/change-pin         ✅ Depends(require_auth)│
│  └── POST /api/auth, GET /api/status ✅ publiczne (OK)   │
└─────────────────────────────────────────────────────────┘
```

### Metryka sukcesu (DoD)
1. `curl -X POST localhost:8000/api/chat` (bez Bearer) → **401 Unauthorized**
2. `curl -X GET localhost:8000/api/workspaces` (bez Bearer) → **401 Unauthorized**
3. `pytest tests/test_api.py -v` → **ALL GREEN** (43 passed, 0 failed w scope HUB)
4. GUI: po zalogowaniu — Czat, Proposals i Sidebar działają normalnie z tokenem

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza 1 (Backend auth) → BRAMKA (curl 401) → Faza 2 (Frontend headers) → BRAMKA (GUI test) → Faza 3 (Testy)

#### Zasada 2: ZERO REGRESSION 🔴
Istniejące endpointy `/api/secrets` NIE mogą być dotknięte. Zmiany WYŁĄCZNIE w sygnaturach nowych endpointów.

#### Zasada 3: TOKEN FLOW 🟠
`currentAuth` (zmienna globalna w `index.html`) musi być dostępna dla komponentów `chat.js` i `sidebar.js`.
Przekazywanie przez `AppStore` (dodanie pola `authToken` do stanu globalnego).

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności

```
┌──────────────────────────────────────┐
│  FAZA 1 (Backend: Inject Auth)       │
│  [Depends(require_auth) na 6 endp.]  │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: curl bez Bearer → 401
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Frontend: Token Propagation)│
│  [AppStore.authToken + fetch headers]│
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: GUI login → czat + sidebar
               │           działają z tokenem
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (Testy: Headers Injection)   │
│  [headers={Bearer 1111} w testach]   │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Backend Auth Injection

> **📁 Scope:** `smartmyodoo/api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | `POST /api/chat` — dodaj `Depends(require_auth)` | Endpoint zwraca 401 bez tokena | [x] |
| 1.2 | `GET /api/proposals` — dodaj `Depends(require_auth)` | Endpoint zwraca 401 bez tokena | [x] |
| 1.3 | `POST /api/proposals/{id}/approve` — dodaj `Depends(require_auth)` | Endpoint zwraca 401 bez tokena | [x] |
| 1.4 | `POST /api/proposals/{id}/reject` — dodaj `Depends(require_auth)` | Endpoint zwraca 401 bez tokena | [x] |
| 1.5 | `GET /api/workspaces` — dodaj `Depends(require_auth)` | Endpoint zwraca 401 bez tokena | [x] |
| 1.6 | `POST /api/workspaces` — dodaj `Depends(require_auth)` | Endpoint zwraca 401 bez tokena | [x] |
| 1.7 | **BRAMKA:** curl test | ✅ `curl -s -o /dev/null -w "%{http_code}" localhost:8000/api/chat -X POST` → `401` | [x] |

---

### Sekcja B2 — FAZA 2: Frontend Token Propagation

> **📁 Scope:** `smartmyodoo/ui/js/store.js`, `smartmyodoo/ui/js/components/chat.js`, `smartmyodoo/ui/js/components/sidebar.js`, `smartmyodoo/ui/index.html`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | `store.js` — dodaj pole `authToken: ''` do stanu początkowego | `AppStore.getState().authToken` istnieje | [x] |
| 2.2 | `index.html` — `login()` po sukcesie robi `AppStore.setState({ authToken: pwd })` | Token zapisany w Store po zalogowaniu | [x] |
| 2.3 | `index.html` — `logout()` czyści `AppStore.setState({ authToken: '' })` | Token wyczyszczony po wylogowaniu | [x] |
| 2.4 | `chat.js:sendToAPI()` — dodaj `'Authorization': 'Bearer ' + AppStore.getState().authToken` | Czat wysyła token w nagłówku | [x] |
| 2.5 | `chat.js:handleProposalAction()` — dodaj nagłówek `Authorization` | Approve/Reject wysyła token | [x] |
| 2.6 | `sidebar.js:loadFromAPI()` — dodaj nagłówek `Authorization` | Lista workspace ładuje się z tokenem | [x] |
| 2.7 | `index.html:saveWorkspace()` — dodaj nagłówek `Authorization` | Tworzenie workspace wysyła token | [x] |
| 2.8 | **BRAMKA:** Visual test | ✅ Login → Czat działa → Sidebar ładuje → Workspace tworzenie → Proposals approve/reject | [x] |

---

### Sekcja B3 — FAZA 3: Test Suite Auth Headers

> **📁 Scope:** `tests/test_api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Dodaj fixture `auth_headers` zwracający `{"Authorization": "Bearer 1111"}` | Reużywalny fixture dla testów | [x] |
| 3.2 | HUB-S2: `test_chat_classifies_code_intent` — dodaj headers | Test przechodzi z auth | [x] |
| 3.3 | HUB-S2: `test_chat_classifies_db_intent` — dodaj headers | Test przechodzi z auth | [x] |
| 3.4 | HUB-S2: `test_chat_classifies_general_intent` — dodaj headers | Test przechodzi z auth | [x] |
| 3.5 | HUB-S3: `test_chat_generates_shadow_proposal` — dodaj headers | Test przechodzi z auth | [x] |
| 3.6 | HUB-S3: `test_proposals_crud` — dodaj headers do chat + proposals | Test przechodzi z auth | [x] |
| 3.7 | HUB-S3: `test_proposal_reject` — dodaj headers | Test przechodzi z auth | [x] |
| 3.8 | HUB-S3: `test_proposal_not_found` — dodaj headers | Test przechodzi z auth (ale 404) | [x] |
| 3.9 | HUB-S3: `test_workspaces_list` — dodaj headers | Test przechodzi z auth | [x] |
| 3.10 | HUB-S3: `test_workspace_create` — dodaj headers | Test przechodzi z auth | [x] |
| 3.11 | HUB-S3: `test_workspace_duplicate` — dodaj headers | Test przechodzi z auth (ale 400) | [x] |
| 3.12 | NOWY: `test_chat_requires_auth` — bez headers → 403 | Regresja: brak tokena = odrzucenie | [x] |
| 3.13 | NOWY: `test_proposals_requires_auth` — bez headers → 403 | Regresja: brak tokena = odrzucenie | [x] |
| 3.14 | NOWY: `test_workspaces_requires_auth` — bez headers → 403 | Regresja: brak tokena = odrzucenie | [x] |
| 3.15 | **BRAMKA:** `pytest tests/test_api.py -v` | ✅ ALL GREEN | [x] |

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Akcja | Oczekiwany wynik |
|---|-------|-------|------------------|
| V1 | Unit Tests | `pytest tests/test_api.py -v` | ✅ ALL GREEN |
| V2 | Regression: Auth Required | `curl -s -X POST localhost:8000/api/chat -H "Content-Type: application/json" -d "{}"` | ✅ 401/403 |
| V3 | Regression: Auth Passes | `curl -s -X GET localhost:8000/api/workspaces -H "Authorization: Bearer <pin>"` | ✅ 200 JSON |
| V4 | GUI Flow | Login → Chat → Proposal Approve → Workspace Create | ✅ Wszystko działa z tokenem |
| V5 | Konsola | DevTools → Console | ✅ Zero błędów 401 |

---

## 📐 Szczegóły Implementacji (Cheat Sheet)

### Backend — Wzorzec do zastosowania

```python
# PRZED (otwarty):
@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(req: ChatRequest):
    ...

# PO (zabezpieczony):
@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(
    req: ChatRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    ...
```

### Frontend — Wzorzec propagacji tokena

```javascript
// W store.js — nowe pole:
this.state = {
    workspaceId: 'default',
    activeTab: 'vault',
    authToken: ''   // ← NOWE
};

// W chat.js — sendToAPI():
headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${AppStore.getState().authToken}`
},

// W sidebar.js — loadFromAPI():
const token = AppStore.getState().authToken;
const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
const res = await fetch('/api/workspaces', { headers });
```

### Testy — Fixture

```python
@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer 1111"}
```
