---
sprint_id: "F5-04"
workspace: "SmartMyOdoo"
status: "TODO"
created: 2026-06-05
closed: false
goal: "Zakończenie Fazy 5: Integracje Agenta z Odoo (Smart Chat, Fireflies, Shadow Mode, Projektowanie Odoo)"
prefix: "F5"
complexity: 9
roadmap_ref: "conductor/index.md"
tags: ["swarm", "odoo", "owl", "ui", "webhook", "best-practices"]
---

# SPRINT F5-04: Agent Swarm Integrations (Phase 4)

## 📈 PROGRESS BAR
- [x] `/arch` — Przygotowanie ADR-005 z zachowaniem Odoo Best Practices (Izolacja OWL, Banery w Formularzach)
- [ ] `/dev`  — Implementacja modułów Odoo (`smart_chat`, `fireflies_connector`, Odoo Projects logger)
- [ ] `/qa`   — Testy Manualne / Odoo Test framework (Python)
- [ ] `/doc`  — Zakończenie Walkthrough i ZAMKNIĘCIE Fazy 5
- [ ] **Release Gate**

---

## SEKCJA A: /arch (Architektura & Planowanie)

Architektura zatwierdzona przez ADR-005.

1. **User Stories:**
   - **US-1:** JAKO Użytkownik Odoo CHCĘ mieć czat-bota OWL w rogu systemu ŻEBY delegować zadania do Swarmu bez otwierania osobnej aplikacji.
   - **US-2:** JAKO Użytkownik CHCĘ otrzymywać duży baner nad edytowanym formularzem w "Shadow Mode" ŻEBY zminimalizować szansę przezoczenia proponowanych zmian i zjawisko tzw. "ślepoty na notyfikacje".
   - **US-3:** JAKO System CHCĘ w locie przyjmować webhooki z zewnętrznej aplikacji "Fireflies" ignorując sztywny format JSON-RPC Odoo ŻEBY nie gubić danych wejściowych.

---

## SEKCJA B: /dev (Rozbicie Zadań Odoo)

| Zadanie | Opis i DoD (Definition of Done) |
|---------|--------------------------------|
| B.1 | **Moduł `smart_chat` (OWL)**<br>Utworzenie `custom_addons/smart_chat/` i zagnieżdżenie widgetu JS w `web.layout`. Wpięcie komunikacji z klasą Dispatcher. |
| B.2 | **Moduł `fireflies_connector`**<br>Utworzenie webhooka w `controllers/main.py` bez `jsonrpc`. Użycie algorytmu dopasowania (Email/Domain) i wywołanie Agenta. |
| B.3 | **Integracja Shadow Mode**<br>Wstrzyknięcie komponentu UI nad formularzami uwalniającego strefę FSM (`ACTUATION`) pod przyciskiem [Potwierdź]. |
| B.4 | **Project Task Logger**<br>Logowanie postępu kroków FSM na żywo do zadań na kanbanie w Odoo (zamiast konsoli terminala). |

---

## SEKCJA C: /qa (Quality Assurance)

| Kryterium / Zadanie | Oczekiwany Rezultat | Werdykt |
|---------------------|---------------------|---------|
| C.1 Ładowanie UI    | Moduł `smart_chat` instaluje się bez błędów i w prawym rogu pojawia się chmurka (OWL). | ⬜ Pending |
| C.2 Webhook 200 OK  | Uderzenie curl/Postman na `/api/fireflies/webhook` z poprawnym hasłem zwraca HTTP 200, a nie Exception. | ⬜ Pending |

---

## 🏁 CLOSE CHECKLIST (Bramka Zamykająca)
- [ ] Moduły zintegrowane i przetestowane w środowisku deweloperskim.
- [ ] Cała Faza 5 i Track odznaczona w `conductor/tracks/agent-swarm_20260604/plan.md`.
