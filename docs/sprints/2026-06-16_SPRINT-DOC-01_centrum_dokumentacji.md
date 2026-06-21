---
sprint_id: "DOC-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-16
closed: 2026-06-21
goal: "Wbudowane Centrum Dokumentacji w panelu: best-practice sekcje + wyszukiwarka + kompendium wiedzy, dostępne globalnie z paska nawigacji"
prefix: "DOC"
complexity: 3
roadmap_ref: "Faza 8 (po FIX-02) — UX/dokumentacja"
tags: ["docs", "ui", "search", "knowledge-base", "ux"]
---

# 📚 Sprint: DOC-01 — Centrum Dokumentacji (w aplikacji)

> **Architekt:** /arch | **Owner:** /dev + /doc | **Review:** /gf-review | **Data:** 2026-06-16

---

## 📋 Sekcja A — Cel & Reguły

### Problem (stan zastany)
Skrót „📖 Dokumentacja" istnieje tylko na zakładce **Skarbiec** (`index.html:122`) i otwiera **statyczny,
nieaktualny** modal (`#docs-modal`) — sama notka o bezpieczeństwie, port `5050` (realnie `8000`),
**bez** powiązania z żywą dokumentacją w `docs/` (README index, sprinty, HLD, CHANGELOG). Użytkownik
nie ma w aplikacji jednego miejsca z wiedzą o produkcie.

### Cel biznesowy
Jedno **Centrum Dokumentacji** dostępne z **każdej** zakładki (pasek nav), podzielone na sekcje wg
best-practice, z **wyszukiwarką** (filtr w czasie rzeczywistym) i **kompendium wiedzy** (Odoo, pułapki,
FAQ). Treść zgodna z realnym stanem (FastAPI gateway, swarm, Vault, routery, FIX-02).

### Sekcje (best-practice podział)
1. 🚀 **Start** — czym jest, uruchomienie, logowanie (PIN vs Master).
2. 🏛️ **Architektura** — gateway FastAPI, routery + deps-module, swarm (Dispatcher/Executor/Pipeline), MCP, RAG.
3. 🔐 **Bezpieczeństwo** — Vault (KEK/Fernet), PII (Presidio), sandbox fail-closed, TokenGovernor, distributed lock.
4. 🗝️ **Skarbiec & Klucze** — typy kluczy (odoo_data/odoo_timesheet/llm_provider), jak AI bierze creds bez haseł.
5. ⚙️ **Modele AI** — tiery CHEAP/STANDARD/PREMIUM, budżet, cache, degradacja, retry/fallback.
6. 🧠 **Skille & Agenci** — persony, dispatcher, routing modeli per skill, Shadow Mode.
7. 🛠️ **Sprinty & Roadmap** — FIX-01, KEY-01, FIX-02 (S3/S5) + linki do `docs/`.
8. 📚 **Kompendium wiedzy** — Odoo Docker/edycje/hosting, pułapki, best practices, FAQ.

### ⚖️ Zasady
- **Treść = prawda:** odzwierciedla realny kod (port 8000, 240 testów, routery, deps-module) — koniec staleness.
- **Offline-first:** treść wbudowana po stronie klienta (działa bez sieci); głębsze materiały = linki do repo `docs/`.
- **Dostępność globalna:** wejście z paska nav, nie tylko ze Skarbca.

---

## 🧱 Sekcja B — Podział Zadań

| # | Zadanie | Pliki | Status |
|---|---------|-------|--------|
| DOC-01-1 | Nowa zakładka „📖 Dokumentacja" w nav (globalna) + ekran `#docs-screen` | `ui/index.html` | ⬜ |
| DOC-01-2 | Komponent `docs.js`: model treści (8 sekcji), sidebar, render, **wyszukiwarka** (filtr po tytule+treści) | `ui/js/components/docs.js` (NEW) | ⬜ |
| DOC-01-3 | Rejestracja zakładki w `canvas.js`; repoint starego przycisku Skarbca na nową zakładkę | `ui/js/components/canvas.js`, `ui/index.html` | ⬜ |
| DOC-01-4 | Kompendium wiedzy + FAQ + klikalne linki do repo `docs/` | `docs.js` | ⬜ |
| DOC-01-5 | Test strukturalny (zakładka/sekcje/wyszukiwarka obecne, brak stale `5050`) | `tests/test_ui_docs.py` (NEW) | ⬜ |

---

## 🔬 Sekcja C — Weryfikacja & Wyjście

### Definition of Done
- [ ] „📖 Dokumentacja" w pasku nav działa na każdej zakładce; otwiera `#docs-screen`.
- [ ] 8 sekcji z treścią zgodną z kodem; wyszukiwarka filtruje wpisy w czasie rzeczywistym.
- [ ] Kompendium wiedzy + FAQ + linki do `docs/` (repo).
- [ ] Brak nieaktualnego portu `5050`; test strukturalny zielony; pełna suita bez regresji.

> **Po DOC-01:** opcjonalnie endpoint `/api/docs` serwujący indeks z `docs/` (dynamiczne) — follow-up.
