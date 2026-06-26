---
sprint_id: "RAG-DOCKER-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-26
closed: 2026-06-26
goal: "Zaszyć wektorowy RAG (LanceDB + sentence-transformers + torch CPU) w obrazie Docker, by każdy `docker compose up` miał działający Shared Brain (degraded=False) BEZ pobierania czegokolwiek w runtime. Baza wektorowa + model embeddingów budowane w obrazie (offline-ready). FTS5/MEM-01 zostaje warstwą podstawową (zawsze on); RAG semantyczny to 'turbo' w kontenerze. Cel usera 2: każdy, kto ściągnie z GitHub, ma LanceDB działające — optymalnie (Docker pinuje Python 3.12, więc brak problemu wheeli torcha z Py3.14)."
prefix: "RAG-DOCKER"
complexity: 5
roadmap_ref: "Po MEM-01 (lekka pamięć FTS5). Zgłoszenie usera: 'dodaj rag do dockera'. Analiza 2026-06-26: torch nie ma wheeli na Py3.14 → Docker (3.12) to właściwy nośnik wektorowego RAG."
parent_sprint: "MEM-01"
tags: ["rag", "docker", "lancedb", "embeddings", "distribution", "offline"]
---

# 🧱 Sprint: RAG-DOCKER-01 — Wektorowy RAG w kontenerze

> **Architekt:** /arch | **Data:** 2026-06-26

## 0A. Problem (1 zdanie)
Wektorowy RAG (Shared Brain) jest zdegradowany wszędzie, bo obraz Docker nie ma ani bibliotek ML, ani modelu, ani zasianej bazy — więc nikt po `docker compose up` nie dostaje semantycznego wyszukiwania.

## 0B. Fakty (kod + DOWODY)
| Fakt | Dowód |
|---|---|
| `lancedb/sentence-transformers/pyarrow` NIE są w żadnym requirements | grep deps |
| Dockerfile nie kopiuje `knowledge/` ani nie zasiewa bazy | `Dockerfile` (przed fixem) |
| Baza `.agents/lancedb_store` gitignored + dockerignored | `.gitignore:8`, `.dockerignore:73` |
| Docker base = python:3.12-slim → pewne wheele torcha (inaczej niż Py3.14 lokalnie) | `Dockerfile:15` |
| Ścieżka bazy konfigurowalna `SMARTMYODOO_LANCEDB_PATH`, model `all-MiniLM-L6-v2` | `lancedb_client.py:20,25` |
| Jest seeder CLI `python -m smartmyodoo.swarm.brain.seed_knowledge <dir>` | `seed_knowledge.py:205` |

## ⚖️ Decyzje (/arch)
- **D1 — torch CPU-only.** Osobny plik `requirements-rag.txt` z `--extra-index-url .../whl/cpu`; local-version „+cpu" ma pierwszeństwo nad CUDA z PyPI → brak ~2GB CUDA. Instalacja osobnym `RUN` bez `--pre` (by nie wciągać prerelease torcha), z `-c constraints.txt` (numpy pinned spójnie ze stosem spaCy).
- **D2 — Baza + model ZASZYTE w obrazie (offline-ready).** W runtime stage: `COPY knowledge`, `ENV SMARTMYODOO_LANCEDB_PATH=/app/.lancedb`, pobranie modelu (`SentenceTransformer('all-MiniLM-L6-v2')`) + `seed_knowledge knowledge`. `HF_HOME=/app/.hfcache` (download robi root, potem `chown -R /app appuser` → appuser czyta w runtime).
- **D3 — Baza w OBRAZIE, nie na wolumenie /data.** Wiedza to wspólna treść statyczna (nie stan usera) → zaszyta w warstwie obrazu, każdy ma to samo. `/data` (vault/DB) zostaje osobnym wolumenem.
- **D4 — FTS5 (MEM-01) zostaje warstwą bazową.** RAG to opcjonalny turbo; rozdział `requirements-rag.txt` pozwala zbudować wariant bez RAG. Aplikacja działa też przy `degraded=True` (graceful).

## 🧱 Sekcja B — Zadania (/dev)
| # | Zadanie | Pliki | Weryfikacja | Status |
|---|---------|-------|-------------|--------|
| T1 | **requirements-rag.txt** (torch CPU + lancedb + pyarrow + sentence-transformers) | NEW `requirements-rag.txt` | build instaluje bez CUDA | ✅ DONE |
| T2 | **Dockerfile** — instalacja RAG (builder) + COPY knowledge + ENV + model + seed (runtime) | `Dockerfile` | obraz się buduje | ✅ DONE |
| T3 | **Smoke w kontenerze** — `degraded=False`, search_knowledge_base zwraca realny kontekst | — | docker run import LanceDBClient().degraded == False | ✅ DONE |

## 🛡️ Sekcja D — Security/Trust
- [ ] Brak sekretów w obrazie (bez zmian — .dockerignore nadal wyklucza vault/.enc/.db).
- [ ] Baza wiedzy = tylko dokumenty `knowledge/` (zero PII/danych Odoo).
- [ ] Obraz większy o ~300–500 MB (torch CPU + model) — świadomy koszt, udokumentowany.

## 🔬 DoD
- [x] Obraz buduje się zielono (torch CPU, bez CUDA).
- [x] `docker run … python -c "LanceDBClient().degraded"` → `False`.
- [x] `search_knowledge_base` w kontenerze zwraca realny kontekst (nie „tryb zdegradowany").
- [x] Rozmiar obrazu udokumentowany.

> Po RAG-DOCKER-01: każdy `docker compose up` ma działający semantyczny RAG offline, a lokalnie (Py3.14) FTS5/MEM-01 pokrywa pamięć bez torcha. Cel 2 usera spełniony optymalnie.

## ✅ Wyniki (LIVE, smoke obrazu)
- **Rozmiar: 3.83 GB → 2.29 GB** (−1.54 GB, −40%) — odchudzenie: `torch`+`sentence-transformers` → `fastembed` (ONNX Runtime już w obrazie).
- `LanceDBClient().degraded == False`, enkoder `_FastEmbedAdapter` (fastembed 0.8.0).
- `search('odoo orm rekordy')` → 3 realne trafienia; wektor 384-wym (zgodny ze schematem).
- Czat: `swarm.tools` importuje się (12 narzędzi), `mcp 1.28.0` (fastmcp OK po pinie); `torch` USUNIĘTY.
- App bootuje, `/api/status` = 200. Regresja 428/0.
- **Bonus fix:** pin `mcp==1.28.0` w constraints — `--pre` ciągnął `mcp 2.0.0a3` (alpha, bez `fastmcp`) → czat w kontenerze był złamany. Teraz działa.
