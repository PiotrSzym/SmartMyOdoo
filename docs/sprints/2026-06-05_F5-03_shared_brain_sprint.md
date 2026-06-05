---
sprint_id: "F5-03"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-05
closed: true
goal: "Wdrożenie lokalnej bazy wektorowej LanceDB (RAG) z darmowym modelem osadzania (sentence-transformers) oraz SQLite"
prefix: "F5"
complexity: 8
roadmap_ref: "conductor/index.md"
tags: ["swarm", "brain", "lancedb", "rag", "sqlite"]
---

# SPRINT F5-03: Global Knowledge Sync (Shared Brain)

## 📈 PROGRESS BAR
- [x] `/arch` — Wybór darmowego modelu `sentence-transformers` i delegacja scrapowania do tooli
- [x] `/dev`  — Implementacja LanceDB, SQLite Metadata i RAG API
- [x] `/qa`   — Testy wstawiania i wyszukiwania wektorowego (z mockami bibliotek ML)
- [x] `/doc`  — Walkthrough
- [x] **Release Gate**

---

## SEKCJA A: /arch (Architektura & Planowanie)

### 1. User Stories
1. **US-1:** JAKO Agent CHCĘ wyszukiwać rozwiązania i instrukcje semantycznie (RAG) ŻEBY nie zgadywać kontekstu na podstawie słów kluczowych.
2. **US-2:** JAKO Architekt CHCĘ, by cała wiedza (wektory) znajdowała się lokalnie w `LanceDB` z użyciem darmowego modelu (np. `all-MiniLM-L6-v2`) ŻEBY system był w pełni zero-trust i pozbawiony kosztów API.
3. **US-3:** JAKO System CHCĘ synchronizować metadane plików (np. skille, instrukcje MD) w lokalnym `SQLite` ŻEBY śledzić zmiany w plikach bez niepotrzebnej re-wektoryzacji.

---

## SEKCJA B: /dev (Rozbicie Zadań)

| Zadanie | Opis i DoD (Definition of Done) | Wymagane Testy |
|---------|--------------------------------|----------------|
| B.1 | **Metadata Tracker** (`sqlite_metadata.py`)<br>Baza SQLite przechowująca hash plików (MD/YAML) uodparniająca na wielokrotną wektoryzację. | Unit |
| B.2 | **Vector Store** (`lancedb_client.py`)<br>Inicjalizacja LanceDB. Automatyczne generowanie wektorów przez `sentence-transformers`. | Unit (Mocked) |
| B.3 | **RAG API** (`rag_api.py`)<br>Główny interfejs `ask_brain(query)` dostępny dla FSM (Cognitive phase). | Unit |

---

## SEKCJA C: /qa (Quality Assurance)

| Kryterium / Zadanie | Oczekiwany Rezultat | Werdykt |
|---------------------|---------------------|---------|
| C.1 Integracja API  | `ask_brain` poprawnie formatuje top-K wyników i podaje źródło. | ✅ Przeszło |
| C.2 SQLite Cache    | Dodanie tego samego pliku dwukrotnie nie wywołuje ponownej wektoryzacji (ochrona CPU). | ✅ Przeszło |

---

## 🏁 CLOSE CHECKLIST (Bramka Zamykająca)
- [x] Wszystkie testy jednostkowe `pytest` z wynikiem zielonym.
- [x] `/qa` oficjalnie odznaczył Sekcję C.
