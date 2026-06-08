---
title: "SPIKE: Analiza stanu Roadmapy (Faza 7)"
status: "DONE"
author: "Antigravity (Architekt)"
date: "2026-06-08"
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
---

# Raport ze Spike'a: Stan Roadmapy i braki z Fazy 7

## Kontekst
Polecenie wyzwalające: `/spike /arch co mamy na ordmap i czego nam pbrkuje ?`
Celem tego dokumentu jest zwięzłe podsumowanie tego, co zostało zrealizowane w projekcie `SmartMyOdoo` w stosunku do oficjalnej roadmapy, oraz identyfikacja zadań, które wciąż blokują zakończenie Fazy 7.

---

## 🟢 Co już mamy wdrożone (Faza 0 do Faza 6 + część Fazy 7)

Projekt jest na bardzo zaawansowanym etapie. Ukończyliśmy i zamknęliśmy Fazy od 0 do 6, co obejmuje m.in.:
- **Infrastrukturę i fundamenty:** SmartMyVault, bazę SQLite z migracjami Alembic, API oparte na FastAPI.
- **Odoo MCP Bridge:** XML-RPC (odczyt i zapis) połączony z Vaultem.
- **Token Governor & Project Hub:** Multi-Workspace UI, Task Binding (powiązanie z zadaniami w Odoo), auto-timesheety oraz Microsoft Presidio Middleware (anonimizacja PII).
- **Agent Swarm & Tool Calling:** Działający Dispatcher, rejestr narzędzi (Tool Engine z function callingiem OpenAI JSON Schema) oraz omijanie (bypass) Dispatchera przy ręcznym wyborze ról (dodane niedawno w ramach sprintów `S1.1`).
- **Premium GUI & CLI:** Rozbudowany interfejs webowy (panele skilli, chat, timeline, konfiguracja projektów) oraz CLI.

Z **Fazy 7 (Production Hardening & Client-Server Mode)** – która jest "w trakcie" – zrealizowaliśmy już:
- Dwustanowy widok projektów (Sprint F7-01).
- Zintegrowany Skill Panel i ręczny dobór skilli z badge'ami w oknie czatu (Sprinty ARCH-S1.1, HOTFIX-S1.1).
- Mechanizmy Auto-Timesheets.

---

## 🔴 Czego nam brakuje (Pozostałości z Fazy 7)

To są elementy, które aktualnie wiszą na roadmapie jako niezrealizowane i blokują pełne zakończenie Fazy 7:

### 1. Pipeline Integration (7.1)

**Opis Problemu:**
Obecnie `SkillExecutor` i `/api/chat` operują świetnie na luźnych konwersacjach, jednak nie są spięte w przewidywalny i bezpieczny "Potok Operacyjny". Aby agent mógł bezpiecznie i transakcyjnie operować na danych Odoo, musimy podpiąć jego działanie pod docelową Maszynę Stanów (FSM), zgodnie z założeniami ze sprintu F5-02 oraz politykami bezpieczeństwa.

**Fazy Maszyny Stanów (FSM) i Wymagania Integracyjne:**
1. **AUTH (Autoryzacja):** Inicjalizacja potoku z udziałem `SmartMyVault`. Należy wstrzyknąć credentials przy użyciu PIN-u Agenta zabezpieczonego przez KDF w sposób bezstanowy, izolując główny skarbiec od logów systemowych bota (zgodnie z **ADR-001: Dual-Auth Zero-Trust**).
2. **RECON (Analiza Sytuacji):** Uruchomienie narzędzi zwiadowczych. Zastosowanie ustrukturyzowanego promptu Agent Decision Protocol (ADP), podczas którego agent ma dostęp tylko do narzędzi w trybie "read-only" na klonie środowiska (Scratchpad DB).
3. **COGNITIVE (Myślenie):** Model LLM przetwarza zebrane w fazie RECON dane i układa plan akcji (Tool Engine przygotowuje argumenty JSON).
4. **ACTUATION (Działanie na Odoo):** Wywołanie zadeklarowanych akcji modyfikujących stan. Jeśli włączony jest **Shadow Mode** (zgodnie z **ADR-005**), działanie nie zapisuje wprost do bazy, lecz generuje Baner Formularza w Odoo do zatwierdzenia przez usera.
5. **SYNC (Zapis):** Finalna faza operacji. W przypadku powodzenia – synchronizacja stanu. Jeżeli w fazie ACTUATION wystąpi błąd (exception), FSM wyzwala procedurę `rollback()` i przywraca spójność danych.

**Kroki do zrealizowania:**
- [ ] Podłączenie Tool Engine do `pipeline.py` z restrykcjami dla poszczególnych faz (np. zablokowanie zapisu w fazie RECON).
- [ ] Utworzenie wrappera autoryzacyjnego wstrzykującego rozkodowany klucz ze SmartMyVault w fazie AUTH.
- [ ] Implementacja solidnej pętli obsługi wyjątków współpracującej z mechanizmem `rollback()`.

### 2. CLI Client-Server Mode (7.2)
- [x] Przejście CLI z bezpośredniego importowania funkcji na pełnego klienta HTTP odpytującego nasz backend FastAPI (Zrealizowane: F7-02).
- [x] Naprawa endpointu `/api/chat` – zwraca **prawdziwą odpowiedź LLM-a** z wykorzystaniem `SkillExecutor` (Zrealizowane: ARCH-F7-03).
- [x] Chat persistence — poprawne zapisywanie historii czatu (LLM i fallback) oraz logów audytowych w bazie (Zrealizowane: F7-02c).
- [x] Zaimplementowanie WebSocketów (streaming responses) do wyświetlania na żywo logów (Live Logs) w GUI/CLI z backendu (Zrealizowane: F7-02b).

### 3. Advanced Features & Extended Ecosystem (7.3)
- [ ] Dry Run mode (flaga `--dry-run` do CLI, by można było zasymulować działanie agencji bez realnego wpływu).
- [ ] Integracja z systemami zewnętrznymi dla zadań: **Jira** oraz **Linear** (obecnie działa tylko `project.task` jako Task Picker Odoo).
- [ ] Opcja **Knowledge Seeding** (odłożona z Fazy 5) – zasilanie pamięci agentów danymi ze Stack Overflow i Odoo Forums.
- [ ] **Odoo Knowledge Base Expert Skill:** Integracja narzędzia [MarkItDown](https://github.com/microsoft/markitdown) jako natywnego skilla/narzędzia w SmartMyOdoo do ekstrakcji wiedzy z załączników (PDF, PPTX) oraz linków (np. YouTube) i konwersji do formatu Markdown.

---

## 🔬 Analiza Wdrożeniowa dla `/api/chat` i WebSocketów

Aby wdrożyć dwa ostatnie, kluczowe punkty z sekcji 7.2, musimy zastosować się do naszych dotychczasowych Decyzji Architektonicznych (ADR) oraz wypracowanych dobrych praktyk:

### 1. Podpięcie LLM do `/api/chat` (HTTP POST)
**Co musi zostać zrobione:**
- Usunięcie hardkodowanej odpowiedzi z endpointu FastAPI.
- Zainicjalizowanie `SkillExecutor` w kontekście żądania webowego. Endpoint musi przyjąć payload (historię czatu, zapytanie), przekazać do Orkiestratora i zaczekać na gotową odpowiedź.
**Wymagania ADR i Dobre Praktyki:**
- **ADR-012 (LLM Context Guardrails):** Zanim endpoint wyśle całą historię do LLM, musi oszacować wielkość promptu i upewnić się, że nie przekracza limitu modelu (np. 150k tokenów dla Sonnet) oraz nie przepala budżetu (`TokenGovernor`).
- **ADR-011 (Logging & Sanitization):** Wszelkie błędy wykonania skilli przez agenta po stronie serwera muszą być logowane, ale z pominięciem danych wrażliwych PII. Wyjątki muszą powracać jako ustrukturyzowany JSON do klienta CLI/GUI.

### 2. Architektura WebSocket / Streaming
**Co musi zostać zrobione:**
- Utworzenie nowego endpointu `ws://.../api/chat/stream` w FastAPI.
- Przystosowanie `SmartMyOdooClient` (w konsoli) oraz interfejsu GUI do nawiązywania połączenia WS zamiast używania surowego `requests.post`.
**Wymagania ADR i Dobre Praktyki:**
- **Asynchroniczność:** Wykorzystanie w pełni asynchronicznych generatorów Pythona (Asyncio) i biblioteki do obsługi WebSockets w FastAPI (klasa `WebSocket`).
- **Streaming Tokenów:** Wywołanie modeli z OpenRouter z flagą `stream=True`. W miarę spływania chunków tekstu, FastAPI musi natychmiast przepychać je socketem do klienta.
- **Live Logs (Dual Stream):** Socket powinien wysyłać dwa typy wiadomości JSON: `{"type": "token", "content": "..."}` dla tekstu od LLM oraz `{"type": "log", "content": "Wywołuję funkcję odoo_search..."}` informując usera o tym, co agent robi w "czarnej skrzynce".
- **Obsługa zerwań (Graceful Disconnect):** Endpoint musi poprawnie łapać wyjątek `WebSocketDisconnect`, aby nie crashować całego serwera, gdy klient w terminalu wciśnie `Ctrl+C`.

---

## 🎯 Architektoniczna Konkluzja i Rekomendacja

Architektonicznie jesteśmy na etapie, w którym GUI i narzędzia agentów wyprzedziły główny mechanizm wyzwalający. Naszym najwyższym priorytetem powinna być teraz **naprawa `/api/chat`** i przejście na **pipeline FSM (7.1 i 7.2)**, ponieważ interfejs webowy i CLI muszą przestać polegać na hardkodowanych mockach w zakresie komunikacji z LLM-em. Bez tego, mimo zaawansowanego GUI i zarejestrowanych skilli, nie mamy w pełni funkcjonalnego "Client-Server Mode".
