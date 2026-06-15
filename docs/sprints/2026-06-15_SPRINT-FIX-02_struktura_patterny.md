# 🧱 SPRINT FIX-02 — Struktura i Patterny (dług po audycie)

> **Data:** 2026-06-15 · **Wersja silnika:** 5.3 · **Status:** PLANOWANY
> **Poprzednik:** [EPIC-FIX-01](2026-06-15_EPIC-FIX-01_naprawa_weryfikacja.md) (S1+S2 ✅, [PR #1](https://github.com/PiotrSzym/SmartMyOdoo/pull/1))
> **Źródło:** `.agents/AUDIT_REPORT.md` (pozostałe znaleziska 🟠/🟡 z wymiarów Struktura + Patterny)

## Cel
Spłacić dług strukturalny i wdrożyć brakujące wzorce stacku — **bez zmiany zachowania**
(refaktor na stabilnym, zielonym zestawie 188 testów). Zasada [Evidence Before Claims](2026-06-15_EPIC-FIX-01_naprawa_weryfikacja.md#2--zasada-nadrzędna--evidence-before-claims) obowiązuje: każda zmiana z testem.

## Zakres

### S3 — Struktura (owner `/audyt` + `/dev`, review `/gf-review`)
| # | Zadanie | Plik | DoD (test/dowód) |
|---|---|---|---|
| S3.1 | Rozbić `api.py` (1315 l., 30+ endpointów) na `APIRouter` per domena + warstwa serwisowa; `Depends()` zamiast globali; modele Pydantic zamiast surowych dict | `api.py` → `api/routers/*`, `services/*` | istniejące testy API przechodzą **bez zmian zachowania** (188 nadal zielone) |
| S3.2 | Ekstrakcja wspólnych helperów z `execute`/`execute_stream` (koniec rozjazdu polityk: red flags/read_only/audit/PII) | `swarm/executor.py` | jeden zestaw helperów; testy obu ścieżek dzielą logikę bezpieczeństwa |
| S3.3 | Konsolidacja dwóch warstw PII (`mcp/pii_*` vs `security/pii/*`) do jednej kanonicznej | `security/pii/` | jedna implementacja; duplikat usunięty; recognizery PL spójne; testy PII zielone |
| S3.4 | `attach_existing_scratchpad()` zamiast dostępu do `sandbox._active_scratchpad` z `pipeline.py` (enkapsulacja) | `swarm/sandbox.py`, `swarm/pipeline.py` | test: pipeline ustawia scratchpad publicznym API; brak dostępu do `_`-pól |

### S5 — Patterny (owner `/dev` + `/gf-review`)
| # | Zadanie | Plik | DoD (test/dowód) |
|---|---|---|---|
| S5.1 | `litellm.Router` z retry/backoff/fallback + cache na Redis; `temperature`/`max_tokens` do `SkillConfig` | `swarm/llm_client.py` | test: 429/5xx → retry; fallback model; parametry z konfiguracji |
| S5.2 | Wzorce Redis: distributed lock (`SET NX PX`) dla `execute_approved_proposals` (TOCTOU), rate-limit, FSM przez pub/sub | `core/queue.py`, `api.py` | test: równoległe approve → tylko jedno wykonanie |
| S5.3 | RAG: chunking z overlapem po granicach, próg distance + re-ranker, mock RAG **sygnalizuje degradację** (nie fabrykuje kontekstu) | `swarm/brain/rag_api.py`, `lancedb_client.py` | test: mock zwraca flagę degradacji; chunki z overlapem |

## ⛔ NIE robić
- Nie „refaktorować" `SkillConfig`/`Dispatcher` pod pretekstem God Node (>25 edges) — kohezyjny fan-in.
  Zamiast tego skorygować próg metryki grafu (ART.21) dla fan-in core abstractions.

## Kolejność
```
S3.1 (api.py) — fundament, odblokowuje czystsze testy domenowe
   └─ S3.2/S3.3 (dedup executor + PII) równolegle
S3.4 (enkapsulacja sandbox)
S5.* po S3 (ulepszenia na uporządkowanej strukturze)
```

## Definicja ukończenia
- [ ] `api.py` rozbity (APIRouter + serwisy), bez globali w handlerach
- [ ] `execute`/`execute_stream` współdzielą helpery; jedna warstwa PII
- [ ] `litellm.Router` (retry/fallback/cache); distributed lock dla approve; RAG z overlapem
- [ ] Suite ≥ 188 passed (zero regresji), pokrycie krytycznych modułów ≥ 85%
- [ ] Re-audyt `/audyt` potwierdza zamknięcie znalezisk Struktura/Patterny
