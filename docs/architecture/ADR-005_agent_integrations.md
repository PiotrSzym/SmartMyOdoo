# ADR 005: Agent Swarm Integrations (Phase 4)

## Status
Zatwierdzony (2026-06-05)

## Kontekst
W ramach Fazy 4 (Integracje Ekosystemu Odoo) w architekturze Agent Swarm, konieczne było podjęcie decyzji dotyczących fizycznego punktu styku agentów AI z interfejsem użytkownika (GUI) oraz z zewnętrznymi usługami (Fireflies AI). Wyzwanie polegało na zachowaniu izolacji kodu (Best Practices) oraz zapewnieniu najwyższego poziomu UX dla Shadow Mode, bez psucia natywnego kodu Odoo.

## Podjęte Decyzje (Best Practices)

### 1. Niezależny moduł `smart_chat` dla OWL
- **Decyzja:** Zamiast dodawać komponent czatu OWL do istniejących modułów (np. nadpisując `mail.chat`), utworzony zostanie całkowicie nowy, dedykowany moduł Odoo `custom_addons/smart_chat`.
- **Uzasadnienie (Best Practice):** Całkowita izolacja (Separation of Concerns). Pozwala to na włączanie/wyłączanie Chat Bota bez wpływu na rdzeń Odoo. Komponent `.js` OWL zakotwiczy się w głównym układzie UI (`web.layout`) jako niezależny "pływający" widget w prawym dolnym rogu.

### 2. Shadow Mode jako Baner Formularza (Form View Banner)
- **Decyzja:** Działania agenta wykonane "w cieniu" (Shadow Mode - zablokowane na etapie ACTUATION w FSM) nie będą generować ulotnych powiadomień systemowych (Systray). Zamiast tego, wstrzyknięty zostanie komponent banera renderowany nad obszarem arkusza (sheet) w `form_view`.
- **Uzasadnienie (Best Practice):** Kontekstowość. Użytkownik widzi dokładnie ten rekord, którego dotyczy proponowana przez AI zmiana, a ogromny przycisk `[Potwierdź zmiany Agenta]` minimalizuje ryzyko omyłkowego zatwierdzenia, wymuszając intencjonalną weryfikację.

### 3. Publiczny Webhook dla Fireflies omijający JSON-RPC
- **Decyzja:** Otwarcie kontrolera REST na ścieżce `/api/fireflies/webhook` z adnotacją `auth='public'` i ręczną weryfikacją nagłówków, bez użycia rzutowania struktury Odoo RPC.
- **Uzasadnienie (Best Practice):** Systemy 3rd party (takie jak Fireflies) wysyłają czysty JSON payload. Wymuszanie zgodności ze specyfikacją Odoo JSON-RPC `{"jsonrpc": "2.0", "params": {...}}` na zewnątrz powoduje tarcia architektoniczne i błędy integracji. Publiczny `http.Controller` z typem `type='http'` pozwala na surowy odbiór `request.httprequest.data`.

## Konsekwencje
1. Dodatkowy narzut na stworzenie nowego szkieletu modułu Odoo (`__manifest__.py`, struktury `static/src`).
2. Potrzeba rozszerzenia standardowego widoku `web.FormView` za pomocą XPath i OWL w celu obsługi banera Shadow Mode.
3. Znaczny zysk na stabilności i utrzymywalności architektury ekosystemu Odoo.
