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
- **Pipeline Integration (7.1):** Pełna integracja Potoku Operacyjnego (Maszyny Stanów FSM) dla operacji agentów (AUTH → RECON → COGNITIVE → ACTUATION → SYNC) z polityką izolacji narzędzi, obsługą wyjątków, mechanizmem rollback na Sandbox DB i wstrzykiwaniem kluczy ze SmartMyVault. Audyt QA wykazał 17 usterek – wszystkie **17/17 zostały całkowicie naprawione**. Wdrożono solidną warstwę testów FSM (9/9 passed).
- **CLI Client-Server Mode (7.2):** Pełny refactor na klienta HTTP/WebSocket. Logi audytowe, obsługa strumieniowania (stream=True) dla UI, oraz powiadomienia (Live Logs) na żywo z FSM. Zabezpieczenia Token Governor'a zaimplementowane, odpowiedzi zapisywane do bazy z pełną historią sesji.

---

## 🔴 Czego nam brakuje (Pozostałości z Fazy 7)

To są elementy, które aktualnie wiszą na roadmapie jako niezrealizowane i blokują pełne zakończenie Fazy 7:

### 1. Advanced Features & Extended Ecosystem (7.3)
- [ ] Dry Run mode (flaga `--dry-run` do CLI, by można było zasymulować działanie agencji bez realnego wpływu).
- [ ] Integracja z systemami zewnętrznymi dla zadań: **Jira** oraz **Linear** (obecnie działa tylko `project.task` jako Task Picker Odoo).
- [ ] Opcja **Knowledge Seeding** (odłożona z Fazy 5) – zasilanie pamięci agentów danymi ze Stack Overflow i Odoo Forums.
- [ ] **Odoo Knowledge Base Expert Skill:** Integracja narzędzia [MarkItDown](https://github.com/microsoft/markitdown) jako natywnego skilla/narzędzia w SmartMyOdoo do ekstrakcji wiedzy z załączników (PDF, PPTX) oraz linków (np. YouTube) i konwersji do formatu Markdown.

---

## 🎯 Architektoniczna Konkluzja i Rekomendacja

Architektonicznie wykonaliśmy ogromny skok. Skomplikowana warstwa komunikacji z LLM została poprawnie zapakowana w asynchronicznego klienta WebSocketowego połączonego z silnikiem Maszyny Stanów (FSM).
Zarówno **Faza 7.1** (Pipeline Integration) jak i **Faza 7.2** (Websocket Streaming) są w **100% zrealizowane, przetestowane i zintegrowane**. Zlikwidowano wszystkie obejścia (mocki).

**Następne kroki:**
Możemy teraz płynnie przejść do **Fazy 7.3** (Advanced Features), a w pierwszej kolejności zająć się:
1. Implementacją trybu `Dry Run` (symulacji) i Shadow Mode (Banery akceptacji w Odoo).
2. Dodaniem wsparcia dla narzędzia **MarkItDown** jako specjalistycznego systemu Knowledge Base z parserem PDF/wideo.
3. Integracjami zewnętrznymi z Jirą/Linearem dla zintegrowanego zarządzania planem agentów.
