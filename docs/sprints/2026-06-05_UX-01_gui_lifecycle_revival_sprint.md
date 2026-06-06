# 🩺 Sprint: UX-01 — GUI Lifecycle Revival (Naprawa Martwego Interfejsu)

> **Architekt:** /arch | **Tryb:** Sequential (4 Fazy + 4 Bramki)
> **Data:** 2026-06-05 | **Bazuje na:** Live-server audit na porcie 8000
> **Epic:** `docs/sprints/2026-06-05_EPIC-HUB_centrum_zarzadzania.md`
> **Wymaga:** ✅ SEC-01 zakończone

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Interfejs SmartMyOdoo HUB po zalogowaniu jest "martwy": Sidebar pokazuje mockowane
dane (401 na `/api/workspaces` zanim użytkownik wpisze PIN), Czat to pusta czarna
dziura bez żadnej interakcji, zakładka Ustawienia to placeholder. Użytkownik widzi
pusty ekran i myśli, że aplikacja jest zepsuta.

### Root Cause Analysis

```
┌────────────────────────────────────────────────────────────┐
│  12 BUGÓW W 4 KATEGORIACH                                  │
│                                                             │
│  🔴 Lifecycle Desync (3 bugi):                              │
│  ├── BUG-01: sidebar.js ładuje dane PRZED logowaniem       │
│  │           → 401 → fallback na mockowane workspaces       │
│  ├── BUG-02: Brak ochrony przed podwójnym login()          │
│  └── BUG-03: Store nie ma pola isAuthenticated              │
│                                                             │
│  🟡 Dead UI (3 bugi):                                       │
│  ├── BUG-04: Czat pusty — brak wiadomości powitalnej       │
│  ├── BUG-05: Ustawienia = placeholder <p>                  │
│  └── BUG-06: getWorkspaceName() hardcoded mapa nazw        │
│                                                             │
│  🟠 Security Gaps (2 bugi):                                 │
│  ├── BUG-07: Odoo addon "Bearer 1111" hardcoded            │
│  └── BUG-08: currentAuth = globalny PIN w window scope     │
│                                                             │
│  🔵 Architecture Anti-Patterns (4 bugi):                    │
│  ├── BUG-09: /api/chat reply = surowy debug string         │
│  ├── BUG-10: workspaces/proposals in-memory (restart=lost) │
│  ├── BUG-11: vault-screen nie w tablicy tabs canvas.js     │
│  └── BUG-12: Brak loading/error states                     │
└────────────────────────────────────────────────────────────┘
```

### Metryka sukcesu (DoD)
1. Login → Sidebar **natychmiast** pobiera workspaces z API (nie mockowane dane)
2. Login → Czat wyświetla **proaktywną wiadomość powitalną** agenta
3. Zakładka Ustawienia → **formularz konfiguracji workspace** (nazwa, URL Odoo)
4. Przełączanie zakładek (Vault ↔ Chat ↔ Ustawienia) → **poprawne ukrywanie/pokazywanie**
5. `currentAuth` **wyeliminowany** — wyłącznie `AppStore.getState().authToken`
6. `pytest tests/test_api.py -v` → **ALL GREEN** (zero regresji)
7. DevTools Console → **zero błędów JS** po pełnym flow

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE 🔴
Faza 1 (Lifecycle) → BRAMKA → Faza 2 (Dead UI) → BRAMKA → Faza 3 (Security) → BRAMKA → Faza 4 (Persistence)

#### Zasada 2: ZERO REGRESSION 🔴
Istniejące endpointy i testy z SEC-01 NIE mogą być dotknięte. Zmiany wyłącznie w scope poniżej.

#### Zasada 3: SCOPE ISOLATION 🔴
- **Frontend:** `store.js`, `index.html`, `sidebar.js`, `canvas.js`, `chat.js`
- **Backend:** `api.py` (nowe endpointy + reply improvement)
- **Odoo Addon:** `custom_addons/smart_chat/controllers/main.py` (tylko token fix)
- **Testy:** `tests/test_api.py` (wyłącznie nowe testy, nie modyfikacja istniejących)

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności

```
┌──────────────────────────────────────┐
│  FAZA 1 (Lifecycle Fix)              │
│  [Store isAuthenticated]             │
│  [Sidebar reload po login]           │
│  [Eliminacja podwójnego login]       │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Login → Sidebar
               │           pobiera z API (nie mock)
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Dead UI Revival)            │
│  [Wiadomość powitalna czatu]         │
│  [Formularz Ustawień]                │
│  [Canvas tabs fix]                   │
│  [Naturalny reply zamiast debug]     │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Wszystkie 3 zakładki
               │           żyją i renderują content
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (Security Cleanup)           │
│  [Eliminacja currentAuth]            │
│  [Odoo addon token fix]             │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Zero hardcoded
               │           credentials w codebase
               ▼
┌──────────────────────────────────────┐
│  FAZA 4 (Persistence & Polish)       │
│  [Workspaces/Proposals → SQLite]     │
│  [Loading states]                    │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Lifecycle Fix

> **📁 Scope:** `store.js`, `index.html`, `sidebar.js`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | `store.js` — dodaj `isAuthenticated: false` do initial state | Pole istnieje, komponenty mogą subskrybować | [x] |
| 1.2 | `index.html:login()` — po sukcesie: `AppStore.setState({ isAuthenticated: true, authToken: pwd })` | Token + flaga ustawione atomowo | [x] |
| 1.3 | `index.html:login()` — po sukcesie: `if (window.AppSidebar) window.AppSidebar.loadFromAPI()` | Sidebar odświeża się natychmiast po logowaniu | [x] |
| 1.4 | `index.html:login()` — dodaj flagę `isLoggingIn` chroniącą przed podwójnym wywołaniem | Drugie kliknięcie / Enter podczas trwania login() jest ignorowane | [x] |
| 1.5 | `index.html:logout()` — `AppStore.setState({ isAuthenticated: false, authToken: '' })` | Czyszczenie stanu przy wylogowaniu | [x] |
| 1.6 | `sidebar.js` — nie wywoływać `loadFromAPI()` w konstruktorze bez tokenu | Konstruktor sprawdza `AppStore.getState().authToken` przed fetch | [x] |
| 1.7 | `sidebar.js` — subskrybować `isAuthenticated` → auto-reload | `subscribe()` reaguje na `isAuthenticated: true` → `loadFromAPI()` | [x] |
| 1.8 | **BRAMKA:** Login → Sidebar z API | ✅ Login PIN → Sidebar pokazuje prawdziwe workspaces z `/api/workspaces` (nie fallback) | [x] |

---

### Sekcja B2 — FAZA 2: Dead UI Revival

> **📁 Scope:** `chat.js`, `canvas.js`, `index.html`, `api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | `chat.js` — subskrybować `isAuthenticated` → wiadomość powitalna | Po logowaniu: agent mówi „Witaj! Połączenie z HUB aktywne. Workspace: X." | [ ] |
| 2.2 | `chat.js:getWorkspaceName()` — odczyt z `AppSidebar.workspaces` zamiast hardcoded mapy | Nowo dodane workspace wyświetlają poprawną nazwę w nagłówku czatu | [ ] |
| 2.3 | `canvas.js` — dodaj `vault-screen` do tablicy `this.tabs[]` z kluczem `'vault'` | Przełączanie Vault ↔ Chat ↔ Settings = poprawne hidden/flex | [ ] |
| 2.4 | `index.html` — zakładka Ustawienia: formularz edycji workspace | Formularz z polami: Nazwa workspace, URL Odoo (readonly ID) | [ ] |
| 2.5 | `api.py` — `PUT /api/workspaces/{ws_id}` endpoint | Aktualizacja nazwy/URL istniejącego workspace | [ ] |
| 2.6 | `api.py:handle_chat()` — naturalny reply per persona zamiast debug string | Reply: `[💻 Developer] Rozumiem, chcesz napisać kod...` zamiast `Zklasyfikowano jako A` | [ ] |
| 2.7 | `sidebar.js` + `chat.js` — loading skeleton przy ładowaniu danych | Pulsujący placeholder zamiast pustej białej dziury | [ ] |
| 2.8 | **BRAMKA:** Wszystkie 3 zakładki żyją | ✅ Vault renderuje sekrety, Chat ma powitanie, Settings ma formularz. Przełączanie czyste. | [ ] |

---

### Sekcja B3 — FAZA 3: Security Cleanup

> **📁 Scope:** `index.html`, `custom_addons/smart_chat/controllers/main.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | `index.html` — wyeliminuj globalną zmienną `currentAuth` | Wszystkie `currentAuth` zamienione na `AppStore.getState().authToken` | [ ] |
| 3.2 | `index.html` — usuń `let currentAuth = ""` (linia 249) | Zmienna nie istnieje w window scope | [ ] |
| 3.3 | `main.py` — zastąp `"Bearer 1111"` odczytem z `os.environ.get('SMARTMYODOO_API_TOKEN', '')` | Hardcoded credential usunięty z kodu źródłowego | [ ] |
| 3.4 | **BRAMKA:** Audit credentials | ✅ `Select-String "1111" smartmyodoo/` → zero wyników. `Select-String "currentAuth" smartmyodoo/` → zero wyników. | [ ] |

---

### Sekcja B4 — FAZA 4: Persistence & Polish

> **📁 Scope:** `api.py`, nowy plik `smartmyodoo/swarm/workspace_store.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 4.1 | Nowy moduł `workspace_store.py` — CRUD workspaces na SQLite | Klasa `WorkspaceStore` z metodami `list()`, `create()`, `update()`, `delete()` | [ ] |
| 4.2 | `api.py` — zamień `_workspaces: List` in-memory na `WorkspaceStore` | Restart serwera nie kasuje workspaces | [ ] |
| 4.3 | `api.py` — zamień `_proposals: Dict` in-memory na tabelę SQLite | Restart serwera nie kasuje proposals | [ ] |
| 4.4 | Loading/error states — Sidebar i Vault | Pulsujący skeleton przy ładowaniu, error banner przy 500 | [ ] |
| 4.5 | **BRAMKA:** Persistence test | ✅ Dodaj workspace → restartuj serwer → workspace nadal widoczny | [ ] |

---

## 📐 Szczegóły Implementacji (Cheat Sheet)

### Lifecycle — Store `isAuthenticated` pattern

```javascript
// store.js — nowe pole:
this.state = {
    workspaceId: 'default',
    activeTab: 'vault',
    authToken: '',
    isAuthenticated: false   // ← NOWE
};

// sidebar.js — reagowanie na login:
AppStore.subscribe((newState, oldState) => {
    if (newState.isAuthenticated && !oldState.isAuthenticated) {
        this.loadFromAPI(); // ← reload po zalogowaniu
    }
});

// chat.js — wiadomość powitalna po logowaniu:
AppStore.subscribe((newState, oldState) => {
    if (newState.isAuthenticated && !oldState.isAuthenticated) {
        const wsName = this.getWorkspaceName();
        this.addMessage('agent', `Witaj w panelu SmartMyOdoo HUB! 🔒 Połączenie zabezpieczone. Aktywna przestrzeń: ${wsName}. W czym mogę pomóc?`);
    }
});
```

### Dead UI — Naturalny reply per persona

```python
# api.py — template replies zamiast debug string:
PERSONA_REPLIES = {
    "A": "[💻 Developer] Rozumiem — chcesz napisać lub poprawić kod. Przygotowuję rozwiązanie...",
    "B": "[🗄️ DBA] Wykryłem operację bazodanową. Tworzę propozycję Shadow Mode...",
    "C": "[🧪 QA] Przygotowuję testy i walidację dla Twojego żądania...",
    "D": "[📝 Docs] Generuję dokumentację na podstawie Twojego opisu...",
    "E": "[🔍 Scout] Rozpoczynam research — przeszukuję bazę wiedzy...",
    "F": "[🏗️ Architect] Analizuję architekturę systemu pod kątem Twojego pytania...",
    "G": "[📊 PM] Aktualizuję status projektu i organizuję zadania...",
    "H": "[🤖 Asystent] {message_echo}",
}
```

### Security — Eliminacja currentAuth

```javascript
// PRZED (duplikat):
let currentAuth = "";              // ← USUNĄĆ
currentAuth = pwd;                 // ← USUNĄĆ
AppStore.setState({ authToken: pwd }); // ← ZOSTAWIĆ

// PO (single source of truth):
// Wszędzie gdzie było currentAuth → AppStore.getState().authToken
headers: { 'Authorization': `Bearer ${AppStore.getState().authToken}` }
```

### Persistence — WorkspaceStore

```python
# smartmyodoo/swarm/workspace_store.py
import sqlite3
from typing import List, Optional
from smartmyodoo.swarm.models import WorkspaceInfo

class WorkspaceStore:
    def __init__(self, db_path: str = "smartmyodoo.db"):
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    odoo_url TEXT DEFAULT ''
                )
            """)
            # Seed defaults if empty
            if conn.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO workspaces (id, name) VALUES (?, ?)",
                    [("default", "Domyślna"), ("dev", "Dev Env"), ("prod", "Production")]
                )
```

---

## ✅ Sekcja E — Finalna Weryfikacja

| # | Check | Akcja | Oczekiwany wynik |
|---|-------|-------|------------------|
| V1 | Unit Tests | `pytest tests/test_api.py -v` | ✅ ALL GREEN |
| V2 | PII Regression | `pytest tests/test_pii_recognizers.py tests/test_pii_middleware.py -v` | ✅ ALL GREEN |
| V3 | Login → Sidebar | Wpisz PIN → patrz na Sidebar | ✅ Workspace list z API (nie mock) |
| V4 | Login → Chat | Wpisz PIN → przejdź do Chat | ✅ Wiadomość powitalna agenta |
| V5 | Settings Tab | Kliknij Ustawienia | ✅ Formularz edycji workspace |
| V6 | Tab Switching | Vault → Chat → Settings → Vault | ✅ Poprawne ukrywanie/pokazywanie |
| V7 | Credentials Audit | `Select-String "1111" custom_addons/` | ✅ Zero wyników |
| V8 | Credentials Audit | `Select-String "currentAuth" smartmyodoo/ui/` | ✅ Zero wyników |
| V9 | Persistence | Dodaj workspace → restart serwera → sprawdź | ✅ Workspace przetrwał restart |
| V10 | Konsola | DevTools → Console | ✅ Zero błędów JS |

---

## 📋 Priorytetyzacja (MoSCoW)

| Priorytet | Faza | Bug IDs | Opis |
|---|---|---|---|
| **MUST** | F1 | BUG-01, 02, 03 | Lifecycle — Sidebar reload, Store auth, double-login guard |
| **MUST** | F2 | BUG-04, 11 | Dead UI — Wiadomość powitalna, canvas tabs fix |
| **SHOULD** | F2 | BUG-05, 06, 09, 12 | Dead UI — Ustawienia formularz, workspace name, reply, loading |
| **SHOULD** | F3 | BUG-07, 08 | Security — Eliminacja hardcoded credentials |
| **COULD** | F4 | BUG-10 | Persistence — Workspaces/Proposals do SQLite |
