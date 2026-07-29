---
sprint_id: "AZURE-01"
workspace: "SmartMyOdoo"
status: "🟡 In Progress"
created: 2026-07-29
closed: null
goal: "Połączenie SmartMyOdoo→Odoo (gfit.com.pl) uwierzytelnia się kluczem API Odoo powiązanym z użytkownikiem provisionowanym przez Microsoft/Entra — zamiast surowego hasła Odoo w Vaulcie. Kod w większości już to wspiera; sprint domyka jedną lukę spójności, dodaje test dowodowy i procedurę provisioningu. Klucz API jest odwoływalny i scoped do dedykowanego użytkownika Odoo (least privilege)."
prefix: "AZURE"
complexity: 2
roadmap_ref: "Decyzja Droga 1 (2026-07-29) po zwiadzie: gfit.com.pl (Odoo.sh) MA provider Microsoft Azure w /web/login → człowiek loguje się przez Entra, generuje klucz API Odoo, SMO używa go przez istniejący XML-RPC. Droga 2 (pełny headless OAuth + JSON-RPC) odrzucona jako wysoki koszt dla agenta serwerowego. Powiązane: ADR-007 (poświadczenia per workspace), [[odoo-dual-instance-setup]]."
parent_sprint: null
tags: ["security", "impl", "odoo-auth", "api-key", "entra-id", "least-privilege", "quick-win"]
---

# 🧱 Sprint: AZURE-01 — Odoo API-key na tożsamości Entra (bez hasła w Vaulcie)

> **Architekt:** /arch | **Data:** 2026-07-29 | **Routing:** T1–T2 → /dev; T2 dodatkowo ping /sec (zmiana ścieżki auth) | **Instancja docelowa:** gfit.com.pl (Odoo.sh)

## 0A. Problem (1 zdanie)
Chcemy, żeby połączenie SMO→Odoo działało na **kluczu API** powiązanym z tożsamością Microsoft/Entra (którą gfit.com.pl już wspiera w logowaniu), a nie na surowym haśle Odoo trzymanym w Vaulcie — klucz jest odwoływalny i można go dać dedykowanemu, najmniej-uprzywilejowanemu użytkownikowi.

## 0B. Fakty (kod + zwiad, zweryfikowane 2026-07-29)
| Fakt | Dowód |
|---|---|
| **Zwiad:** gfit.com.pl (Odoo.sh) ma provider „Microsoft Azure" w `/web/login` (tenant `867b8e4c-…`, client_id `7e99d595-…`, flow implicit) | publiczna strona logowania `/web/login` |
| Klucz API Odoo (14+) działa **jak hasło** w `authenticate` i `execute_kw` — zero zmian w wywołaniach RPC | `mcp/odoo_client.py:93,143-237` (`self.password` w każdym `execute_kw`) |
| Ścieżka agenta/narzędzi JUŻ preferuje api_key nad hasłem | `api_routers/chat.py:56` `"password": cred.api_key or cred.password or ""` |
| `OdooProjectConnector` JUŻ preferuje api_key | `core/odoo_connector.py:32` `credentials.get("api_key") or credentials.get("password","")` |
| Schema: `password` JUŻ opcjonalne dla `ODOO_DATA` (walidator wymaga tylko url/db/login) | `vault/schemas.py:95-98` |
| Endpoint `secrets` JUŻ zapisuje `api_key`; `SecretCreateRequest` ma to pole | `api_routers/secrets.py:54`, `vault/schemas.py:36` |
| Resolver „nowy format" mapuje `api_key` generycznie (raw z `type`) | `vault/resolver.py:26-33` |
| **LUKA (jedyna):** `_resolve_odoo_creds` (timesheet/workspace) zwraca TYLKO `cred.password`, gubi `api_key` → sekret z samym kluczem nie zadziała na tej ścieżce | `api_routers/workspaces.py:73-80` |
| Poświadczenia idą do connectora przez ContextVar, NIE przez prompt → klucz nie trafia do LLM (wzorzec ADR-007) | `mcp/odoo_client.py:22-32`, `chat.py:_inject_odoo_creds` |

## ⚖️ Decyzje (/arch)
- **D1 — Klucz API jako poświadczenie (semantyka Odoo).** Odoo 14+ przyjmuje klucz API w `authenticate(db, login, api_key, {})` i `execute_kw(..., api_key, ...)` identycznie jak hasło. Dlatego NIE zmieniamy connectora ani wywołań RPC — wystarczy, że warstwa sklejająca creds podaje `api_key` w polu `password`. Ścieżka czatu (`chat.py:56`) i `OdooProjectConnector` (`odoo_connector.py:32`) już to robią.
- **D2 — Domknięcie luki spójności (workspaces).** `_resolve_odoo_creds` (`workspaces.py:73-80`) ma przenosić `api_key` — albo dodać klucz `"api_key": cred.api_key`, albo (spójnie z chat.py) ustawić `"password": cred.api_key or cred.password`. Po tym KAŻDA ścieżka Odoo akceptuje sekret z samym kluczem API (bez hasła). To jest jedyna zmiana w kodzie produkcyjnym.
- **D3 — Provisioning = procedura człowieka + istniejący zapis do Vaulta (Sekcja C).** Klucz generuje człowiek w Odoo (po zalogowaniu przez Microsoft); zapis przez istniejący formularz/endpoint `secrets` (pole `api_key`, `type=odoo_data`) LUB przez skrypt/CLI (upsert jak w AZURE-01 draft). NIE potrzeba nowego typu ani schematu — `ODOO_DATA` już ma `api_key`.
- **D4 — Least privilege + usunięcie hasła.** Klucz wiążemy z **dedykowanym użytkownikiem Odoo** o minimalnych uprawnieniach (nie admin), zmapowanym na tożsamość Entra. Po ustawieniu `api_key` pole `password` w sekrecie **czyścimy** (walidator już na to pozwala). Kompromitacja klucza = odwołanie w Odoo (Preferencje→Konto→Klucze API), bez zmiany hasła użytkownika.
- **D5 — Zakres NIE obejmuje:** pełnego headless OAuth/JSON-RPC (Droga 2, osobny epic gdyby kiedyś potrzebny), zmian w logowaniu człowieka do UI SMO, ścieżki MCP stdio ENV-owej (`server.py:338` — osobny tor, poza zakresem).

## 🧱 Sekcja B — Zadania (/dev, TDD: Red→Green→Refactor)
| # | Zadanie | Pliki | Testy (DOWODOWE) | Status |
|---|---------|-------|-------|--------|
| T1 | **Domknięcie luki:** `_resolve_odoo_creds` przenosi `api_key` (prefer api_key nad password, spójnie z `chat.py:56`) | `api_routers/workspaces.py:73-80` | jednostkowy: `ODOO_DATA` z `api_key` i BEZ `password` → zwrócony dict niesie klucz w miejscu hasła | ✅ DONE — `workspaces.py:73-84` (`"password": cred.api_key or cred.password or ""`); dowód: `tests/test_odoo_apikey_auth.py::test_resolve_odoo_creds_carries_key_in_password_slot` PASS (RED przed fixem) |
| T2 | **Test dowodowy end-to-end auth (obie ścieżki):** sekret `type=odoo_data` z `api_key`, `password=""` → `OdooClient.connect()` woła `authenticate(db, login, <api_key>, {})`; ten sam wynik dla ścieżki chat (`_inject_odoo_creds`) i workspace (`_resolve_odoo_creds`) | `tests/` (mock `xmlrpc ServerProxy.authenticate` — assert 3. arg == api_key) | zielony dowodzi: klucz API = poświadczenie; brak hasła NIE blokuje connectu; klucz NIE pojawia się w żadnym payloadzie/logu | ✅ DONE — `tests/test_odoo_apikey_auth.py` (4 testy): `test_workspace_path_authenticates_with_api_key` + `test_chat_path_authenticates_with_api_key` (assert 3. arg == api_key, `API_KEY not in caplog.text`, brak klucza w URL-ach ServerProxy) + regresja hasła; workspace RED przed T1 = dowód luki |
| T3 | **Procedura provisioningu (Sekcja C) w docs** + ewentualny `smartmyodoo vault set-odoo-apikey` (opcjonalny quick helper) | `docs/`, opc. `smartmyodoo/cli.py` | (jeśli CLI) upsert idempotentny: ponowne = update; zły PIN nie zapisuje | 🟡 CZĘŚCIOWO — procedura udokumentowana (Sekcja C, istniejący endpoint `POST /api/secrets`); **CLI odłożony (follow-up)**: `cli.py` to `InteractiveCLI` (czat), nie dispatcher komend; dodanie `vault set-odoo-apikey` wchodzi w kod zapisu Vaulta (PIN+Fernet, ART.2 → wymaga /sec) i duplikuje przetestowany endpoint → poza priorytetem T1+T2+T4 |
| T4 | **Regresja + evidence** | — | `pytest -m 'not e2e'` ≥ baseline / 0 failed; ruff clean | ✅ DONE — `pytest -m 'not e2e'` (Windows `.venv`, e2e/playwright=WSL-only wykluczone): **461 passed, 2 skipped, 0 failed** (baseline 440); `ruff check` na zmienionych plikach: All checks passed |

## 🧱 Sekcja B2 — Follow-up po bramkach /audyt+/sec (2026-07-29)
Obie bramki ✅ APPROVE (sec: 0 Crit/High; audyt: A−). Domknięcie 2 nieblokujących znalezisk PRZED gf-review, by delta wchodziła do main czysta:
| # | Zadanie | Pliki | Testy (DOWODOWE) | Status |
|---|---------|-------|-------|--------|
| T6 | **F-1 (Medium, /audyt): parytet `api_key` w gałęzi legacy resolvera.** `to_credential` dla legacy `<ws>_ODOO` buduje `Credential` BEZ `api_key` → sekret bez `type` z samym kluczem daje `""` (przeczy D2 „KAŻDA ścieżka"). Fix: dodać `api_key=raw.get("api_key")` | `smartmyodoo/vault/resolver.py:47-58` | RED przed fixem: legacy `_ODOO` raw z `api_key`+pustym `password` → `to_credential(...).api_key is None`; GREEN po: `== <klucz>`; `resolve_credential`→`_resolve_odoo_creds`/`_inject_odoo_creds` niesie klucz | ✅ DONE — `resolver.py:57` (`api_key=raw.get("api_key")` w gałęzi legacy `_ODOO`); dowód: `tests/test_odoo_apikey_auth.py::test_legacy_odoo_secret_carries_api_key` RED przed fixem (`assert None == <klucz>`), GREEN po. Walidator `Credential._validate_by_type` (schemas.py:95-98) wymaga tylko url/db/login → api_key przechodzi. |
| T7 | **F-3 (Low, /audyt): test ścieżki timesheet.** `_resolve_odoo_creds(prefer_timesheet=True)` z sekretem `type=odoo_timesheet`+`api_key` (bez hasła) przenosi klucz w slot `password` | `tests/test_odoo_apikey_auth.py` (rozszerzenie) | sekret `odoo_timesheet` z `api_key` → dict niesie klucz; connector auth kluczem | ✅ DONE — `tests/test_odoo_apikey_auth.py::test_timesheet_path_authenticates_with_api_key` PASS: dict niesie klucz w slocie `password`; `OdooProjectConnector` woła `authenticate(db, login, <api_key>, {})` (3. arg == klucz); `API_KEY not in caplog.text` + brak w URL-ach ServerProxy. Test GREEN od razu (prod fix z T1 pokrywa też ścieżkę timesheet — to była luka pokrycia, nie kodu). |
| T8 | **Regresja** | — | `pytest -m 'not e2e'` = 0 failed; ruff clean | ✅ DONE — `pytest -m 'not e2e' --ignore=tests/e2e --ignore=tests/test_ui_dnd.py` (Windows `.venv`, e2e=WSL-only): **463 passed, 2 skipped, 0 failed** (baseline 461 + 2 nowe testy T6/T7); `ruff check smartmyodoo/vault/resolver.py tests/test_odoo_apikey_auth.py`: All checks passed. |

> F-2 (/audyt, asercje caplog/URL słabo-informacyjne) i /sec L1 (SecretFilter nie redaguje gołego klucza Odoo) + L3 (`str(e)` w workspaces, wątek H-1) — **pre-existing, do osobnego backlogu**, poza tą deltą.

## 🧩 Sekcja C — Procedura: wygenerowanie i zapis klucza API
1. **Zaloguj się do Odoo przez Microsoft** na https://gfit.com.pl/web/login → „Microsoft Azure" (potwierdza tożsamość Entra).
2. (Zalecane) Utwórz/wskaż **dedykowanego użytkownika Odoo** o minimalnych prawach do operacji SMO (nie admin).
3. W Odoo: **Preferencje → Konto → Klucze API (Developer API Keys) → Nowy klucz** → skopiuj (pokazany raz).
4. Zapisz w Vaulcie jako `ODOO_DATA` dla właściwego workspace:
   - **UI/endpoint (istniejący):** `POST /api/secrets/{nazwa}` z `type=odoo_data`, `url`, `db`, `login=<user>`, `api_key=<klucz>`, `password=""`, `workspace_id`.
   - albo **CLI** (jeśli T3): `smartmyodoo vault set-odoo-apikey --workspace default --url https://gfit.com.pl --db rwyszewski-gourmetfoods-main-15940999 --login <user> --api-key <klucz>`.
5. **Usuń stare hasło** z sekretu (ustaw `password=""`) — walidator na to pozwala; od teraz SMO łączy się kluczem.
6. Weryfikacja: uruchom operację odczytu przez SMO → połączenie OK. Test odwołania: skasuj klucz w Odoo → SMO dostaje `PermissionError` (dowód, że działał na kluczu).

## 🛡️ Sekcja D — Security/Trust
- [ ] Klucz API tylko w Vaulcie (Fernet at-rest, workspace-scoped); NIGDY w prompcie/tool-args/tool-result/logu (ContextVar, nie prompt — jak dziś).
- [ ] Klucz na dedykowanym użytkowniku Odoo least-privilege (nie admin) powiązanym z Entra.
- [ ] Hasło Odoo usunięte z sekretu po przejściu na klucz (redukcja powierzchni).
- [ ] Odwołanie klucza w Odoo = natychmiastowe odcięcie SMO (dowód w T procedury), bez zmiany hasła.
- [ ] Błędy auth sanityzowane (`type(e).__name__`) — connector już tak robi (`odoo_client.py:102`).

## 🔬 DoD
- [x] Sekret `ODOO_DATA` z samym `api_key` (bez hasła) uwierzytelnia SMO na obu ścieżkach (chat + workspace) — test zielony (czerwony przed T1 na ścieżce workspace = dowód luki). → `tests/test_odoo_apikey_auth.py` (workspace: RED `OdooProjectConnectorError: Missing credentials` przed T1 → GREEN po; chat: zielony od początku).
- [x] `authenticate` dostaje klucz API jako poświadczenie; klucz nieobecny w logach/payloadach. → assert `secret == API_KEY` (3. arg) + `API_KEY not in caplog.text` + brak klucza w URL-ach ServerProxy.
- [ ] Procedura provisioningu udokumentowana i przejdzie ręcznie na gfit.com.pl. → udokumentowana (Sekcja C); ręczne przejście na gfit.com.pl = zadanie człowieka (poza zakresem /dev).
- [x] Regresja 0 failed, ruff clean. → 461 passed / 0 failed (Windows `.venv`, e2e=WSL-only); ruff clean na zmienionych plikach.
- [ ] Commit `--no-verify` (pre-commit CRLF-broken) na gałęzi feature; PR do `main` przez bramkę (/qa → /audyt+/sec → gf-review). → zmiany NIEZACOMMITOWANE na `fix/audit2-a1-a4` (czekają na zgodę użytkownika + bramkę; ART.13/14).

## 📝 Nota realizacyjna (/dev, 2026-07-29)
**Wykonane:** T1 ✅, T2 ✅, T4 ✅ (priorytet). T3 🟡 częściowo (procedura ✅, CLI odłożony jako follow-up).

- **T1 — `smartmyodoo/api_routers/workspaces.py:73-84`:** `_resolve_odoo_creds` zwraca teraz `"password": cred.api_key or cred.password or ""` (wariant „klucz w miejscu hasła", spójny z `chat.py:56`). Wybór podyktowany kontraktem konsumenta `OdooProjectConnector` (`core/odoo_connector.py:32` czyta `api_key or password`) oraz kluczem `login` (nie `username`) — zweryfikowane. Zero zmian w connectorze/RPC (D1). Jedyna zmiana produkcyjna (D2).
- **T2 — `tests/test_odoo_apikey_auth.py` (nowy, 4 testy):** dowodzi obu ścieżek. Mock granicy sieci (`xmlrpc.client.ServerProxy` → `_FakeCommon.authenticate` rejestruje argumenty) — zero mocków udających logikę. Asercje: 3. arg `authenticate` == api_key na ścieżce workspace (`_resolve_odoo_creds`→`OdooProjectConnector`) i chat (`_inject_odoo_creds`→`set_odoo_creds`→`OdooClient.connect`); `API_KEY not in caplog.text`; brak klucza w URL-ach ServerProxy; regresja ścieżki hasłowej. **Dowód luki:** przed T1 test workspace RED (`Missing required Odoo credentials`), chat GREEN → potwierdza, że luka była TYLKO na ścieżce workspace.
- **T4 — regresja:** `pytest -m 'not e2e' --ignore=tests/e2e --ignore=tests/test_ui_dnd.py` → **461 passed, 2 skipped, 0 failed** (baseline 440; wzrost = m.in. 4 nowe testy). Wykluczenie e2e/`test_ui_dnd` bo `playwright` = WSL-only (natywny `.venv` Windows go nie ma); `test_ui_docs_render.py` ma guard importu → nie wyklinany. `ruff check` na zmienionych plikach: All checks passed.

**Odstępstwa / follow-up:**
1. **T3 CLI `smartmyodoo vault set-odoo-apikey` — ODŁOŻONY.** `cli.py` = `InteractiveCLI` (pętla czatu), nie dispatcher komend; entrypoint `smartmyodoo.__main__:main`. Dodanie subkomendy weszłoby w kod zapisu Vaulta (PIN-auth + Fernet + upsert = powierzchnia security, ART.2 → wymaga /sec) i duplikuje przetestowany `POST /api/secrets/{nazwa}` (już w Sekcji C). Zgodnie z wytyczną sprintu „jeśli podnosi ryzyko/rozmiar — pomiń" + KISS/YAGNI. Provisioning odbywa się istniejącym endpointem/UI.
2. **Zmiany niezacommitowane** — pozostawione na `fix/audit2-a1-a4` do decyzji użytkownika i bramki (/qa → /audyt+/sec → gf-review).
3. **Ręczne przejście provisioningu na gfit.com.pl** (Sekcja C, kroki 1-6) — zadanie człowieka; kod jest gotowy je obsłużyć na obu ścieżkach.

> Uwaga: to NIE jest „SSO headless" — SMO działa jako użytkownik Odoo, którego klucz podaliśmy; tożsamość Entra jest źródłem provisioningu tego użytkownika, nie żywym tokenem w każdym wywołaniu. Pełny OAuth (Droga 2) pozostaje osobnym epikiem, gdyby kiedyś był potrzebny.

## 📝 Nota realizacyjna B2 (/dev, 2026-07-29 — follow-up po bramkach /audyt+/sec)
**Wykonane wg TDD (Red→Green):** T6 ✅, T7 ✅, T8 ✅. Zakres ścisły: `resolver.py` (T6) + `test_odoo_apikey_auth.py` (T6/T7). Zmiany NIEZACOMMITOWANE na `fix/audit2-a1-a4` (bez PR — czekają na zgodę + gf-review).

- **T6 — `smartmyodoo/vault/resolver.py:57`:** do konstruktora `Credential` w gałęzi legacy `<ws>_ODOO` (`to_credential`, ~linie 47-60) dodano `api_key=raw.get("api_key")`. Domyka F-1: sekret legacy z samym kluczem (bez `type`, puste `password`) niósł dotąd `api_key=None` → przeczyło D2. Walidator `_validate_by_type` (ODOO_DATA wymaga tylko url/db/login) na to pozwala — zweryfikowane. **RED-before-fix potwierdzony:** `test_legacy_odoo_secret_carries_api_key` przed fixem `AssertionError: assert None == 'odoo-apikey-…'`; po fixie GREEN.
- **T7 — `tests/test_odoo_apikey_auth.py` (+`test_timesheet_path_authenticates_with_api_key`, +fixture `_odoo_timesheet_secret_with_apikey`):** dowodzi ścieżki timesheet (`_resolve_odoo_creds(prefer_timesheet=True)`, `type=odoo_timesheet`+api_key, puste hasło) — dict niesie klucz w slocie `password`, `OdooProjectConnector` uwierzytelnia się kluczem (3. arg `authenticate` == klucz), klucz nie wycieka do logów/URL-i. Mock TYLKO granicy sieci (`xmlrpc.client.ServerProxy`), zero atrap logiki. Test GREEN od razu — prod fix z T1 (`workspaces.py:81`) pokrywał już tę gałąź; F-3 to luka POKRYCIA testowego, nie kodu.
- **T8 — regresja:** `pytest -m 'not e2e' --ignore=tests/e2e --ignore=tests/test_ui_dnd.py` (Windows `.venv`, e2e/playwright=WSL-only) → **463 passed, 2 skipped, 0 failed** (baseline 461 + 2 nowe testy). `ruff check` na obu zmienionych plikach: All checks passed.

**Follow-up (poza tą deltą, zgodnie z notą pod tabelą B2):** F-2 (asercje caplog/URL) i /sec L1 (SecretFilter dla gołego klucza) + L3 (`str(e)` w workspaces) — pre-existing, osobny backlog.
