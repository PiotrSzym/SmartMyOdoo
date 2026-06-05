---
sprint_id: "F5-02"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-05
closed: true
goal: "Wdrożenie Agent Decision Protocol (ADP) oraz Maszyny Stanów (Execution Pipeline) z obsługą Scratchpad DB"
prefix: "F5"
complexity: 8
roadmap_ref: "conductor/index.md"
tags: ["swarm", "fsm", "adp", "rollback", "database-manager"]
---

# SPRINT F5-02: Agent Decision Protocol (ADP) & Execution Pipeline (FSM)

## 📈 PROGRESS BAR
- [x] `/arch` — Projektowanie hybrydowego mechanizmu bazy danych Odoo
- [x] `/dev`  — Implementacja Pipeline FSM i Odoo Database API
- [x] `/qa`   — Testy maszyny stanów z rollbackiem
- [x] `/doc`  — Walkthrough
- [x] **Release Gate**

---

## SEKCJA A: /arch (Architektura & Planowanie)

### 1. User Stories
1. **US-1:** JAKO Agent CHCĘ decydować o moich akcjach z pomocą ustrukturyzowanego promptu (ADP) ŻEBY nie psuć kontekstu biznesowego podczas działania.
2. **US-2:** JAKO Architekt CHCĘ transakcyjnej maszyny stanów FSM (Auth → Recon → Cognitive → Actuation → Sync) ŻEBY system był w stanie przerwać i zrollbackować akcję w dowolnym momencie.
3. **US-3:** JAKO System CHCĘ operować na sklonowanej bazie Odoo (Scratchpad DB) przed aplikowaniem zmian na główną bazę ŻEBY uniknąć ręcznego zrzucania `pg_dump` i desynchronizacji filestore.

### 2. Wybrane Technologie & Koncepcje
- **Agent Decision Protocol (ADP)** w postaci 8-krokowego Chain-of-Thought (Historia, Kontekst, Wersja, Analiza, Trudność, Plan itp.).
- **Maszyna Stanów (Pipeline)** zarządzająca stanem działania Agenta.
- **Odoo Database API** integracja punktu `/web/database/duplicate` do klonowania środowiska.

---

## SEKCJA B: /dev (Rozbicie Zadań)

| Zadanie | Opis i DoD (Definition of Done) | Wymagane Testy |
|---------|--------------------------------|----------------|
| B.1 | **Odoo Database Manager** (`db_manager.py`)<br>Funkcje do powielania bazy (`duplicate`) oraz rollbacku via native Odoo API. | Unit (Mocked) |
| B.2 | **Agent Decision Protocol** (`adp.py`)<br>Ustrukturyzowany prompt Chain-of-Thought i ewaluacja odpowiedzi modelu. | Unit |
| B.3 | **Maszyna Stanów FSM** (`pipeline.py`)<br>Definicja stanów (AUTH, RECON, COGNITIVE, ACTUATION, SYNC) oraz mechanizm `rollback()`. | Unit (FSM flow) |

---

## SEKCJA C: /qa (Quality Assurance)

| Kryterium / Zadanie | Oczekiwany Rezultat | Werdykt |
|---------------------|---------------------|---------|
| C.1 Testy FSM       | Błąd wyrzucony w trybie ACTUATION wywołuje procedurę `rollback()` i cofa do trybu SYNC. | ✅ Przeszło |
| C.2 Testy DB Manager| Prawidłowe logowanie HTTP błędów Odoo DB Manager API. | ✅ Przeszło |

---

## 🏁 CLOSE CHECKLIST (Bramka Zamykająca)
- [x] Wszystkie testy jednostkowe `pytest` z wynikiem zielonym.
- [x] `/qa` oficjalnie odznaczył Sekcję C.
