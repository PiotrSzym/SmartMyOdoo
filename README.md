# 🚀 SmartMyOdoo

SmartMyOdoo to inteligentny asystent AI do zarządzania, automatyzacji i audytowania systemu ERP Odoo. Gwarantuje ekstremalne skrócenie czasu rutynowych prac (np. napraw, audytu faktur, migracji produktów) wspierając się architekturą Model Context Protocol (MCP) oraz systemem bezpiecznego magazynowania kluczy (SmartMyVault).

---

## 🗂 Struktura Projektu

- **`smartmyodoo/`** — Zunifikowany pakiet aplikacji.
  - **`vault/`** — Moduł menedżera kluczy z lokalnym sejfem kryptograficznym chroniącym dostępy do baz danych, tokeny LLM (OpenRouter) oraz dane krytyczne.
  - **`mcp/`** — Serwer integracyjny MCP umożliwiający modelom językowym bezpośrednią konwersację i wykonywanie zdarzeń z bazą Odoo.
  - **`core/`** — Rdzeń aplikacji z bazą SQLite (z obsługą WAL), modelami danych (Pydantic, SQLAlchemy) oraz logiką autoryzacyjną dla serwera FastAPI.
- **📚 [`docs/`](docs/README.md)** — Pełna dokumentacja projektowa. **Zacznij od [mapy dokumentacji →](docs/README.md)** (klikalny indeks: CHANGELOG, Architektura/Design, Przewodniki, Sprinty, HLD, ADR).
- **`conductor/`** — System do zwinnego zarządzania pracą i sprintami, zawierający Tracki (Epic/Features) oraz definicje projektu.

---

## ⚡ Wymagania i Uruchomienie

1. Wymagane środowisko: **Python >= 3.11** oraz instancja docelowa Odoo.
2. Zależności projektu są w pliku `pyproject.toml`. Użyj `pip install -e .` aby zainstalować pakiet lokalnie.
3. Aplikacja udostępnia CLI: `python -m smartmyodoo --help`.
4. Aby uruchomić serwer FastAPI i Vault: `python -m smartmyodoo serve`.

---

## 🤝 Współdzielenie wiedzy i poświadczeń

Przekazujesz aplikację innej osobie/zespołowi? Wiedza zespołowa jedzie jako tekst
w gicie (folder [`knowledge/`](knowledge/)), a indeks wektorowy i sekrety zostają
lokalne. Po klonie odbuduj indeks: `python -m smartmyodoo seed --shared knowledge/`.

Trzy ścieżki dla sekretów (zespół = własny vault / migracja same-person = export /
organizacja = menedżer sekretów) opisuje przewodnik:
**[docs/guides/sharing_knowledge_and_secrets.md →](docs/guides/sharing_knowledge_and_secrets.md)**
(decyzja: [ADR-015](docs/adr/ADR-015-Knowledge-As-Source-Secrets-Stay-Local.md)).

---

## 🛡️ Bezpieczeństwo
SmartMyOdoo kładzie główny nacisk na bezpieczeństwo. Cały kod został poddany twardej weryfikacji — nie używa bezpośrednio kluczy w locie i stosuje model **Shadow Mode** (operacje są rejestrowane w bazie danych SQLite i muszą być zatwierdzone przez użytkownika zanim wejdą na produkcyjne Odoo). Posiada rygorystyczny `Token Governor` oraz lokalną bazę logów audytowych.

*Zaktualizowano przez Conductor w ramach migracji FastAPI-SQLite.*
