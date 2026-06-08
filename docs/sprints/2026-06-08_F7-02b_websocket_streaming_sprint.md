---
sprint_id: "F7-02b"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-08
goal: "WebSocket Streaming — Live Logs & token-by-token odpowiedzi w CLI i GUI"
prefix: "F7"
complexity: 5
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
tags: ["websocket", "streaming", "live-logs", "asyncio", "litellm", "rich-live"]
parent_sprint: "F7-02"
depends_on: ["F7-02", "ARCH-F7-03", "F7-02c"]
---

# ARCH-F7-02b: WebSocket Streaming (Live Logs & Token-by-Token)

> **Roadmap Context:** `docs/blueprint/tom2-architektura/roadmap.md` → Phase F7 — Production Hardening & Client-Server Mode
> Date: 2026-06-08
> Status: 🔵 Planning

---

## 📊 PROGRESS BAR (Omnidirected)
| # | Block (Task Name) | Arch | Dev | QA | Doc | Status |
|---|-------------------|:----:|:---:|:--:|:---:|:------:|
| 1 | LLM Streaming Client | ✅ | ⬜ | ⬜ | ⬜ | 🔵 |
| 2 | Async Executor Generator | ✅ | ⬜ | ⬜ | ⬜ | 🔵 |
| 3 | FastAPI WebSocket Endpoint | ✅ | ⬜ | ⬜ | ⬜ | 🔵 |
| 4 | CLI/GUI WebSocket Client | ✅ | ⬜ | ⬜ | ⬜ | 🔵 |

**Status Summary:** 0/4 ✅ Done | 0/4 🟡 In Dev | 4/4 🔵 Planned | 0/4 ⬜ Backlog

> **Legend:** Arch=Planned, Dev=Coded, QA=Audited, Doc=Documented. A block is only DONE once all 4 agent columns are marked ✅.

---

## SEKCJA A — ARCHITECT (/arch, /plan)
> **Active Skills:** `architecture`, `api-patterns`, `python-patterns`

### A1. User Story & Acceptance Criteria
| ID | As a... | I want... | So that... | E2E Test Link |
|----|---------|-----------|------------|---------------|
| US-010 | Użytkownik CLI | widzieć odpowiedź agenta pojawiającą się litera po literze | nie muszę czekać 15s na pełną odpowiedź — widzę postęp na żywo | `tests/test_ws_streaming.py` |
| US-011 | Użytkownik CLI/GUI | widzieć live-logi (np. "Szukam w Odoo…") | wiem, co agent robi "w czarnej skrzynce" | `tests/test_ws_streaming.py` |
| US-012 | Serwer | bezpiecznie obsłużyć nagłe zamknięcie WebSocketa | aby `Ctrl+C` w CLI nie crashowało procesu serwera | `tests/test_ws_disconnect.py` |

### A2. L1-L5 Decision Matrix
| Level | Key Decision | Rationale | Skill Used |
|-------|--------------|-----------|------------|
| **L1** | Protokół strumieniowania: **WebSocket** (nie SSE) | FastAPI ma wbudowaną obsługę `WebSocket`. SSE wymaga dodatkowej warstwy. WS daje dwukierunkową komunikację (cancel, ping). | `api-patterns` |
| **L2** | Biblioteka klienta WS w CLI: **`websockets`** (pakiet pypi) | Lekki, asyncio-native, zero zależności, standard de facto. `httpx-ws` jest immature. | `python-patterns` |
| **L3** | Format wiadomości WS: zunifikowany JSON `{"type": "...", "content": "..."}` | Uniwersalny kontrakt dla CLI (Python) i GUI (JavaScript). Typy: `token`, `log`, `done`, `error`. | `architecture` |
| **L4** | LLM Streaming: `litellm.completion(..., stream=True)` | litellm jest już naszą jedyną zależnością LLM. Obsługuje streaming OpenRouter + tool calling w streamie. | `ai-ml` |
| **L5** | CLI rendering: `rich.live.Live` + `Markdown` mutowany na żywo | Rich jest już zainstalowany. `Live` context manager daje atomowe aktualizacje terminala bez migotania. | `python-patterns` |

### A3. ADR / Complexity Score
- **Complexity Score:** 🔴5
- **ADR Link:** Nowy ADR-015 (WebSocket Streaming Architecture) — do utworzenia po zatwierdzeniu sprintu.
- **Obowiązujące ADR:**
  - **ADR-011 (Logging & Sanitization):** Live-logi nie mogą zawierać danych PII. Nazwy narzędzi i argumenty muszą być sanityzowane przez Presidio przed wysłaniem do WS.
  - **ADR-012 (LLM Context Guardrails):** TokenGovernor sprawdzenie musi odbyć się PRZED otwarciem streamu, a nie w trakcie.

### A4. L5 Execution Plan for Developer
| # | Task | Target File | Test File | Score | Status |
|---|------|------------|-----------|-------|--------|
| 1 | chat_stream() w LLM Client | `smartmyodoo/swarm/llm_client.py` | `tests/test_llm_stream.py` | 🟡3 | ⬜ |
| 2 | execute_stream() w Executor | `smartmyodoo/swarm/executor.py` | `tests/test_executor_stream.py` | 🔴5 | ⬜ |
| 3 | WS Endpoint /api/chat/stream | `smartmyodoo/api.py` | `tests/test_ws_endpoint.py` | 🟠4 | ⬜ |
| 4 | CLI WS Client + Rich Live | `smartmyodoo/http_client.py`, `smartmyodoo/cli.py` | `tests/test_cli_stream.py` | 🟠4 | ⬜ |

---

## 📋 Sekcja A-bis — Business Discovery & Rules

### Cel biznesowy
Przekształcenie obecnego synchronicznego modelu request-response (POST `/api/chat` → czekaj → cała odpowiedź) na strumieniowy model WebSocket, w którym:
1. Tekst odpowiedzi agenta pojawia się **token po tokenie** (UX jak ChatGPT).
2. Podczas wywoływania narzędzi w Odoo pojawiają się **live-logi** informujące, co agent robi.
3. Nagłe zamknięcie CLI (`Ctrl+C`) nie powoduje crashu serwera.

### Metryka sukcesu (DoD)
1. `python -m smartmyodoo` → zadaj pytanie → tekst wylewa się płynnie w terminalu (nie pojawia się "hurtowo").
2. Kiedy agent wywołuje narzędzie, w CLI pojawia się log `🔧 Wywołuję: odoo_search(...)`.
3. `Ctrl+C` w trakcie streamu → CLI wraca do promptu, serwer loguje `WebSocketDisconnect` i nie crashuje.
4. `python -m pytest tests/ -v` → ALL GREEN.
5. GUI (przeglądarka) nadal działa z klasycznym `POST /api/chat` (backwards compatible).

### ⚖️ ZASADY SPRINTU — Podsumowanie

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Fazy 1→2→3→4 muszą być realizowane sekwencyjnie. Faza N+1 nie startuje bez zamkniętej Bramki Fazy N.

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Każda faza kończy się uruchomieniem `python -m pytest tests/ -v` i oczekiwaniem **ALL GREEN**.

#### Zasada 3: SCOPE ISOLATION 🔴
| Faza | Pliki w scope | Zakaz |
|------|---------------|-------|
| 1 | `swarm/llm_client.py` | Nie ruszamy executor.py |
| 2 | `swarm/executor.py` | Nie ruszamy api.py |
| 3 | `api.py` | Nie ruszamy cli.py |
| 4 | `http_client.py`, `cli.py` | Nie ruszamy api.py |

#### Zasada 4: BACKWARDS COMPATIBILITY 🔴
Istniejący endpoint `POST /api/chat` **MUSI** działać bez zmian. WebSocket to **dodatkowy** endpoint, nie zastępczy.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────────────────────┐
│  FAZA 1: LLM Streaming Client                        │
│  llm_client.py → chat_stream()                       │
│  ┌──────────────────────────────────────────────┐    │
│  │ 1.1 Metoda chat_stream() (async generator)   │    │
│  │ 1.2 Obsługa delta.content + delta.tool_calls │    │
│  │ 1.3 Testy z mockiem litellm                  │    │
│  └──────────────────────────────────────────────┘    │
└───────────────────┬──────────────────────────────────┘
                    │ ✅ BRAMKA: pytest tests/test_llm_stream.py → GREEN
                    ▼
┌──────────────────────────────────────────────────────┐
│  FAZA 2: Async Executor Generator                     │
│  executor.py → execute_stream()                       │
│  ┌──────────────────────────────────────────────┐    │
│  │ 2.1 async generator execute_stream()         │    │
│  │ 2.2 Tool call delta buffering & execution    │    │
│  │ 2.3 Yield {"type":"log"} przy tool calls     │    │
│  │ 2.4 Yield {"type":"token"} przy delta.content│    │
│  │ 2.5 Red Flags + Sandbox integration          │    │
│  │ 2.6 Testy z mock LLM stream                  │    │
│  └──────────────────────────────────────────────┘    │
└───────────────────┬──────────────────────────────────┘
                    │ ✅ BRAMKA: pytest tests/test_executor_stream.py → GREEN
                    ▼
┌──────────────────────────────────────────────────────┐
│  FAZA 3: FastAPI WebSocket Endpoint                   │
│  api.py → @app.websocket("/api/chat/stream")         │
│  ┌──────────────────────────────────────────────┐    │
│  │ 3.1 WS handshake + auth (first message)      │    │
│  │ 3.2 Odbiór ChatRequest z WS                  │    │
│  │ 3.3 Iteracja po execute_stream() → send_json │    │
│  │ 3.4 WebSocketDisconnect handler              │    │
│  │ 3.5 Chat persistence po zakończeniu streamu  │    │
│  │ 3.6 Testy z TestClient.websocket_connect     │    │
│  └──────────────────────────────────────────────┘    │
└───────────────────┬──────────────────────────────────┘
                    │ ✅ BRAMKA: pytest tests/test_ws_endpoint.py → GREEN
                    ▼
┌──────────────────────────────────────────────────────┐
│  FAZA 4: CLI/GUI WebSocket Client                     │
│  http_client.py + cli.py                              │
│  ┌──────────────────────────────────────────────┐    │
│  │ 4.1 chat_stream() w SmartMyOdooClient (WS)   │    │
│  │ 4.2 Rich Live rendering w InteractiveCLI     │    │
│  │ 4.3 Live log display (status bar / spinner)  │    │
│  │ 4.4 Ctrl+C graceful disconnect               │    │
│  │ 4.5 Fallback: jeśli WS fail → HTTP POST      │    │
│  │ 4.6 Testy z mock WebSocket                   │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: LLM Streaming Client

> **Trigger:** Start sprintu (brak zależności wewnętrznych)
> **📁 Scope:** `smartmyodoo/swarm/llm_client.py`, `tests/test_llm_stream.py` [NEW]

#### Specyfikacja nowej metody `chat_stream()`

```python
# smartmyodoo/swarm/llm_client.py  — DODAĆ do klasy OpenRouterClient

def chat_stream(
    self,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Generator:
    """
    Streaming version of chat().
    Yields raw chunks from litellm (delta objects).
    Caller (Executor) is responsible for interpreting deltas.
    """
    kwargs = {
        "model": self.model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2000,
        "api_key": self.api_key,
        "stream": True,  # ← kluczowa flaga
    }
    if tools:
        kwargs["tools"] = tools

    response = litellm.completion(**kwargs)
    for chunk in response:
        yield chunk
```

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Dodanie metody `chat_stream()` do `OpenRouterClient` | Metoda istnieje, jest wywoływalna | [ ] |
| 1.2 | Obsługa parametru `stream=True` w `litellm.completion()` | litellm zwraca generator chunków | [ ] |
| 1.3 | Propagacja błędów — `try/except` z logowaniem, yield specjalnego error-chunk | Brak crashu przy problemach sieciowych | [ ] |
| 1.4 | Testy: `tests/test_llm_stream.py` — mock `litellm.completion` zwracający fake chunks | ≥4 testy, ALL GREEN | [ ] |
| 1.5 | **BRAMKA:** `python -m pytest tests/test_llm_stream.py -v` | ✅ ALL GREEN | [ ] |

---

### Sekcja B2 — FAZA 2: Async Executor Generator

> **Trigger:** Bramka 1.5 zamknięta
> **📁 Scope:** `smartmyodoo/swarm/executor.py`, `tests/test_executor_stream.py` [NEW]

#### Specyfikacja `execute_stream()` — kluczowa logika

```python
# smartmyodoo/swarm/executor.py — DODAĆ nową metodę

async def execute_stream(
    self, skill_config: SkillConfig, message: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Async generator yielding streaming events.
    Each event: {"type": "token"|"log"|"done"|"error", "content": "..."}
    """
    # 1. Red Flag Detection (identycznie jak execute())
    for flag in skill_config.red_flags:
        if re.search(flag, message, re.IGNORECASE):
            yield {"type": "error", "content": f"⛔ Red flag: {flag}"}
            return

    # 2. Build messages (identycznie jak execute())
    messages = [{"role": "system", "content": skill_config.system_prompt}]
    # ... Smart Context ...
    messages.append({"role": "user", "content": message})
    self._save_chat("user", message)

    # 3. Streaming loop
    tools_used = set()
    full_response = ""
    tool_call_buffer = {}  # id → {name, arguments_chunks}

    for iteration in range(10):
        yield {"type": "log", "content": f"Iteracja {iteration+1}: odpytuję LLM..."}

        for chunk in self.llm_client.chat_stream(messages, tools_schemas):
            delta = chunk.choices[0].delta

            # 3a. Text token
            if delta.content:
                full_response += delta.content
                yield {"type": "token", "content": delta.content}

            # 3b. Tool call delta (buffered)
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_call_buffer:
                        tool_call_buffer[idx] = {
                            "id": tc_delta.id,
                            "name": tc_delta.function.name or "",
                            "arguments": ""
                        }
                    if tc_delta.function.arguments:
                        tool_call_buffer[idx]["arguments"] += tc_delta.function.arguments

        # 3c. Finish reason: if tool calls were buffered, execute them
        if tool_call_buffer:
            for idx, tc in tool_call_buffer.items():
                func_name = tc["name"]
                yield {"type": "log", "content": f"🔧 Wywołuję: {func_name}(...)"}
                tools_used.add(func_name)

                # Execute tool ...
                # Append tool result to messages ...

            tool_call_buffer = {}
            continue  # next iteration — send tool results to LLM

        else:
            break  # no tool calls → response complete

    # 4. Finalize
    self._save_chat("assistant", full_response, {"tools_used": list(tools_used)})
    yield {"type": "done", "content": "", "tools_used": list(tools_used)}
```

#### Kluczowe wyzwanie: Tool Call Delta Buffering

W trybie `stream=True` API nie wysyła pełnego `tool_calls` w jednym kawałku. Zamiast tego argumenty funkcji przychodzą w wielu deltach:

```
chunk[0]: delta.tool_calls[0].function.name = "odoo_search"
chunk[1]: delta.tool_calls[0].function.arguments = '{"model":'
chunk[2]: delta.tool_calls[0].function.arguments = ' "res.pa'
chunk[3]: delta.tool_calls[0].function.arguments = 'rtner"}'
chunk[4]: finish_reason = "tool_calls"
```

Executor **MUSI** buforować te delty (`tool_call_buffer`), skleić argumenty po zakończeniu, sparsować JSON, i dopiero wtedy wywołać narzędzie z `TOOL_REGISTRY`.

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Nowa metoda `async execute_stream()` w `SkillExecutor` | Metoda istnieje, jest async generatorem | [ ] |
| 2.2 | Red Flag Detection na wejściu (yield error, return) | Identyczna logika jak execute(), ale yield zamiast raise | [ ] |
| 2.3 | Smart Context loading (identycznie jak execute()) | Kontekst z poprzednich sesji wstrzyknięty | [ ] |
| 2.4 | Token streaming: yield `{"type": "token"}` przy `delta.content` | Tekst pojawia się po kawałku | [ ] |
| 2.5 | Tool call delta buffering — sklejanie arguments z wielu chunków | Buffer poprawnie skleja JSON | [ ] |
| 2.6 | Tool execution po zakończeniu bufferingu | Wywołanie z `TOOL_REGISTRY`, yield `{"type": "log"}` | [ ] |
| 2.7 | Sandbox auto-enter/exit (identycznie jak execute()) | Write tools → sandbox | [ ] |
| 2.8 | Audit Trail logowanie (identycznie jak execute()) | Każde wywołanie narzędzia → AuditLog | [ ] |
| 2.9 | Finalizacja: `_save_chat()` + yield `{"type": "done"}` | Pełna odpowiedź zapisana w DB | [ ] |
| 2.10 | Testy: `tests/test_executor_stream.py` — mock LLM stream | ≥6 testów (happy path, tool call, red flag, max iterations, disconnect, empty) | [ ] |
| 2.11 | **BRAMKA:** `python -m pytest tests/test_executor_stream.py tests/test_llm_stream.py -v` | ✅ ALL GREEN | [ ] |

---

### Sekcja B3 — FAZA 3: FastAPI WebSocket Endpoint

> **Trigger:** Bramka 2.11 zamknięta
> **📁 Scope:** `smartmyodoo/api.py`, `tests/test_ws_endpoint.py` [NEW]

#### Specyfikacja endpointu

```python
# smartmyodoo/api.py — DODAĆ

from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/api/chat/stream")
async def websocket_chat_stream(websocket: WebSocket):
    await websocket.accept()

    try:
        # 1. Auth handshake (first message)
        auth_msg = await websocket.receive_json()
        # auth_msg = {"token": "PIN_OR_MASTER", "message": "...",
        #             "workspace_id": "...", "session_id": "...",
        #             "selected_skills": [...]}
        vk, role = get_auth_key(auth_msg["token"])
        if not vk:
            await websocket.send_json({"type": "error", "content": "Unauthorized"})
            await websocket.close(code=4001)
            return

        # 2. Build executor (identycznie jak handle_chat)
        # ... resolve LLM key, build SkillExecutor ...

        # 3. Stream execution
        async for event in executor.execute_stream(skill_config, message):
            await websocket.send_json(event)

        # 4. Graceful close
        await websocket.close()

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client (Ctrl+C or browser close)")
        # Zapisz częściowy chat do DB jeśli cokolwiek zostało wystreamowane
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
```

#### Protokół WebSocket — kontrakt JSON

**Klient → Serwer (first message = handshake):**
```json
{
  "token": "1234",
  "message": "Jakie mamy otwarte zadania?",
  "workspace_id": "default",
  "session_id": "cli-1720000000",
  "selected_skills": ["ODOO_BUSINESS_ANALYST"]
}
```

**Serwer → Klient (stream of events):**
```json
{"type": "log",   "content": "Iteracja 1: odpytuję LLM..."}
{"type": "token", "content": "W "}
{"type": "token", "content": "projekcie "}
{"type": "token", "content": "są "}
{"type": "log",   "content": "🔧 Wywołuję: odoo_search(...)"}
{"type": "log",   "content": "✅ odoo_search zwrócił 12 rekordów"}
{"type": "token", "content": "następujące "}
{"type": "token", "content": "zadania: ..."}
{"type": "done",  "content": "", "tools_used": ["odoo_search"]}
```

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Nowy endpoint `@app.websocket("/api/chat/stream")` | Handshake WS działa | [ ] |
| 3.2 | Auth via first JSON message (nie nagłówek, bo przeglądarka nie może) | 401 → close(4001) dla złego tokena | [ ] |
| 3.3 | Resolve LLM key z Vault (identycznie jak `handle_chat`) | Klucz OpenRouter pobierany z vault | [ ] |
| 3.4 | Iteracja po `execute_stream()` → `websocket.send_json()` | Każdy event przesyłany do klienta | [ ] |
| 3.5 | `WebSocketDisconnect` handler — log + partial chat save | Serwer NIE crashuje | [ ] |
| 3.6 | Backwards compatibility: `POST /api/chat` nienaruszone | Istniejący endpoint działa identycznie | [ ] |
| 3.7 | Testy: `tests/test_ws_endpoint.py` z `TestClient.websocket_connect()` | ≥5 testów (auth, stream, disconnect, error, no-llm fallback) | [ ] |
| 3.8 | **BRAMKA:** `python -m pytest tests/test_ws_endpoint.py -v` | ✅ ALL GREEN | [ ] |

---

### Sekcja B4 — FAZA 4: CLI/GUI WebSocket Client

> **Trigger:** Bramka 3.8 zamknięta
> **📁 Scope:** `smartmyodoo/http_client.py`, `smartmyodoo/cli.py`, `tests/test_cli_stream.py` [NEW]

#### Specyfikacja klienta WS

```python
# smartmyodoo/http_client.py — DODAĆ

import websockets
import asyncio

class SmartMyOdooClient:
    # ... istniejące metody login(), chat(), list_sessions() ...

    async def chat_stream(
        self,
        message: str,
        workspace_id: str,
        session_id: str,
        selected_skills: Optional[List[str]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """WS streaming — yields events from server."""
        ws_url = self.base_url.replace("http://", "ws://") + "/api/chat/stream"
        async with websockets.connect(ws_url) as ws:
            # Handshake
            await ws.send(json.dumps({
                "token": self._token,
                "message": message,
                "workspace_id": workspace_id,
                "session_id": session_id,
                "selected_skills": selected_skills or [],
            }))
            # Receive stream
            async for raw in ws:
                event = json.loads(raw)
                yield event
                if event.get("type") == "done":
                    break
```

#### Specyfikacja Rich Live rendering w CLI

```python
# smartmyodoo/cli.py — ZMODYFIKOWAĆ run() loop

from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

# W pętli run(), zamiast:
#   with self.console.status("Agent myśli..."):
#       result = self.callback(user_input)
#   self.print_agent_response(result["response"])

# Nowa logika:
async def _stream_response(self, user_input: str):
    """Streamuje odpowiedź token po tokenie w terminalu."""
    accumulated = ""
    tools_log = []

    with Live(
        Panel("[dim]Agent myśli...[/dim]", title="SmartMyOdoo Agent", border_style="blue"),
        console=self.console,
        refresh_per_second=12,
    ) as live:
        async for event in self.http_client.chat_stream(
            user_input, self.workspace_id, self.session_id
        ):
            if event["type"] == "token":
                accumulated += event["content"]
                live.update(
                    Panel(
                        Markdown(accumulated),
                        title="SmartMyOdoo Agent",
                        border_style="blue",
                        subtitle="[dim]▌streaming...[/dim]",
                    )
                )
            elif event["type"] == "log":
                tools_log.append(event["content"])
                live.update(
                    Panel(
                        Markdown(accumulated) if accumulated else "[dim]...[/dim]",
                        title="SmartMyOdoo Agent",
                        border_style="blue",
                        subtitle=f"[dim cyan]{event['content']}[/dim cyan]",
                    )
                )
            elif event["type"] == "done":
                live.update(
                    Panel(
                        Markdown(accumulated),
                        title="SmartMyOdoo Agent",
                        border_style="blue",
                    )
                )
```

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 4.1 | `chat_stream()` w `SmartMyOdooClient` (async WS generator) | Metoda istnieje, yield'uje eventy | [ ] |
| 4.2 | Refaktor `InteractiveCLI.run()` — `_stream_response()` z `rich.live.Live` | Tekst wylewa się płynnie | [ ] |
| 4.3 | Live log display: subtitle panelu Rich pokazuje bieżący log z agenta | "🔧 Wywołuję: odoo_search..." widoczne pod panelem | [ ] |
| 4.4 | Graceful Ctrl+C: `KeyboardInterrupt` → zamknięcie WS, powrót do promptu | CLI nie crashuje, serwer loguje disconnect | [ ] |
| 4.5 | Fallback: jeśli WS timeout/fail → automatycznie `POST /api/chat` (sync) | Brak regresji jeśli WS niedostępny | [ ] |
| 4.6 | Dodanie `websockets>=12.0` do `requirements.txt` i `pyproject.toml` | Zależność zadeklarowana | [ ] |
| 4.7 | Testy: `tests/test_cli_stream.py` — mock WS, weryfikacja rendering flow | ≥4 testy GREEN | [ ] |
| 4.8 | **BRAMKA:** `python -m pytest tests/ -v` — ALL GREEN (cały suite, brak regresji) | ✅ ALL GREEN | [ ] |

---

## 📦 Nowe zależności

```
# requirements.txt — dodać:
websockets>=12.0
```

```toml
# pyproject.toml → dependencies — dodać:
"websockets>=12.0"
```

> FastAPI ma wbudowaną obsługę WebSocket (nie wymaga dodatkowej paczki po stronie serwera). Paczka `websockets` jest potrzebna **wyłącznie jako klient** w CLI.

---

## 📈 Sprint Metrics

| Metryka | Przed (F7-02) | Cel (F7-02b) |
|---------|---------------|--------------|
| Czas do pierwszego tokena | 5-15s (pełna odpowiedź) | <1s (pierwszy token) |
| Widoczność tool calls | Brak (czarna skrzynka) | Live logs w terminalu |
| Protokół CLI↔Server | HTTP POST (sync) | WebSocket (stream) + HTTP fallback |
| Nowe pliki testów | — | 4 (`test_llm_stream`, `test_executor_stream`, `test_ws_endpoint`, `test_cli_stream`) |
| Szacowana liczba nowych testów | — | ~20 |
| Nowe LOC (szacunek) | — | ~350 (production) + ~300 (testy) |

---

## ✅ Sekcja E — Finalna Weryfikacja

> Wykonuje użytkownik lub `/qa` po zakończeniu Fazy 4.

| # | Check | Komenda | Oczekiwany wynik |
|---|-------|---------|------------------|
| V1 | Unit Tests | `python -m pytest tests/ -v` | ✅ ALL GREEN (≥ poprzednie + ~20 nowych) |
| V2 | CLI streaming E2E | `python -m smartmyodoo` → pytanie → obserwacja | ✅ Tekst "wylewa się" token-by-token |
| V3 | Live Logs E2E | Pytanie wymagające tool call → obserwacja | ✅ "🔧 Wywołuję: odoo_search" widoczne |
| V4 | Ctrl+C disconnect | `Ctrl+C` w trakcie streamu | ✅ CLI wraca do promptu, serwer nie crashuje |
| V5 | HTTP fallback | Wyłączenie WS w serwerze → CLI automatycznie fallback | ✅ Sync odpowiedź przez POST /api/chat |
| V6 | Backwards compat GUI | Przeglądarka → `http://127.0.0.1:8000` → chat | ✅ GUI działa identycznie |
| V7 | Backwards compat POST | `curl -X POST /api/chat ...` | ✅ Endpoint nienaruszone |

---

## 🏁 Definition of Done

- [ ] `llm_client.py` posiada `chat_stream()` z `stream=True`
- [ ] `executor.py` posiada `async execute_stream()` yielding zunifikowane JSON events
- [ ] `api.py` posiada `@app.websocket("/api/chat/stream")` z auth + graceful disconnect
- [ ] `http_client.py` posiada `chat_stream()` z `websockets` client
- [ ] `cli.py` używa `rich.live.Live` do token-by-token rendering
- [ ] `POST /api/chat` działa bez zmian (backwards compatibility)
- [ ] `python -m pytest tests/ -v` → ALL GREEN
- [ ] Sprint zamknięty w YAML frontmatter (`status: DONE`)

---

## SEKCJA E — LESSONS LEARNED (Mandatory)
> *Required before sprint closure. Entries never deleted.*

| # | Agent | Logic / PITFALL | Future Action / Pattern |
|---|-------|-----------------|-------------------------|
| — | — | *(do wypełnienia po zamknięciu sprintu)* | — |

> **Final Recommendation:** *(do wypełnienia po zamknięciu sprintu)*
