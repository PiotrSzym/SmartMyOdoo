---
sprint_id: "MCP-01"
workspace: smartmyodoo
status: BACKLOG
created: 2026-06-05
closed: null
goal: "Pełna łączność odczyt/zapis z Odoo (v16-v19) przez XML-RPC, rozbudowa klienta i integracja z Shadow Mode"
prefix: MCP
complexity: 5
roadmap_ref: "Faza 2: Odoo MCP Bridge"
epic_ref: "EPIC-F2-MCP"
tags: ["odoo", "xml-rpc", "mcp", "shadow-mode"]
---

# 🚀 Sprint: MCP-01 Odoo MCP Bridge (XML-RPC CRUD)

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-05 | **Bazuje na:** odoo-mcp-bridge_20260604 plan.md

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Zapewnienie pełnej łączności (odczyt i zapis) pomiędzy lokalnym agentem AI a systemem Odoo (v16-v19) przy użyciu XML-RPC. Pozwoli to na automatyzację powtarzalnych zadań ERP bez ręcznego pisania kodu do komunikacji XML-RPC, a integracja z SQLite (Shadow Mode) ochroni przed niechcianymi zmianami w systemie produkcyjnym.

### Metryka sukcesu (DoD)
Działający `OdooClient` obsługujący metody `search_read`, `write`, `create`, `unlink`, `fields_get`. Testy z użyciem `pytest test_odoo_client.py -v` świecące na zielono dla wszystkich nowych operacji, a nowe narzędzia MCP poprawnie używające SQLite do zapisywania i wykonywania propozycji.

### ⚖️ ZASADY SPRINTU — Podsumowanie dla Użytkownika

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Faza 2 (Shadow Mode) nie może się rozpocząć, dopóki Faza 1 (Rozbudowa klienta) nie będzie w 100% pokryta zielonymi testami jednostkowymi.

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Zadania wymagają tworzenia testów w pierwszej kolejności (TDD). Oznaczone w etapach jako RED i GREEN.

#### Zasada 3: SCOPE ISOLATION 🔴
Kluczowe pliki to izolowane komponenty: `smartmyodoo/core/odoo_client.py`, testy dla OdooClient oraz moduł Shadow Mode dla SQLite.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────┐
│  FAZA 1 (Rozbudowa OdooClient)       │
│  [CRUD XML-RPC]                      │
│  [Async Wrapper]                     │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: pytest test_odoo_client.py
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Shadow Mode z SQLite)       │
│  [Propozycje zapisu]                 │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Test bazy SQLite
               ▼
┌──────────────────────────────────────┐
│  FAZA 3 (Nowe Narzędzia MCP)         │
│  [create, delete, execute tools]     │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: OdooClient CRUD Extensions

> **Trigger:** Rozpoczęcie implementacji XML-RPC CRUD
> **📁 Scope:** `smartmyodoo/core/` i `tests/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | 🔴 RED — Testy dla `write`, `create`, `unlink` z mockowanym XML-RPC | Plik testowy zawiera failing tests | [x] |
| 1.2 | 🟢 GREEN — Implementacja operacji CRUD w `OdooClient` | Kod kliencki pomyślnie mockuje nowe API | [x] |
| 1.3 | Async wrapper na `xmlrpc.client` (np. przez pool wątków / to_thread) | OdooClient korzysta z async/await przy I/O | [x] |
| 1.4 | **BRAMKA:** Weryfikacja testów `OdooClient` | ✅ `pytest tests/ -v` na zielono dla klienta Odoo | [x] |

---

### Sekcja B2 — FAZA 2: Shadow Mode Integration (SQLite)

> **Trigger:** Faza 1 ukończona (zielona bramka)
> **📁 Scope:** Tabele SQLite, obsługa persistencji (CRUD propozycji)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Rozszerzenie logiki bazy o Shadow Mode: `create`, `update`, `delete` | Struktura gotowa na nowe typy operacji | [x] |
| 2.2 | 🔴 RED — Testy propozycji zapisu/tworzenia w SQLite | Failing tests dla nowych typów w Shadow Mode | [x] |
| 2.3 | 🟢 GREEN — Implementacja z persystencją w tabeli `proposals` | SQL/ORM poprawnie obsługuje dodawanie propozycji | [x] |
| 2.4 | **BRAMKA:** Mechanizm akceptacji/odrzucenia propozycji | ✅ Narzędzie/Funkcja pomyślnie przetwarza aprobaty | [x] |

---

### Sekcja B3 — FAZA 3: Nowe Narzędzia MCP

> **Trigger:** Faza 2 ukończona (zielona bramka)
> **📁 Scope:** `smartmyodoo/mcp/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Implementacja narzędzia `create_odoo_record` (MCP) | Narzędzie rejestrowane w MCP Fast | [x] |
| 3.2 | Implementacja narzędzia `delete_odoo_record` (MCP + Shadow Mode) | Narzędzie rzuca poprawne zdarzenia do Shadow Mode | [x] |
| 3.3 | Implementacja `execute_approved_proposals` (batch) | Narzędzie z sukcesem parsuje zatwierdzenia | [x] |
| 3.4 | **BRAMKA:** Zaktualizowany status i weryfikacja klienta MCP | ✅ Endpointy działają w kliencie MCP | [x] |

---

## 📊 PROGRESS BAR

| # | Faza | /dev | /qa | /doc | Status |
|---|--------|:----:|:---:|:----:|:------:|
| 1 | OdooClient CRUD Extensions | ✅ | ✅ | ✅ | ✅ |
| 2 | Shadow Mode Integration (SQLite) | ✅ | ✅ | ✅ | ✅ |
| 3 | Nowe Narzędzia MCP | ✅ | ✅ | ✅ | ✅ |

**Podsumowanie:** 3/3 ✅ Done | Blokujący: —

---

## ✅ Sekcja E — Finalna Weryfikacja

> Wykonuje użytkownik lub `/qa` po zakończeniu wszystkich faz.

| # | Check (Core Pillars) | Komenda | Oczekiwany wynik |
|---|----------------------|---------|------------------|
| V1 | [Testy Jednostkowe] | `pytest -v` | Wszelkie testy zakończone sukcesem (100% green) |
| V2 | [Serwer MCP] | `mcp run smartmyodoo` | Proces MCP startuje bez wyjątków |
| V3 | [Inspekcja Narzędzi] | Ręczny klient / Claude | Agenci widzą operacje Write, Create, Unlink |

---
_Wygenerowane przy użyciu szablonów TeamEngine (sprint_plan_multidev_template.md)._
