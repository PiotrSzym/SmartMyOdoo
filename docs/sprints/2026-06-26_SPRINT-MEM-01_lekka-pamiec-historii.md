---
sprint_id: "MEM-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-26
closed: 2026-06-26
goal: "Dać asystentowi PAMIĘĆ historii rozmów i rozwiązanych problemów BEZ ciężkiego wektorowego RAG. Cel usera: (1) na natywnym środowisku (Py3.14, .venv-qa) móc przypominać historię chatów + rozwiązane problemy; (2) po wysłaniu na GitHub każdy kto sklonuje ma to działające — optymalnie. Decyzja: lekka pamięć FTS5 (sqlite wbudowany, ZERO torch/lancedb) zamiast wektorowego RAG, który na Py3.14 nie ma wheeli i obciąża dystrybucję. LanceDB zostaje opcjonalnym 'turbo' (graceful degrade), a FTS5 to domyślna pamięć działająca wszędzie."
prefix: "MEM"
complexity: 4
roadmap_ref: "Zgłoszenie usera 2026-06-26: RAG natywnie z historią chatów/problemów + optymalna dystrybucja. Reframe /arch: do tego celu (228 wiadomości + 79 sprintów) FTS5 wystarcza i jest dramatycznie prostsze niż torch+LanceDB."
parent_sprint: null
tags: ["memory", "fts5", "history", "recall", "no-ml", "distribution", "trust"]
---

# 🧱 Sprint: MEM-01 — Lekka pamięć historii (SQLite FTS5)

> **Architekt:** /arch | **Data:** 2026-06-26

## 0A. Problem (1 zdanie)
Asystent nie pamięta wcześniejszych rozmów ani rozwiązanych problemów, a wektorowy RAG (LanceDB+torch) jest dla tego overkillem i nie działa na Py3.14 ani „za darmo” u każdego, kto sklonuje repo.

## 0B. Fakty (kod + DOWODY)
| Fakt | Dowód |
|---|---|
| Wektorowy RAG zdegradowany lokalnie — brak `lancedb/sentence-transformers/pyarrow` w `.venv-qa` | `pip` ModuleNotFoundError; `LanceDBClient.degraded=True` |
| `.venv-qa` = Python **3.14** → wheele torcha często brak; Docker = 3.12 | `python --version`, `Dockerfile:15` |
| FTS5 dostępne w sqlite Pythona (3.46.1) | test `CREATE VIRTUAL TABLE … USING fts5` ✅ |
| Materiał mały: 228 wiadomości / 65 sesji + 79 sprintów + 7 notatek | zapytania SQLite / `ls` |
| Historia chatów w `chat_messages` (content, session_id, workspace_id, created_at) | schemat tabeli |
| Sprinty = „rozwiązane problemy” w `docs/sprints/*.md` | `ls` |

## ⚖️ Decyzje (/arch)
- **D1 — FTS5 zamiast wektorów.** Pamięć = wirtualna tabela `memory_fts` (sqlite FTS5, wbudowane). ZERO nowych zależności → działa na Py3.14 i u każdego, kto sklonuje (każdy ma sqlite). Indeks: chaty + sprinty + knowledge.
- **D2 — Reindex przy każdym wyszukaniu.** Dane małe (setki rekordów) → przebudowa indeksu jest tania i gwarantuje świeżość (zero stale-bugów).
- **D3 — Izolacja czatów per workspace, dokumenty globalne.** Filtr `workspace_id` dotyczy CZATÓW (prywatne); sprinty/knowledge są wspólne.
- **D4 — Bezpieczne zapytanie FTS.** Tekst usera → tokeny (≥2 znaki) jako frazy łączone OR; eliminacja znaków specjalnych FTS (zero błędów składni / wstrzyknięć).
- **D5 — Fallback dla wektorowego RAG.** Gdy LanceDB zdegradowany, `search_knowledge_base` sięga do FTS5 zamiast zwracać „tryb zdegradowany” (naprawia UX z poprzedniego zgłoszenia).
- **D6 — Dystrybucja: nie wymagać LanceDB.** FTS5 to domyślna pamięć (zawsze on). Wektorowy RAG = opcjonalny turbo (Docker/venv 3.12), bez blokowania startu aplikacji.

## 🧱 Sekcja B — Zadania (/dev)
| # | Zadanie | Pliki | Testy | Status |
|---|---------|-------|-------|--------|
| T1 | **Moduł pamięci** — `memory_search.py`: ensure_index, reindex (chaty+sprinty+knowledge), search_memory, format_hits, bezpieczne `_fts_query` | NEW `core/memory_search.py` | unit: sanitizacja, reindex, search, izolacja ws | ✅ DONE |
| T2 | **Tool `search_history`** + fallback FTS w `search_knowledge_base` | `swarm/tools.py` | unit: tool zwraca trafienia | ✅ DONE |
| T3 | **Wpięcie w domyślnego asystenta** (allowed_tools + hint w prompcie) | `api_routers/chat.py` | LIVE: „czy rozmawialiśmy o…” | ✅ DONE |
| T4 | **Regresja + LIVE** | testy | 0 failed; LIVE recall działa natywnie | ✅ DONE |

## 🛡️ Sekcja D — Security/Trust
- [x] Brak wstrzyknięć FTS (tokenizacja, zero surowego inputu w MATCH).
- [x] Izolacja czatów per workspace (filtr); dokumenty globalne świadomie.
- [ ] Wynik narzędzia przechodzi przez anonimizację PII executora (jak inne tool-results).

## 🔬 DoD
- [x] FTS5 działa, reindex z realnych danych (309 rekordów).
- [x] search_memory znajduje realną historię (traktory, WRITE-02, ERR-01) — LIVE skrypt.
- [x] LIVE chat: „czy rozmawialiśmy o traktorach?” → asystent przypomina (search_history).
- [x] Fallback: gdy LanceDB degraded, „baza wiedzy” odpowiada z FTS, nie „tryb zdegradowany”.
- [x] Regresja 0 failed (osobny przebieg).

> Po MEM-01: asystent pamięta rozmowy i rozwiązane problemy NATYWNIE (Py3.14, zero ML), a każdy kto sklonuje repo ma tę pamięć za darmo. Wektorowy RAG zostaje opcjonalnym turbo (Docker) — to osobny, mniejszy sprint RAG-DOCKER-01.
