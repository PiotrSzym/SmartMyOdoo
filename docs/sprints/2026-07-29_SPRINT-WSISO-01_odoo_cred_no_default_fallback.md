---
sprint_id: "WSISO-01"
workspace: "SmartMyOdoo"
status: "🟡 In Progress"
created: 2026-07-29
closed: null
goal: "Zamknięcie cichego fallbacku poświadczeń Odoo do workspace `default`. Gdy wybrany jest KONKRETNY (nie-default) workspace bez własnego ODOO_DATA, system NIE może po cichu połączyć się z instancją Odoo innego workspace (dziś: grfood→myodoo). Zamiast tego: jawny błąd „ten workspace nie ma połączenia Odoo". Zamyka cross-client data exposure (echo audytu #2 A-1 staging→prod)."
prefix: "WSISO"
complexity: 4
roadmap_ref: "Bug live 2026-07-29: user przełączył na workspace grfood (rwyszewski-gourmetfoods-main-15940999), ale odczyty Odoo szły do myodoo (default). Root: resolver.py:77 akceptuje workspace LUB default → przy braku creds grfood zwraca default(myodoo). Powiązane: audyt#2 A-1 (staging→prod przy dual-instance), AZURE-01 (provisioning klucza per workspace), [[odoo-dual-instance-setup]]."
parent_sprint: null
tags: ["security", "impl", "workspace-isolation", "odoo-auth", "cross-client", "fail-closed"]
---

# 🧱 Sprint: WSISO-01 — Koniec cichego fallbacku Odoo do `default`

> **Architekt:** /arch | **Data:** 2026-07-29 | **Routing:** T1–T4 → /dev; WSZYSTKIE → ping /sec (izolacja klienta) | **Trigger:** bug live grfood→myodoo

## 0A. Problem (1 zdanie)
Wybór konkretnego (nie-`default`) workspace bez własnego `ODOO_DATA` powoduje **ciche połączenie z Odoo workspace'u `default`** (grfood→myodoo) — odczyty/operacje trafiają na instancję INNEGO klienta, mimo że UI pokazuje właściwy workspace.

## 0B. Fakty — 3 WEKTORY cichego fallbacku (kod + dowód, 2026-07-29)
| # | Wektor | Dowód | Ryzyko |
|---|---|---|---|
| **V1** | `resolve_credential` akceptuje `workspace_id` **LUB `"default"`** → przy braku creds workspace zwraca default | `vault/resolver.py:77` `if cred.workspace_id not in (workspace_id, "default"): continue` | 🔴 cross-client (grfood→myodoo) |
| **V2** | Legacy fallback `{ws}_ODOO` → **`default_ODOO`** gdy brak sekretu workspace | `api_routers/workspaces.py:86-88` | 🔴 to samo, ścieżka timesheet/workspace |
| **V3** | Gdy `_inject_odoo_creds` nie wstrzyknie (cred=None) → `OdooClient` czyta **ENV** `ODOO_URL/ODOO_PASSWORD` | `mcp/odoo_client.py:51-64` (ENV fallback), `chat.py:51` (inject tylko `if cred`) | 🟠 warunkowe (gdy ENV Odoo ustawione) |

**Dowód że przełączenie UI DZIAŁA** (problem nie tu): log serwera `GET /api/chat/sessions?workspace_id=rwyszewski-gourmetfoods-main-15940999` — UI wysyła poprawny workspace; historia/sekrety/audyt są scope'owane dobrze. Wektor to WYŁĄCZNIE wybór poświadczeń Odoo.

**Wołający `resolve_credential` (zakres zmiany V1):**
- `chat.py:50` — ODOO_DATA (napraw: bez fallbacku)
- `workspaces.py:69` — ODOO_TIMESHEET, `:71` — ODOO_DATA (napraw)
- `resolver.py:102` (`resolve_llm_key`) — LLM_PROVIDER (**ZOSTAW fallback** — klucz OpenRouter jest globalny, dziedziczenie z default jest POŻĄDANE)

**Nie-wektor (zweryfikowane):** stan ContextVar między żądaniami — `set_odoo_creds` woła się w tasku żądania; contextvars kopiują się per-task (izolacja), więc creds z żądania A nie wyciekają do B. Ryzyko realne to V3 (ENV), nie stale-context.

## 🧭 Niezmiennik (invariant do wymuszenia)
> **Tylko workspace `default` może dziedziczyć poświadczenia Odoo** (z default-tagowanego sekretu / legacy `default_ODOO` / ENV). **Konkretnie wybrany nie-`default` workspace używa WYŁĄCZNIE własnego `ODOO_DATA`; przy jego braku → jawny, głośny błąd, NIGDY fallback do innej instancji.**

LLM_PROVIDER wyłączony z tej reguły (klucz globalny — fallback do default OK).

## ⚖️ Decyzje (/arch)
- **D1 — V1: parametr `allow_default_fallback` w `resolve_credential`.** Sygnatura: `resolve_credential(..., allow_default_fallback: bool = True)`. Gdy `False`: kandydaci TYLKO z `cred.workspace_id == workspace_id` (bez „default"). Domyślnie `True` (zachowanie LLM niezmienione). Wołający Odoo (`chat.py:50`, `workspaces.py:69/71`) przekazują `allow_default_fallback=False`. Uwaga: dla `workspace_id="default"` `False` i tak zwraca default-creds (dokładne dopasowanie) — czyli workspace default działa normalnie.
- **D2 — V2: legacy `default_ODOO` tylko dla default.** `_resolve_odoo_creds` (`workspaces.py:86-88`): `secret_key = f"{ws_id}_ODOO"; if secret_key not in vault_data and ws_id == "default": secret_key = "default_ODOO"`. Dla nie-default brak → `HTTPException(400, "Brak poświadczeń Odoo dla workspace {ws}")` (już jest 400 niżej — dopiąć komunikat z nazwą workspace).
- **D3 — V3: blokada ENV/fallbacku dla wybranego nie-default bez creds.** `_inject_odoo_creds` gdy `cred is None` i `workspace_id != "default"`: ustaw jawny marker „workspace nieskonfigurowany" (nowy ContextVar `_odoo_unconfigured_ws` lub sentinel w `set_odoo_creds`). `OdooClient.__init__`/`connect`: gdy marker aktywny dla wybranego workspace → `raise OdooWorkspaceUnconfigured("Workspace '{ws}' nie ma skonfigurowanego połączenia Odoo — dodaj klucz API (ODOO_DATA)")` ZAMIAST fallbacku do ENV. **Zachowaj ENV dla `default`/`vault run`** (CLI: ws=default, ENV ustawione — działa jak dziś).
- **D4 — UX: czytelny błąd w czacie.** Executor/handler łapie `OdooWorkspaceUnconfigured` i zwraca użytkownikowi jasny komunikat (nie generyczny „błąd narzędzia"), sanityzowany (`type(e).__name__` + własny message bez sekretów).
- **D5 — Zakres NIE obejmuje:** opt-in „dziedzicz Odoo z default" per workspace (over-engineering; jawność > wygoda), zmiany semantyki workspace `default`, migracji istniejących sekretów.

## ⚠️ Nota migracyjna (behavior change)
Setupy, które ŚWIADOMIE liczyły na jedno Odoo z `default` współdzielone przez wszystkie workspace'y, po tej zmianie zobaczą jawny błąd dla nie-default workspace bez własnego `ODOO_DATA`. To zamierzone (bezpieczeństwo > cicha wygoda). Migracja: dodać `ODOO_DATA` per workspace (patrz AZURE-01 Sekcja C) albo świadomie trzymać operacje na `default`.

## 🧱 Sekcja B — Zadania (/dev, TDD: Red→Green→Refactor)
| # | Zadanie | Pliki | Testy (DOWODOWE) | Status |
|---|---------|-------|-------|--------|
| T1 | **V1: `allow_default_fallback` w resolverze** + Odoo-wołający `=False`; LLM bez zmian | `vault/resolver.py:69-99`, `api_routers/chat.py:47-84`, `api_routers/workspaces.py:67-78` | ✅ RED (sonda /dev na kodzie sprzed fixu): `resolve_credential(grfood)`→`default(myodoo)`. GREEN: `test_t1_nondefault_without_creds_returns_none_no_fallback` (→None), `test_t1_default_workspace_still_resolves_with_no_fallback`, `test_t1_nondefault_with_own_creds_resolves_own`, `test_t1_regres_llm_key_still_falls_back_to_default` (LLM fallback ZACHOWANY). Wszystkie PASS. | ✅ DONE |
| T2 | **V2: legacy `default_ODOO` tylko dla default** + komunikat z nazwą ws | `api_routers/workspaces.py:85-97` | ✅ RED: `_resolve_odoo_creds(grfood)`→`default_ODOO(myodoo)` bez błędu. GREEN: `test_t2_nondefault_missing_creds_raises_400_with_ws_name` (HTTPException 400 „Brak poświadczeń Odoo dla workspace grfood", bez URL/hasła), `test_t2_default_still_uses_default_odoo_legacy`, `test_t2_nondefault_with_own_creds_ok`. PASS. | ✅ DONE |
| T3 | **V3: blokada ENV dla wybranego nie-default bez creds** — marker + `OdooWorkspaceUnconfigured` | `api_routers/chat.py:_inject_odoo_creds`, `mcp/odoo_client.py:13-96` | ✅ RED: `OdooClient("default")` po inject grfood → `url=myodoo (ENV/leak)`. GREEN: `test_t3_unconfigured_nondefault_raises_not_env` (rzuca `OdooWorkspaceUnconfigured`, `.workspace_id=="grfood"`, NIE ENV), `test_t3_default_with_env_still_connects` (vault run OK), `test_t3_nondefault_with_own_creds_connects` (grfood→gfit), `test_t3_env_fallback_without_marker_regression`. PASS. | ✅ DONE |
| T4 | **D4: czytelny błąd w czacie** — sanityzowany komunikat | `mcp/odoo_errors.py:24-41` (SSoT ścieżki narzędzi), `swarm/executor.py:484-509` (parytet) | ✅ Narzędzia Odoo (`server.py`) routują wyjątek przez `classify_odoo_error` → dodano gałąź `OdooWorkspaceUnconfigured` (nazwa ws z wyjątku, bez URL/hasła/klucza). Executor `_invoke_tool` łapie parytetowo. GREEN: `test_t4_classify_error_is_clean_and_leakfree`, `test_t4_executor_invoke_tool_sanitizes_unconfigured`, `test_t4_tool_path_returns_clean_error` (realny `search_odoo_records`→`{"error":"❌…"}`, brak `records`). PASS. | ✅ DONE |
| T5 | **Regresja + evidence** | — | ✅ `pytest -m 'not e2e'` (Win `.venv` Py3.12, e2e/playwright WSL-only wykluczone): **478 passed / 0 failed / 2 skipped** (baseline 2026-07-11 = 440; wzrost = +15 nowych WSISO + AZURE-01). Ruff: All checks passed. Bandit: **0 nowych** zgłoszeń (moje B110 stłumione `# nosec` wg konwencji projektu; B411 xmlrpc:13 + B110:67 pre-existing). | ✅ DONE |

## 🛡️ Sekcja D — Security/Trust
- [x] Niezmiennik wymuszony: nie-default workspace bez `ODOO_DATA` NIGDY nie łączy z Odoo innego workspace (V1+V2+V3 zamknięte).
- [x] Fallback do `default` zachowany TYLKO dla ws=`default` i dla LLM (klucz globalny) — `test_t1_regres_llm_key_still_falls_back_to_default`, `test_t3_default_with_env_still_connects`.
- [x] Błąd braku creds jawny i sanityzowany (bez URL/hasła/klucza w payloadzie) — `classify_odoo_error`/executor używają własnego message (nie `str(e)`); testy asertują brak `MYODOO_URL`/`KEY-`.
- [x] Read-mode guard/step-up PIN/shadow-mode niezmienione (dotknięto TYLKO wyboru poświadczeń połączenia; WRITE_TOOLS/edit_mode bez zmian; suita zielona).
- [x] Test dowodowy cross-client: „grfood bez creds → NIE dane z myodoo" — `test_t4_tool_path_returns_clean_error` (brak klucza `records`, tylko `❌ error`).

## 🔬 DoD
- [x] 3 wektory (V1/V2/V3) zamknięte z testami dowodowymi (RED udokumentowany sondą /dev przed fixem na każdym wektorze).
- [x] Regres: ws=default działa (vault+ENV), LLM fallback działa, existing testy zielone (478 passed / 0 failed).
- [ ] Live re-check: po dodaniu klucza grfood (AZURE-01 Sekcja C) czat na grfood łączy z gfit.com.pl; bez klucza → jawny błąd, NIE myodoo. *(wymaga żywego Odoo + PIN — do weryfikacji przez /qa/manualnie; guard pokryty testem jednostkowym `test_t3_nondefault_with_own_creds_connects`)*
- [ ] Commit na nowej gałęzi (base main `5476cf2`), `--no-verify`; bramka /qa→/audyt+/sec→gf-review→merge. *(NIE commituję — czekam na approval usera; gałąź `fix/wsiso-01-odoo-cred-isolation` gotowa)*

> Uwaga: to jest hardening pre-existing zachowania (fallback istniał przed AZURE-01) — NIE regresja z ostatniego merge. Priorytet wysoki: cross-client data exposure.

## ✅ Nota realizacyjna (/dev, 2026-07-29)
**Wykonano wszystkie T1–T5 (TDD Red→Green→Refactor).** RED potwierdzony sondą na kodzie sprzed fixu: na 3 ścieżkach `grfood` (nie-default bez ODOO_DATA) po cichu dostawał `myodoo` (default) — dokładnie bug live.

**Zmiany (pliki:linie):**
- `smartmyodoo/vault/resolver.py` — `resolve_credential(..., allow_default_fallback: bool = True)`; gdy `False` kandydatem TYLKO `cred.workspace_id == workspace_id`. `resolve_llm_key` NIETKNIĘTE (domyślnie `True` → LLM globalny fallback zachowany).
- `smartmyodoo/api_routers/chat.py` — `_inject_odoo_creds`: `allow_default_fallback=False` + gdy brak creds i ws≠`default` → `set_odoo_creds(None)` + `set_odoo_unconfigured(workspace_id)` (marker). ws=`default` bez creds → bez markera (ENV/`vault run` OK).
- `smartmyodoo/mcp/odoo_client.py` — nowy wyjątek `OdooWorkspaceUnconfigured(workspace_id)` + ContextVar `_odoo_unconfigured_ctx` + `set_odoo_unconfigured`; w `OdooClient.__init__` FAIL LOUD (marker aktywny ∧ brak ctx-creds) ZANIM sięgniemy po ENV.
- `smartmyodoo/api_routers/workspaces.py` — `_resolve_odoo_creds`: oba `resolve_credential` z `allow_default_fallback=False`; legacy `default_ODOO` tylko dla `ws_id=="default"`; inaczej `HTTPException(400, "Brak poświadczeń Odoo dla workspace {ws}")`.
- `smartmyodoo/mcp/odoo_errors.py` — `classify_odoo_error`: gałąź `OdooWorkspaceUnconfigured` → sanityzowany „❌" z nazwą przestrzeni z wyjątku (narzędzia wołają `OdooClient("default")`, więc bierzemy ws z wyjątku, nie z argumentu).
- `smartmyodoo/swarm/executor.py` — `_invoke_tool`: parytetowa gałąź `except OdooWorkspaceUnconfigured` → własny sanityzowany komunikat „❌" (bez `str(e)`), rollback sandboxa.
- `tests/test_wsiso_odoo_cred_isolation.py` — 15 testów dowodowych (T1–T4 + regresy).

**Architektura błędu (istotne):** narzędzia Odoo w `mcp/server.py` łapią wyjątki i routują je przez `classify_odoo_error` → to jest RZECZYWISTE miejsce sanityzacji T4 (SSoT), więc tam trafia główna poprawka; gałąź w executorze to defensywny parytet dla narzędzi, które by re-raise'owały.

**Regres — 0 zepsutych:** (a) ws=`default` łączy (vault+ENV), (b) `resolve_llm_key` z fallbackiem, (c) `test_odoo_apikey_auth.py`/`test_credential_resolver.py`/`test_odoo_creds_context.py` zielone. Suita 478 passed / 0 failed. Ruff clean, bandit 0 nowych.

**Poza zakresem (D5, świadomie):** brak opt-in „dziedzicz Odoo z default", brak zmiany semantyki `default`, brak migracji sekretów. **Nie commitowano** (czeka na approval usera). **Następny krok: /qa.**
