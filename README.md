# 🚀 SmartMyOdoo

SmartMyOdoo to inteligentny asystent AI do zarządzania, automatyzacji i audytowania systemu ERP Odoo. Gwarantuje ekstremalne skrócenie czasu rutynowych prac (np. napraw, audytu faktur, migracji produktów) wspierając się architekturą Model Context Protocol (MCP) oraz systemem bezpiecznego magazynowania kluczy (SmartMyVault).

---

## 🗂 Struktura Projektu

- **`smart_vault/`** — Moduł menedżera kluczy z lokalnym sejfem kryptograficznym chroniącym dostępy do baz danych, tokeny LLM (OpenRouter) oraz dane krytyczne.
- **`odoo_mcp_server/`** — Serwer integracyjny wykorzystujący FastMCP umożliwiający modelom językowym bezpośrednią konwersację i wykonywanie zdarzeń z bazą Odoo (za pośrednictwem XML-RPC).
- **`docs/`** — Katalog z pełną dokumentacją projektową (HLD, Business, Architektura oraz ADR-y).
- **`conductor/`** — System do zwinnego zarządzania pracą i sprintami, zawierający Tracki (Epic/Features) oraz definicje projektu.

---

## ⚡ Wymagania i Uruchomienie

1. Wymagane środowisko: **Python >= 3.11** oraz instancja docelowa Odoo.
2. Zależności projektu (zostaną określone w procedurze instalacji).
3. Do sprawnego działania należy skonfigurować swój sejf używając `smart_vault`. 

---

## 🛡️ Bezpieczeństwo
SmartMyOdoo kładzie główny nacisk na bezpieczeństwo. Cały kod został poddany twardej weryfikacji — nie używa bezpośrednio kluczy w locie i stosuje model **Shadow Mode** (operacje muszą być asynchronicznie zatwierdzone przez użytkownika zanim wejdą na produkcyjne Odoo).

*Wygenerowane przez Zespół SmartMyOdoo w ramach Sprintu 0 (Hardening).*
