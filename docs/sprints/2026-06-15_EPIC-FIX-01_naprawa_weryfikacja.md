# 🛠️ EPIC FIX-01 — Naprawa i Weryfikacja SmartMyOdoo

> **Data:** 2026-06-15 · **Wersja silnika:** 5.3 · **Źródło:** `.agents/AUDIT_REPORT.md` (39 potwierdzonych znalezisk)
> **Właściciel:** `/arch` · **Wykonawcy:** `/sec`, `/dev`, `/odoo`, `/audyt`, `/qa`, `/gf-review`
> **Status:** W TRAKCIE — S4.1 ✅, S1.1 ✅, S1.2 ✅ (2026-06-15)

## 0. Postęp realizacji
| Zadanie | Status | Dowód (test) |
|---|---|---|
| **S4.1** Konfiguracja pytest (asyncio_mode, izolacja e2e, cov) | ✅ DONE | `pytest` = **164 passed / 0 failed / 0 error** (było 125/9/33); e2e wykluczone markerem |
| **S1.2** Master password fail-closed (koniec domyślnego `admin`) | ✅ DONE | `tests/test_sandbox.py::test_sandbox_fail_closed_without_master_password` |
| **S1.1** Pseudonimizacja PII na ścieżce czat/pipeline (obie: `execute` + `execute_stream`) | ✅ DONE | `tests/security/test_pii_pipeline.py` (no-leak do LLM + deanon dla usera) |
| **S2.1** Kontrakt Dispatcher→chat() (messages=[...], choices[0].message.content) | ✅ DONE | `tests/swarm/test_dispatcher.py` (contract + None bez crasha) |
| **S2.2** TokenGovernor podłączony do LLM (record usage + pre-flight hard-block) | ✅ DONE | `tests/swarm/test_llm_cost_governance.py` (spent≠0, hard-block) |
| **S2.3** Sandbox: fail-closed + redirect narzędzi na scratchpad (ODOO_DB) | ✅ DONE | `tests/swarm/test_sandbox_isolation.py` (blokada write bez izolacji + redirect+restore) |
| **S2.6** Routing person/skilli do pipeline (koniec hardkodu ODOO_DEVELOPER) | ✅ DONE | `tests/swarm/test_pipeline_routing.py` (routed skill + fallback) |
| **S2.5** Workery: uczciwe handlery (shadow_ops real, not_implemented zamiast fake completed) + graceful shutdown | ✅ DONE | `tests/workers/test_main_worker.py` |
| S1.3, S1.4, S2.4 (queue reliable) | ⬜ TODO | — |

> Stan testów: **179 passed / 0 failed / 2 deselected (e2e)**.

---

## 1. Cel

Naprawić defekty z audytu **oraz udowodnić realnymi testami, że funkcjonalności faktycznie istnieją i działają** — nie jako atrapy. Audyt wykazał, że część „zaawansowanej" infrastruktury *udaje* działanie (TokenGovernor `spent=0.0`, sandbox dekoracyjny, kolejka bez producentów, Dispatcher z bugiem kontraktu). Ten epic likwiduje rozjazd deklaracji z rzeczywistością.

## 2. 🔴 ZASADA NADRZĘDNA — Evidence Before Claims

> **Żadne zadanie nie jest „done" bez testu dowodowego, który:**
> 1. **pada PRZED naprawą** (czerwony — udowadnia, że problem istniał),
> 2. **przechodzi PO naprawie** (zielony — udowadnia naprawę),
> 3. **NIE jest mockiem udającym działanie** — mock dozwolony tylko na granicy zewnętrznej (litellm, sieć Odoo, Redis→fakeredis), nigdy do „zasymulowania" testowanej logiki.
> 4. Zakaz self-declared `[x]` bez logu z przebiegu testu (ART.19).

Bramka pokrycia: dodać `pytest-cov` + `--cov-fail-under=70` w CI; krytyczne moduły (`executor`, `dispatcher`, `sandbox`, `queue`, `token_governor`, `pii`) ≥ 85%.

## 3. 🔬 Reality Matrix — co jest deklarowane vs co faktycznie działa

Stan z audytu + test, który to ROZSTRZYGA (czerwony dziś → zielony po naprawie):

| Funkcjonalność | Deklarowane | Stan faktyczny (audyt) | TEST DOWODOWY (rozstrzyga) |
|---|---|---|---|
| **Pseudonimizacja PII (RODO)** | ✅ w UI | ❌ tylko ścieżka MCP; czat/pipeline wysyła surowe PII do LLM | Wyślij wiadomość z PESEL/NIP → assert: payload do (zamockowanego) litellm **nie zawiera** surowego PII; odpowiedź zde-anonimizowana |
| **Sandbox / shadow izolacja** | ✅ | ❌ dekoracyjny — narzędzia nie idą na klon; fail-open | Operacja write z `SANDBOX_ENABLED=true` → assert trafia na **scratchpad DB**, nie na `original_db`; gdy klon padnie → **RedFlag/wyjątek**, nie cichy write |
| **Kontrola kosztów (TokenGovernor)** | ✅ | ❌ `spent` zawsze `0.0`, `usage` ignorowane | Po wywołaniu LLM (mock z `usage`) → assert `spent > 0`; przekroczenie budżetu → **hard-block** |
| **Klasyfikacja intencji (Dispatcher)** | ✅ | ❌ `chat(str)` → None → `json.loads(None)` TypeError | `classify_intent("dodaj fakturę")` → poprawny intent; `chat()` dostaje `messages=[...]`, czyta `choices[0].message.content` |
| **Kolejka zadań (JobQueue/workers)** | ✅ skalowalna | ❌ brak producentów, brak ack/TTL, race, martwe workery | enqueue→worker→`completed`; crash po BRPOP przed ack → zadanie **nie ginie**; 2× równoległy dequeue → brak duplikatów |
| **Routing person/skilli** | ✅ | ❌ pipeline hardkoduje `ODOO_DEVELOPER`, persona `'H'` | `classify_intent` → pipeline używa **wybranego** SkillName/persony, nie hardkodu |
| **Master password (bezpieczeństwo baz)** | — | ❌ fallback `admin` (fail-open) | Brak `ODOO_MASTER_PASSWORD` → **wyjątek/fail-closed**, nigdy `admin` |

> Wniosek: 7 reklamowanych zdolności wymaga dowodu. Dopóki test nie jest zielony — funkcjonalność traktujemy jako **nieistniejącą**.

### 3a. Zmierzony baseline (2026-06-15, `pytest`)
Realny przebieg `python -m pytest` (167 testów): **125 ✅ · 9 ❌ · 33 💥 ERROR**.

| Obszar | Wynik | Diagnoza |
|---|---|---|
| `tests/test_api.py` (23) | 💥 `OperationalError` | brak testowej bazy/migracji — API niesprawdzalne |
| `tests/test_queue.py` (3) | 💥 `Runner.run() cannot...` | brak `asyncio_mode='auto'` (→ S4.1); kolejka niesprawdzalna |
| `test_executor_stream`, `test_api_stream` (4) | ❌ RuntimeError | ten sam async-bug na ścieżce streamingu |
| fireflies webhook (3), e2e (2) | ❌ | wymaga środowiska Odoo / serwera+chromium |
| rdzeń: pii, recognizers, sandbox, registry, llm_stream | ✅ 125 | logika jednostkowa istnieje |

**Krytyczny wniosek:** „125 passed" ≠ „działa". Zielone testy dają fałszywe poczucie bezpieczeństwa — `test_sandbox` sprawdza enter/exit, nie realne przekierowanie narzędzi; `pii_middleware` roundtrip zielony, ale niewpięty w czat; `shadow_mode` testuje in-memory dict, nie DB. **Pierwszym krokiem każdego sprintu jest naprawa konfiguracji testów (S4.1) + test dowodowy sprawdzający REALNE zachowanie.**

---

## 4. Sprinty

### 🛡️ S1 — Bezpieczeństwo krytyczne (owner `/sec`, wsparcie `/odoo`)
Blokuje wydanie. Najpierw.

| # | Zadanie | Plik | Test dowodowy (DoD) |
|---|---|---|---|
| S1.1 | Pseudonimizacja PII na ścieżce czat/pipeline (anonymize/deanonymize per-sesja, mapping nietrwały) | `swarm/executor.py`, konsolidacja `security/pii/` | `tests/security/test_pii_pipeline.py`: PESEL/NIP/email w wejściu i w wyniku `odoo_search` → brak surowego PII w payloadzie do litellm; round-trip deanonimizacja |
| S1.2 | Usunąć fallback `admin`; fail-closed bez `ODOO_MASTER_PASSWORD`; hasło z Vault | `swarm/sandbox.py`, `swarm/db_manager.py` | `tests/swarm/test_sandbox_security.py`: brak env → `ValueError`/RedFlag; nigdy `admin` |
| S1.3 | CORS: jawna lista origin (koniec `*`+credentials) + rate-limiting/lockout na auth i endpointy LLM | `api.py` | `tests/api/test_security_headers.py`: obce Origin odrzucone; N nieudanych PIN → lockout |
| S1.4 | Średnie/niskie sec: path traversal `scaffold_module`, hasła z compose→`.env`, Redis `requirepass`, redakcja `master_pwd` w logach | `swarm/tools.py`, `docker-compose.yml`, `core/queue.py`, logi | testy regex nazwy modułu; brak sekretów w logu (assert na capturze) |

### 🧩 S2 — Reality Check: atrapy → realne działanie (owner `/dev`)
Sedno epica. Każde zadanie = atrapa zamieniona w działającą funkcję + test, że faktycznie działa.

| # | Zadanie | Plik | Test dowodowy (DoD) |
|---|---|---|---|
| S2.1 | Naprawić kontrakt `Dispatcher → chat()` (messages=[...], `choices[0].message.content`) | `swarm/dispatcher.py`, `swarm/llm_client.py` | `tests/swarm/test_dispatcher_contract.py`: klasyfikacja zwraca intent; brak TypeError na None |
| S2.2 | Podłączyć TokenGovernor do `OpenRouterClient` (DI, odczyt `response.usage`, pre-flight estimate, hard-block) | `mcp/token_governor.py`, `swarm/llm_client.py` | `tests/mcp/test_token_governor_live.py`: po wywołaniu `spent>0`; przekroczenie → blok |
| S2.3 | Sandbox faktycznie przekierowuje narzędzia na scratchpad; fail-closed | `swarm/sandbox.py`, `swarm/executor.py`, `swarm/pipeline.py` | (jak S1.2) + `test_sandbox_isolation.py`: write idzie na scratchpad, nie original |
| S2.4 | JobQueue niezawodna: RPOPLPUSH/Streams + ack + TTL + atomowy status; albo jawnie oznaczyć eksperymentalne i NIE aktywować w deploy | `core/queue.py`, `workers/main_worker.py` | `tests/test_queue_reliability.py`: crash przed ack → redelivery; równoległy dequeue bez duplikatów; `job:*` ma TTL |
| S2.5 | Implementacja handlerów workera (shadow_ops→`execute_approved_proposals`) lub status `not_implemented` | `workers/main_worker.py` | `tests/workers/test_main_worker.py` (fakeredis): completed/failed/unknown/graceful shutdown |
| S2.6 | Przepiąć routing person/skilli do pipeline (`classify_intent` przed pipeline; koniec hardkodu `ODOO_DEVELOPER`/`'H'`) | `swarm/pipeline.py`, `api.py` | `tests/swarm/test_routing.py`: różne intencje → różne SkillName/persona |

### 🏛️ S3 — Struktura i jakość (owner `/audyt` + `/dev`, review `/gf-review`)

| # | Zadanie | Plik | DoD |
|---|---|---|---|
| S3.1 | Rozbić `api.py` (1315 l.) na `APIRouter` per domena + warstwa serwisowa; `Depends()` zamiast globali; modele Pydantic zamiast dict | `api.py` → `api/routers/*`, `services/*` | testy endpointów przechodzą bez zmian zachowania; brak importów w handlerach |
| S3.2 | Ekstrakcja wspólnych helperów z `execute`/`execute_stream` (koniec rozjazdu polityk: red flags/read_only/audit) | `swarm/executor.py` | jeden zestaw helperów; testy obu ścieżek dzielą logikę bezpieczeństwa |
| S3.3 | Konsolidacja dwóch warstw PII (`mcp/pii_*` vs `security/pii/*`) do jednej kanonicznej | `security/pii/` | jedna implementacja; duplikat usunięty; recognizery PL spójne |
| S3.4 | Zastąpić `except Exception: pass` logowaniem + zawęzić typy; naprawić `WorkerDaemon.stop()`; `attach_existing_scratchpad` zamiast dostępu do `_active_scratchpad` | `api.py`, `workers/`, `pipeline.py` | brak połkniętych wyjątków; graceful shutdown bez wyjątków |

### 🧪 S4 — Testy i bramki (owner `/qa`)

| # | Zadanie | DoD |
|---|---|---|
| S4.1 | `pytest-cov` + `[tool.pytest.ini_options]` (`asyncio_mode='auto'`) + `--cov-fail-under=70` (krytyczne ≥85%) | CI mierzy pokrycie i blokuje regresję |
| S4.2 | Test round-trip `shadow_mode` przez DB (nie in-memory dict) + `accept_proposal('zły_id') is False` | `mcp/test_shadow_mode.py` |
| S4.3 | Test `OpenRouterClient.chat()` (kwargs bez stream, None przy wyjątku); testy pętli narzędziowej executora (rollback/iteracje/audyt) | nowe testy |
| S4.4 | Naprawić mutację globalnego `TOOL_REGISTRY` w testach (`monkeypatch.setitem`/fixture z teardown) | brak zanieczyszczenia rejestru |

### 🧩 S5 — Patterny stacku (owner `/dev` + `/gf-review`) — po S1/S2

| # | Zadanie | DoD |
|---|---|---|
| S5.1 | `litellm.Router` z retry/backoff/fallback + cache na Redis; parametry (`temperature`/`max_tokens`) do `SkillConfig` | test: 429/5xx → retry; fallback model |
| S5.2 | Wzorce Redis: distributed lock (`SET NX PX`) dla `execute_approved_proposals` (TOCTOU), rate-limit, FSM przez pub/sub | test: równoległe approve → tylko jedno wykonanie |
| S5.3 | RAG: chunking z overlapem po granicach, próg distance + re-ranker, mock RAG **sygnalizuje degradację** (nie fabrykuje kontekstu) | test: mock zwraca flagę degradacji, nie fałszywy kontekst |

---

## 5. ⛔ NIE robić (z audytu)
- **Nie refaktorować `SkillConfig`/`Dispatcher` pod pretekstem „God Node >25 edges"** — adwersaryjna weryfikacja wykazała, że to **kohezyjny fan-in, nie God Object**. Zamiast tego skorygować próg metryki grafu (`graphify`/ART.21) dla fan-in core abstractions.

## 6. Protokół weryfikacji (bramka wyjścia epica)
1. **Dual Run (ART.18):** testy krytyczne uruchomione na `mock=true` i `mock=false` (realny Odoo/Redis na staging).
2. **Reality Matrix zielona:** wszystkie 7 testów dowodowych z §3 przechodzą; każdy ma log z przebiegu (ART.19).
3. **Pokrycie:** `--cov-fail-under` spełnione; krytyczne moduły ≥85%.
4. **Re-audyt:** ponowny `graphify update .` + skrót audytu `/audyt` — 2 krytyczne i atrapy zamknięte.
5. **Brak nowych połkniętych wyjątków** (grep `except.*: pass` = 0 w kodzie produkcyjnym).

## 7. Kolejność i zależności
```
S1 (bezpieczeństwo) ──► wydanie odblokowane
   └─ S1.2 ⊂ S2.3 (sandbox)
S2 (reality check)  ──► funkcje faktycznie działają  ◄── rdzeń epica
S4 (testy) biegnie RÓWNOLEGLE do S1/S2 (każda naprawa = test)
S3 (struktura) po S2 (refaktor na stabilnym zachowaniu)
S5 (patterny) na końcu (ulepszenia po naprawie krytycznych)
```

## 8. Definicja ukończenia EPICA
- [ ] 2 krytyczne (PII pipeline, master password) zamknięte + testy zielone
- [ ] Reality Matrix: 7/7 funkcjonalności udowodnione realnym testem
- [ ] Pokrycie krytycznych modułów ≥85%, globalne ≥70% (bramka CI)
- [ ] `api.py` rozbity, duplikacje PII i `execute/execute_stream` zlikwidowane
- [ ] Re-audyt potwierdza zamknięcie atrap; brak deklaracji RODO bez pokrycia
