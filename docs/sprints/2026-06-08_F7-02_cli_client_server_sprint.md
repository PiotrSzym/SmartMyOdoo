---
sprint_id: "F7-02"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-08
goal: "Refaktoryzacja CLI z 'Grubego Klienta' na cienki klient HTTP odpytujący backend FastAPI (Client-Server Mode)"
prefix: "F7"
complexity: 4
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
tags: ["cli", "client-server", "http-client", "thin-client", "websocket", "refactoring"]
parent_sprint: "ARCH-F7-03"
depends_on: ["ARCH-F7-03"]
---

# 🏗️ Sprint F7-02 — CLI Client-Server Mode (Thin HTTP Client)

> **Architekt:** /arch | **Data:** 2026-06-08
> **Roadmap ref:** `docs/blueprint/tom2-architektura/roadmap.md` § 7.2
> **Parent Phase:** Faza 7 — Production Hardening & Client-Server Mode

---

## 📊 Audyt Bieżącego Stanu (Problem Statement)

### Problem: „Gruby Klient" (Monolit x2)

Obecnie mamy **dwa niezależne mózgi** wykonujące identyczną pracę:

```
┌─────────────────────────────────────────────────────┐
│              STAN OBECNY (MONOLITY)                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  CLI (__main__.py)          API (api.py)             │
│  ┌─────────────────┐       ┌─────────────────┐      │
│  │ Database ✓      │       │ Database ✓      │      │
│  │ LLM Client ✓    │       │ LLM Client ✓    │      │
│  │ SkillExecutor ✓ │       │ SkillExecutor ✓ │      │
│  │ ChatRepo ✓      │       │ ChatRepo ✓      │      │
│  │ Sandbox ✓       │       │ Sandbox ✓       │      │
│  └─────────────────┘       └─────────────────┘      │
│        ▲                         ▲                   │
│        │                         │                   │
│    Terminal                  Browser                  │
└─────────────────────────────────────────────────────┘
```

**Konsekwencje:**
- Zmiana logiki w `api.py` (np. nowy skill, nowy tool) nie jest widoczna w CLI
- Dwa oddzielne połączenia do SQLite → możliwe konflikty WAL
- Duplikacja kodu zarządzania Vaultem, LLM-em, Dispatcherem
- CLI wymaga wszystkich zależności produkcyjnych (litellm, lancedb, etc.)

### Cel: Architektura Client-Server

```
┌─────────────────────────────────────────────────────┐
│              STAN DOCELOWY (CLIENT-SERVER)           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐      ┌──────────────────────────┐ │
│  │ CLI (Thin)   │─HTTP→│ FastAPI Server (api.py)   │ │
│  │ httpx/aiohttp│      │ ┌──────────────────────┐ │ │
│  │ Rich TUI     │      │ │ Database             │ │ │
│  │ NO DB        │      │ │ LLM Client           │ │ │
│  │ NO LLM       │      │ │ SkillExecutor        │ │ │
│  │ NO Executor  │      │ │ ChatRepo             │ │ │
│  └──────────────┘      │ │ Sandbox              │ │ │
│                        │ └──────────────────────┘ │ │
│  ┌──────────────┐      │                          │ │
│  │ Browser (GUI)│─HTTP→│                          │ │
│  └──────────────┘      └──────────────────────────┘ │
│                                                     │
│              ┌──────────────────────┐                │
│              │ WebSocket (opcja)    │                │
│              │ Streaming Logs/Reply │                │
│              └──────────────────────┘                │
└─────────────────────────────────────────────────────┘
```

### Pliki dotknięte problemem

| Plik | Rola obecna | Rola docelowa |
|------|-------------|---------------|
| `smartmyodoo/__main__.py` (93 LOC) | Gruby klient: DB + LLM + Executor | Thin client: login HTTP → chat HTTP → print |
| `smartmyodoo/cli.py` (138 LOC) | TUI z callbackiem do Executora | TUI z callbackiem do HTTP POST `/api/chat` |
| `smartmyodoo/api.py` (994 LOC) | Backend obsługujący GUI | **Jedyny mózg** — Server dla GUI + CLI |

### Endpointy API potrzebne przez CLI

| Endpoint | Metoda | Status | Uwagi |
|----------|--------|--------|-------|
| `POST /api/auth` | POST | ✅ Działa | CLI użyje do logowania |
| `POST /api/chat` | POST | ⚠️ Wymaga fix (ARCH-F7-03 G1) | Musi zwracać prawdziwą odpowiedź LLM |
| `GET /api/chat/sessions` | GET | ✅ Działa | CLI użyje do `_show_previous_sessions()` |
| `GET /api/chat/sessions/{sid}/messages` | GET | ✅ Działa | Opcjonalnie: podgląd historii |
| `GET /api/skills` | GET | ✅ Działa | CLI może wyświetlić listę skilli |

---

## ⚠️ Decyzje wymagające zatwierdzenia

### D1: Zależność od ARCH-F7-03 (G1)

Sprint F7-02 **WYMAGA**, aby endpoint `POST /api/chat` zwracał prawdziwą odpowiedź od LLM (nie hardkodowany template).

> **Pytanie:** Czy ARCH-F7-03 Faza 2 (Real LLM Responses) jest już zamknięta?
> Jeśli nie — F7-02 może zostać uruchomiony, ale wymaga co najmniej działającego fallbacku (echo/heuristic mode).

### D2: Biblioteka HTTP dla CLI

| Opcja | Zalety | Wady |
|-------|--------|------|
| **`httpx` (REKOMENDACJA)** | Sync + async, timeout kontrola, JSON first-class | Nowa zależność |
| `requests` | Najpopularniejszy | Brak async, brak WebSocket |
| `urllib3` | Zero zależności | Niskopoziomowy, boilerplate |

**Rekomendacja:** `httpx` — lekki, nowocześny, wspiera streaming responses (SSE) i jest naturalnym krokiem do WebSocketów.

### D3: Autentykacja CLI → Server

CLI musi się zalogować do serwera. Obecny mechanizm to `Bearer Token` (PIN lub Master Password).
**Propozycja:** CLI pyta użytkownika o PIN → wysyła `POST /api/auth` → otrzymuje token → używa go w nagłówku `Authorization: Bearer {pin}` dla wszystkich dalszych requestów.

### D4: WebSocket (Faza 3 — opcjonalna)

Streaming responses (Live Logs) wymaga WebSocket. Czy wdrożyć to w ramach tego sprintu, czy odłożyć?

**Rekomendacja:** Odłożyć do osobnego sprintu F7-02b. Najpierw klasyczny HTTP (synchroniczny request-response).

---

## ⚖️ ZASADY SPRINTU — Podsumowanie

### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Fazy 1→2→3 muszą być realizowane sekwencyjnie. Faza 2 nie może rozpocząć się bez zamkniętej Bramki Fazy 1.

### Zasada 2: TDD FIRST / VALIDATION 🟠
Każda faza kończy się uruchomieniem `python -m pytest tests/ -v` i oczekiwaniem **ALL GREEN**.

### Zasada 3: SCOPE ISOLATION 🔴
Scope: wyłącznie `smartmyodoo/__main__.py`, `smartmyodoo/cli.py`, plus nowy `smartmyodoo/http_client.py`. **Zakaz modyfikacji** `api.py` poza dodaniem ewentualnego nowego endpointu.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────────────────┐
│  FAZA 1: HTTP Client Module                       │
│  Nowy plik: smartmyodoo/http_client.py            │
│  ┌────────────────────────────────────────┐       │
│  │ 1.1 Klasa SmartMyOdooClient            │       │
│  │ 1.2 Metody: login(), chat(), sessions()│       │
│  │ 1.3 Testy jednostkowe z mockami        │       │
│  └────────────────────────────────────────┘       │
└──────────────────┬───────────────────────────────┘
                   │ ✅ BRAMKA: pytest tests/test_http_client.py → GREEN
                   ▼
┌──────────────────────────────────────────────────┐
│  FAZA 2: CLI Refaktoring                          │
│  Modyfikacja: __main__.py + cli.py                │
│  ┌────────────────────────────────────────┐       │
│  │ 2.1 Usunięcie importów DB/LLM/Executor│       │
│  │ 2.2 Nowy callback: HTTP POST /api/chat│       │
│  │ 2.3 Login flow: prompt PIN → auth API │       │
│  │ 2.4 Sessions via HTTP GET             │       │
│  └────────────────────────────────────────┘       │
└──────────────────┬───────────────────────────────┘
                   │ ✅ BRAMKA: pytest + manual test (CLI → Server → odpowiedź)
                   ▼
┌──────────────────────────────────────────────────┐
│  FAZA 3: WebSocket Streaming (OPCJONALNA)         │
│  ┌────────────────────────────────────────┐       │
│  │ 3.1 WS endpoint /ws/chat w api.py     │       │
│  │ 3.2 CLI: websockets client             │       │
│  │ 3.3 Live log rendering w Rich          │       │
│  └────────────────────────────────────────┘       │
└──────────────────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: HTTP Client Module

> **Trigger:** `python -m pytest tests/test_http_client.py -v`
> **📁 Scope:** `smartmyodoo/http_client.py` [NEW], `tests/test_http_client.py` [NEW]

#### Specyfikacja klasy `SmartMyOdooClient`

```python
# smartmyodoo/http_client.py
class SmartMyOdooClient:
    """Thin HTTP client — jedyny interfejs CLI do backendu."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self._token: str | None = None  # PIN/Master password

    def login(self, password: str) -> dict:
        """POST /api/auth → {success: bool, role: str}"""

    def chat(self, message: str, workspace_id: str, session_id: str,
             selected_skills: list[str] | None = None) -> dict:
        """POST /api/chat → ChatResponse"""

    def list_sessions(self, workspace_id: str, limit: int = 5) -> list[dict]:
        """GET /api/chat/sessions → lista sesji"""

    def get_skills(self) -> list[dict]:
        """GET /api/skills → lista dostępnych skilli"""
```

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Utworzenie pliku `smartmyodoo/http_client.py` z klasą `SmartMyOdooClient` | Plik istnieje, klasa importowalna | [ ] |
| 1.2 | Metoda `login(password)` → `POST /api/auth` + zapis tokena | Zwraca `{success, role}`, zapisuje token | [ ] |
| 1.3 | Metoda `chat(message, ...)` → `POST /api/chat` z nagłówkiem `Authorization: Bearer {token}` | Zwraca `ChatResponse` jako dict | [ ] |
| 1.4 | Metoda `list_sessions(workspace_id)` → `GET /api/chat/sessions` | Zwraca listę sesji | [ ] |
| 1.5 | Metoda `get_skills()` → `GET /api/skills` | Zwraca listę skilli | [ ] |
| 1.6 | Obsługa błędów: `ConnectionError`, `HTTPStatusError` (401, 500) | Graceful error messages, nie crash | [ ] |
| 1.7 | Testy: `tests/test_http_client.py` z `httpx.MockTransport` | ≥8 testów, ALL GREEN | [ ] |
| 1.8 | **BRAMKA:** `python -m pytest tests/test_http_client.py -v` | ✅ ALL GREEN | [ ] |

---

### Sekcja B2 — FAZA 2: CLI Refaktoring (Thin Client)

> **Trigger:** Bramka 1.8 zamknięta
> **📁 Scope:** `smartmyodoo/__main__.py`, `smartmyodoo/cli.py`

#### Obecne importy w `__main__.py` (DO USUNIĘCIA):

```python
# ❌ USUNĄĆ — to jest "Gruby Klient":
from smartmyodoo.swarm.executor import SkillExecutor
from smartmyodoo.swarm.llm_client import OpenRouterClient
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.sandbox import SandboxManager
from smartmyodoo.core.database import engine, SessionLocal
from smartmyodoo.core import models as db_models
from smartmyodoo.core.chat_repository import ChatRepository
```

#### Docelowy `__main__.py` (~30 LOC zamiast 93):

```python
# ✅ NOWY — Thin Client:
from smartmyodoo.http_client import SmartMyOdooClient
from smartmyodoo.cli import InteractiveCLI

def main():
    client = SmartMyOdooClient(base_url="http://127.0.0.1:8000")

    # 1. Login
    pin = input("PIN: ")
    auth = client.login(pin)
    if not auth.get("success"):
        print("❌ Logowanie nieudane.")
        return

    # 2. CLI z HTTP callback
    workspace_id = "default"
    session_id = f"cli-{int(time.time())}"

    def callback(message: str) -> dict:
        resp = client.chat(message, workspace_id, cli.session_id)
        return {"response": resp.get("reply", ""), "tools_used": []}

    cli = InteractiveCLI(callback=callback, workspace_id=workspace_id,
                         session_id=session_id)
    cli.run()
```

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Nowy `__main__.py` — zastąpienie 93 LOC na ~30 LOC z `SmartMyOdooClient` | CLI nie importuje `database`, `llm_client`, `executor`, `sandbox` | [ ] |
| 2.2 | Login flow: prompt PIN → `client.login(pin)` → walidacja | Nieudane logowanie → czytelny błąd, nie crash | [ ] |
| 2.3 | Nowy `callback`: `client.chat(message, ...)` zamiast `executor.execute(...)` | Chat przechodzi przez HTTP → serwer | [ ] |
| 2.4 | Refaktor `cli.py` — `_show_previous_sessions()` przez HTTP | `client.list_sessions()` zamiast `chat_repo.list_sessions()` | [ ] |
| 2.5 | Opcjonalny parametr `--url` do CLI (`python -m smartmyodoo --url http://...`) | Konfigurowalny adres serwera | [ ] |
| 2.6 | Opcjonalny parametr `--workspace` do CLI | Konfigurowalny workspace | [ ] |
| 2.7 | Testy: `tests/test_cli_thin.py` — mock HTTP, weryfikacja flow | ≥5 testów, ALL GREEN | [ ] |
| 2.8 | **BRAMKA:** `python -m pytest tests/ -v` — ALL GREEN (brak regresji) | ✅ Cały suite zielony | [ ] |

#### Refaktor `InteractiveCLI` — zmiany w `cli.py`:

**Przed (obecny):**
- `__init__` przyjmuje `chat_repo` (bezpośredni dostęp do DB)
- `_show_previous_sessions()` woła `self.chat_repo.list_sessions()`

**Po (docelowy):**
- `__init__` przyjmuje `http_client: SmartMyOdooClient` (opcjonalnie, dla sessions)
- `_show_previous_sessions()` woła `self.http_client.list_sessions()`
- `callback` nie zmienia sygnatury (nadal `message: str → dict`)

---

### Sekcja B3 — FAZA 3: WebSocket Streaming (OPCJONALNA)

> **Trigger:** Bramka 2.8 zamknięta + decyzja D4 zatwierdzona
> **📁 Scope:** `smartmyodoo/api.py` (nowy endpoint), `smartmyodoo/http_client.py` (WS metoda)

> ⚠️ **Ta faza jest OPCJONALNA** — może zostać odłożona do osobnego sprintu F7-02b.

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Nowy endpoint `WS /ws/chat` w `api.py` z `fastapi.WebSocket` | WebSocket handshake OK | [ ] |
| 3.2 | Streaming: serwer wysyła tokeny odpowiedzi LLM na bieżąco | Klient otrzymuje partial responses | [ ] |
| 3.3 | `SmartMyOdooClient.chat_stream()` — generator tokenów | `for token in client.chat_stream(msg): ...` | [ ] |
| 3.4 | `InteractiveCLI` — Rich `Live` rendering odpowiedzi token-by-token | Płynna animacja w terminalu | [ ] |
| 3.5 | Live Logs: serwer pushuje logi narzędzi (`tools_used`) w trakcie | CLI wyświetla "🔧 Używam: odoo_search..." na bieżąco | [ ] |
| 3.6 | Testy: mock WebSocket, weryfikacja streaming flow | ≥3 testy GREEN | [ ] |
| 3.7 | **BRAMKA:** Manual test: CLI → WS → streaming odpowiedź widoczna | ✅ E2E streaming | [ ] |

---

## 📦 Nowa zależność

```
# requirements.txt — dodać:
httpx>=0.27.0
```

> `httpx` jest jedyną nową zależnością. Dla Fazy 3 (opcjonalnej): `websockets>=12.0`.

---

## 📈 Sprint Metrics

| Metryka | Przed | Cel |
|---------|-------|-----|
| `__main__.py` LOC | 93 (gruby klient) | ~30 (thin client) |
| Importy DB/LLM w CLI | 8 importów | 0 importów |
| CLI wymaga SQLite | ✅ Tak | ❌ Nie |
| CLI wymaga litellm | ✅ Tak | ❌ Nie |
| CLI wymaga OpenRouter key | ✅ Tak | ❌ Nie |
| Punkt wejścia do logiki | 2 (CLI + API) | 1 (tylko API) |
| Testy | 57 zebranych | 57 + ~13 nowych ≈ 70 |

---

## ✅ Sekcja E — Finalna Weryfikacja

> Wykonuje użytkownik lub `/qa` po zakończeniu Fazy 2.

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|------------------|
| V1 | Unit Tests | `python -m pytest tests/ -v` | ✅ ALL GREEN (≥70 testów) |
| V2 | CLI uruchamia się bez DB | `python -m smartmyodoo` (bez pliku .db obok) | ✅ CLI odpala, pyta o PIN |
| V3 | CLI loguje się do serwera | PIN → `POST /api/auth` → odpowiedź | ✅ `role: user` lub `admin` |
| V4 | CLI wysyła chat przez HTTP | Wiadomość → `POST /api/chat` → odpowiedź LLM | ✅ Tekst odpowiedzi w panelu Rich |
| V5 | CLI pokazuje sessions przez HTTP | `/sessions` → `GET /api/chat/sessions` | ✅ Tabela z sesjami |
| V6 | Serwer jest jedynym mózgiem | `grep -r "from smartmyodoo.core.database" smartmyodoo/__main__.py` | ✅ **Brak wyników** |
| V7 | Brak regresji w GUI | Przeglądarka → `http://127.0.0.1:8000` → chat działa | ✅ GUI nienaruszone |

---

## 🏁 Definition of Done

- [ ] `smartmyodoo/http_client.py` istnieje z klasą `SmartMyOdooClient`
- [ ] `smartmyodoo/__main__.py` NIE importuje `database`, `llm_client`, `executor`
- [ ] CLI loguje się przez HTTP (`POST /api/auth`)
- [ ] CLI chatuje przez HTTP (`POST /api/chat`)
- [ ] CLI wyświetla sesje przez HTTP (`GET /api/chat/sessions`)
- [ ] `python -m pytest tests/ -v` → ALL GREEN
- [ ] GUI (przeglądarka) działa bez zmian
- [ ] Sprint zamknięty w YAML frontmatter (`status: DONE`)
