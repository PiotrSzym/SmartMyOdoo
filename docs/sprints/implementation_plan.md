# SPIKE: WebSockets (Live Logs & Streaming) dla SmartMyOdoo

Spike architektoniczny weryfikujący wymagane zmiany w kodzie w celu przejścia z synchronicznego klienta HTTP (Faza 7.2) na klienta ze strumieniowaniem po WebSocket, umożliwiając pojawianie się odpowiedzi litera po literze oraz otrzymywanie Live Logów z działania agenta.

## Cel
Docelowo chcemy, aby w interfejsach (CLI i GUI) tekst pisał się "na żywo" oraz aby pojawiały się komunikaty live-log z wywoływania poszczególnych skilli (np. "Agent szuka w Odoo..."). Faza 7.2 przekształciła aplikację w klasycznego klienta HTTP, a teraz pora dodać WebSocket w celu odblokowania streamingu.

## Proponowane Zmiany Architektoniczne

Wdrożenie WebSocketów i streamingu przechodzi przez wszystkie warstwy systemu:

### 1. Zmiany w Kliencie LLM (`smartmyodoo/swarm/llm_client.py`)
- Należy dodać nową metodę `chat_stream(self, messages, tools)`, która wywołuje `litellm.completion(..., stream=True)`.
- Metoda ta powinna być asynchronicznym generatorem, który yield'uje poszczególne chunki zwracane przez API OpenRouter. Należy obsłużyć zarówno chunki tekstu (`delta.content`), jak i fragmenty opisujące wywołania narzędzi (`delta.tool_calls`).

### 2. Zmiany w Orkiestratorze (`smartmyodoo/swarm/executor.py`)
- Obecna metoda `execute()` jest blokująca. Konieczne jest stworzenie asynchronicznego generatora np. `execute_stream()`.
- Generator zamiast czekać na pełen wynik, przetwarza strumień wiadomości asynchronicznie, yield'ując zunifikowane wiadomości JSON dla WebSocketów:
  - Dla tekstu: `yield {"type": "token", "content": chunk_text}`.
  - Dla logów z funkcji: `yield {"type": "log", "content": f"Wywołuję narzędzie {func_name}..."}`.
- **Wyzwanie tool calling w streamingu:** W trybie stream API przesyła argumenty narzędzia w ułamkach (np. JSON podzielony na części). Executor musi zbuforować te części (deltas), połączyć w pełny JSON po otrzymaniu flagi zakończenia, wykonać lokalną logikę z `TOOL_REGISTRY` i wstrzyknąć wynik do historii konwersacji, a następnie ewentualnie wznowić streamowanie od LLMa.

### 3. Zmiany w Backendzie API (`smartmyodoo/api.py`)
- Rejestracja nowego endpointu FastAPI: `@app.websocket("/api/chat/stream")`.
- **Autoryzacja WebSocket:** W przypadku WS w przeglądarkach często nie możemy wysłać nagłówka `Authorization`. Sugeruję wykorzystanie parametru w URI (`?token=...`) lub wykonanie protokołu Handshake jako pierwszej wiadomości wysyłanej do połączonego socketu.
- Obsługa połączonego gniazda: odbiór wiadomości od klienta (treść pytania, sesja) -> uruchomienie `executor.execute_stream(...)` -> `await websocket.send_json(msg)` -> obsługa zapisu z użyciem `ChatRepository`.
- **Graceful Disconnect:** Bezpieczne łapanie `fastapi.WebSocketDisconnect` by zapobiec wywaleniu procesu serwera, gdy user nagle wyłączy CLI. Zapis wykonanego do tej pory logu i chatu w bazie.

### 4. Zmiany w Kliencie HTTP/CLI (`smartmyodoo/http_client.py` i `smartmyodoo/cli.py`)
- `httpx` służy tylko do HTTP. W CLI trzeba będzie obsłużyć WebSockety. Użycie nowej zewnętrznej zależności, np. `websockets` dla Pythona, aby utworzyć połączenie. W klasie klienta pojawia się nowa metoda `chat_stream(message, ...)`.
- Interfejs `InteractiveCLI` wymaga dużej przebudowy. Zamiast `Console.print()` na końcu, musimy na żywo odświeżać widok w terminalu. W bibliotece `rich` idealnie sprawdzi się mechanizm `rich.live.Live` wyświetlający np. tabelę lub panel, który jest ciągle mutowany (aktualizowana zawartość ekranu) po otrzymaniu zdarzenia z socketa.

## Open Questions

> [!WARNING]
> Pytania wymagające weryfikacji przez eksperta/architekta zanim ruszymy do kodowania:
> 1. Czy decydujemy się na dodanie do dependencies paczki `websockets` lub używamy natywnie asynchronicznego klienta socketów dostępnego w `httpx-ws`?
> 2. UX W CLI: Kiedy agent włącza wyszukiwanie (co potrwa np. 4 sekundy), co ma dokładnie robić ekran? Zatrzymywać rysowanie tekstu i po prostu pisać na czerwono/niebiesko na dole status, a po skończeniu usuwać status i streamować dalej?
> 3. Bezpieczeństwo GUI (Frontend): GUI również będzie w przyszłości podłączane do tego endpointu. Zatem musimy zapewnić uniwersalny protokół JSON (bez specyfik typowych tylko dla Pythona). Używamy `{"type": "...", "content": "..."}`?

## Wymagane aktualizacje konfiguracji
#### [MODIFY] pyproject.toml
#### [MODIFY] requirements.txt
Włączenie do zależności obsługi klienta WS (np. pakiet `websockets`).

## Verification Plan

### Testowanie manualne
1. Uruchomienie deweloperskiego środowiska i wydanie komendy typu "Jakie mamy otwarte zadania w projekcie X?".
2. Zauważenie od razu pierwszych liter w CLI (natychmiastowe strumieniowanie).
3. Wizualne ostrzeżenie i spinner oznaczające `{"type": "log", "content": "Wywołuję funkcję odoo_search..."}`.
4. Kontynuacja strumieniowania po zwróceniu wyników przez funkcję.
5. Awaryjne przerwanie (Ctrl+C) w połowie strumienia — serwer loguje ucięcie, nie crashuje, a klient gładko wraca do znaku zachęty.
