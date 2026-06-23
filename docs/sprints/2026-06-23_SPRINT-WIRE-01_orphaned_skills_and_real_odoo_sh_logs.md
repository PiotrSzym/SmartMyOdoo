---
sprint_id: "WIRE-01"
workspace: "SmartMyOdoo"
status: "🟡 In Progress"
created: 2026-06-23
closed: null
goal: "Domknąć rozjazd 'kod istnieje, ale jest nieosiągalny': (1) podpiąć do routingu 3 osierocone skile (ODOO_SH_LOGS, FINANCIAL_AUDIT, ODOO_DEVOPS_GITHUB), które są w SKILL_REGISTRY, ale dispatcher nigdy ich nie wybiera; (2) zamienić zaślepkę read_odoo_log (lokalny plik 'odoo.log', docstring '(symulowane)') na realne, hosting-aware pobieranie logów (on-premise: konfigurowalna ścieżka; odoo.sh: SSH tail); (3) test-guard blokujący ponowne osierocenie skila. Cel LOKALNY (ADR-008)."
prefix: "WIRE"
complexity: 6
roadmap_ref: "Weryfikacja funkcjonalna 2026-06-23 (live: routing fallback + TOOL_REGISTRY + read_odoo_log stub); po RELEASE-01"
parent_sprint: null
tags: ["wiring", "dispatcher", "skills", "odoo-sh", "logs", "routing", "local-only", "adr-008"]
---

# 🧱 Sprint: WIRE-01 — Osierocone skile + realne logi odoo.sh

> **Architekt:** /arch | **Owner:** /dev | **Review:** /gf-review | **Data:** 2026-06-23
> **Bazuje na:** main (`90d7e5e`) | **Recon:** Weryfikacja funkcjonalna live 2026-06-23 (dispatcher fallback, TOOL_REGISTRY=8 narzędzi, read_odoo_log = stub na lokalny plik) + graphify (2908 węzłów) | **ADR:** ADR-008 (Local-Only)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch)

### 0A. Business Discovery
- **Dla kogo?** Użytkownik czatu SmartMyOdoo (operator/konsultant Odoo) + maintainer.
- **Problem (1 zdanie):** trzy funkcjonalności są zadeklarowane jako kod (`SkillConfig` w `SKILL_REGISTRY`), ale **nieosiągalne z czatu** — dispatcher nie ma do nich żadnej ścieżki; dodatkowo „diagnostyka logów" to **zaślepka** czytająca lokalny plik `odoo.log`, nie logi z odoo.sh.
- **Metryka sukcesu:** 100% skili z `SKILL_REGISTRY` (11/11) osiągalnych z dispatchera (test-guard); `read_odoo_log` realnie zwraca logi dla on-premise (konfig. ścieżka) i odoo.sh (SSH) — udowodnione testem (mock SSH).
- **ROI:** zamienia „martwy kod" w działające funkcje; logi to najczęstszy powód kontaktu konsultanta z odoo.sh — bez tego skill `odoo_sh_logs` jest fasadą.
- **Źródło:** Weryfikacja funkcjonalna live (2026-06-23) — sekcja „Nowy gap wykryty przy weryfikacji".
- **Zakres:** cel **LOKALNY** (ADR-008). Budowa kopii środowisk jako kontenerów Odoo = POZA zakresem (tylko nota, T-DEFER).

### 0B. Fakty (z weryfikacji live + recon /arch, plik:linia)
| Fakt | Dowód | Zadanie |
|---|---|---|
| `SKILL_REGISTRY` ma 11 skili | `swarm/skills/registry.py:17-29` | baseline |
| `ROUTING_TABLE` mapuje tylko 5 unikalnych skili (+None×2) | `swarm/dispatcher.py:9-50` | T1 |
| Fallback heurystyczny dodaje 5 skili | `swarm/dispatcher.py:108-135` | T1 |
| **3 skile NIGDY nie wybierane:** `ODOO_SH_LOGS`, `FINANCIAL_AUDIT`, `ODOO_DEVOPS_GITHUB` | brak w `ROUTING_TABLE` i w fallbacku (zweryf. live: 7 prób, żadna nie trafiła) | T1 |
| Intent prompt obiecuje „przegląd logów" → E_RESEARCH | `dispatcher.py:74` | T1 |
| ...ale `ROUTING_TABLE[E_RESEARCH].skill_name = None` | `dispatcher.py:30-34` | T1 |
| `read_odoo_log` = stub: czyta lokalny `odoo.log`, docstring „(symulowane)" | `swarm/tools.py:160-171` | T2 |
| `read_odoo_log` jest w `allowed_tools` skila logów | `swarm/skills/odoo_sh_logs.py:7-15` | T2 |
| `read_odoo_log` w pipeline (allowed) | `swarm/pipeline.py:83` | T2 |
| Connector zna hosting odoo.sh | `swarm/recon.py:16` (`classify_hosting → odoo_sh`) | T2 |
| Connector zna URL/db/api_key (XML-RPC) | `core/odoo_connector.py:26-46` | T2 |
| TOOL_REGISTRY = 8 narzędzi (live) | `odoo_search, odoo_schema, odoo_create, rollback_changes, scaffold_module, search_knowledge_base, read_odoo_log, search_odoo_code` | baseline |
| Testy zielone (baseline regresji) | pytest **303 passed / 2 skipped / 0 failed** (2026-06-23) | baseline |

### 0C. User Stories
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-WIRE-1 | użytkownik czatu | by każdy zadeklarowany skill dało się wywołać intencją | nie płacić za martwy kod | KIEDY napiszę intencję pasującą do skila (logi/księgowość/devops) TO dispatcher wybiera ten skill, nie H/None |
| US-WIRE-2 | konsultant Odoo | by „pokaż logi" realnie czytało logi instancji | diagnozować bez ręcznego SSH | KIEDY hosting=on_premise TO czyta `ODOO_LOG_PATH`; KIEDY hosting=odoo.sh TO SSH `tail`; KIEDY brak konfiguracji TO jasny komunikat (nie ciche „symulowane") |
| US-WIRE-3 | maintainer | by CI blokował ponowne osierocenie skila | regres nie wróci | KIEDY skill jest w `SKILL_REGISTRY` ale nieosiągalny z dispatchera TO test-guard FAIL |

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| Routing intencji | `ROUTING_TABLE` + fallback heurystyczny (`dispatcher.py`) | 📐 IN-PATTERN (rozszerz, nie przepisuj) |
| Skill config | `SkillConfig` (`skill_config.py`), `SkillName` enum (`models.py`) | 📐 IN-PATTERN |
| Narzędzie MCP | `@register_tool` (`tools.py`) | 📐 IN-PATTERN (zmień ciało `read_odoo_log`, zachowaj sygnaturę/nazwę) |
| Detekcja hostingu | `EnvironmentRecon.classify_hosting` (`recon.py`) | 📐 REFERENCE (użyj do gałęzi log-retrieval) |
| Sekrety (SSH key/hasło) | Vault (`vault/`, `vault_auth.py`) | 📐 IN-PATTERN (SSH creds z vaultu, NIE z env w plaintext) |

### 0E. Test Strategy
| Warstwa | Potrzebna? | Co testować | Kto | Narzędzie |
|---|:--:|---|:--:|---|
| Unit | ✅ | routing: każda z 11 nazw `SKILL_REGISTRY` produkowana dla ≥1 próby | /dev | pytest |
| Unit | ✅ | `read_odoo_log`: on_premise czyta ścieżkę; odoo.sh woła SSH (mock); brak konfiguracji → komunikat błędu (nie „symulowane") | /dev | pytest + monkeypatch |
| Guard | ✅ | `set(SKILL_REGISTRY) - set(osiągalne_z_dispatchera) == {}` | /dev | pytest (parametryzowany) |
| Regresja | ✅ | pełna pytest 0 failed (baseline 303) | /qa | pytest |
| Security | ✅ | SSH creds nie wyciekają do logów; brak `master_pwd`/klucza w `response.text`/log | /sec | grep + review |

### 0F. US → Test Mapping
| US | Scenariusz | Plik/Weryfikacja | Priorytet |
|----|------------|----------|-----------|
| US-WIRE-1 | 11/11 skili osiągalnych | `tests/swarm/test_dispatcher_routing.py` (nowy/rozszerzony) | 🔴 |
| US-WIRE-2 | logi: on_premise + odoo.sh (mock SSH) + brak konfig. | `tests/swarm/test_read_odoo_log.py` (nowy) | 🔴 |
| US-WIRE-3 | guard osieroconych skili | `tests/swarm/test_no_orphaned_skills.py` (nowy) | 🟡 |

### 0G. Security Scope → Sekcja D
Nowa powierzchnia: **SSH do odoo.sh** (T2). Creds (klucz/hasło/host) MUSZĄ iść z vaultu, nie z env w plaintext; zero echa creds do logów (analogia do `db_manager.py:36` — „NIE logujemy response.text"). Komenda SSH: tylko `tail`/odczyt (read-only), bez interpolacji user-inputu do shella (lista argumentów, nie `shell=True`). `search_odoo_code` już używa listy argów (`tools.py:180`) — trzymać ten wzorzec.

### ⚖️ Zasady / Decyzje architektoniczne (/arch)
- **D1 — Rozszerz, nie przepisuj dispatchera.** Dodaj brakujące skile przez (a) nowe gałęzie w fallbacku (słowa-klucze: `log/traceback/błąd deploy` → `ODOO_SH_LOGS`; `faktur/księgow/VAT/zapis` → `FINANCIAL_AUDIT`; `deploy/branch/staging/github/odoo.sh push` → `ODOO_DEVOPS_GITHUB`) ORAZ (b) podpięcie `skill_name` w `ROUTING_TABLE` tam, gdzie dziś `None` (E_RESEARCH → `ODOO_SH_LOGS` jako domyślny dla logów). Nie zmieniać kontraktu `classify_intent`.
- **D2 — `read_odoo_log` hosting-aware, sygnatura bez zmian.** Zachowaj nazwę narzędzia i parametr `lines` (kontrakt `allowed_tools`/pipeline). Wewnątrz: gałąź po `classify_hosting`. Fallback gdy brak konfiguracji = **jawny błąd z instrukcją**, NIE ciche „symulowane".
- **D3 — ✅ ROZSTRZYGNIĘTE (user 2026-06-23): SSH `tail` na kontenerze brancha.** Pobieranie logów odoo.sh przez SSH `tail -n N` pliku logu; klucz/host SSH z vaultu, read-only. Odpadły: scraping panelu (kruche) i odraczanie. **T2b ODBLOKOWANE.**
- **D4 — Kopie środowisk jako kontenery Odoo = POZA zakresem** (T-DEFER). Dziś jest klon BAZY (`db_manager.duplicate_database`); budowa obrazów kontenerów to osobny, większy sprint.
- **D5 — God Node `SkillConfig` (graphify: 69 zależności).** Dokładamy tylko routing (dane), nie nowe zależności do `SkillExecutor`/`Pipeline`.

---

## 🧱 Sekcja B — Podział Zadań (TDD-friendly) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| T1 | **Routing 3 osieroconych skili** 🔴: dodaj gałęzie fallbacku (logi→`ODOO_SH_LOGS`, księgowość→`FINANCIAL_AUDIT`, devops/odoo.sh→`ODOO_DEVOPS_GITHUB`) + podepnij `skill_name` w `ROUTING_TABLE[E_RESEARCH]`. Kolejność `elif` tak, by nie kanibalizować istniejących (np. `audyt`→SECURITY_AUDIT zostaje). | `smartmyodoo/swarm/dispatcher.py` | D1, `dispatcher.py:108-135` | Unit: 3 nowe próby → właściwy skill; istniejące 5 bez regresji | ✅ done |
| T2a | **`read_odoo_log` on-premise (realny)** 🔴: czytaj `ODOO_LOG_PATH` (env/konfig), fallback ścieżki Odoo (`/var/log/odoo/odoo-server.log`); brak/niedostępny → jawny błąd z instrukcją (usuń „symulowane"). Zachowaj nazwę+`lines`. | `smartmyodoo/swarm/tools.py` | D2 | Unit: czyta podaną ścieżkę (`lines=N`); brak → komunikat błędu (nie „symulowane") | ✅ done |
| T2b | **`read_odoo_log` odoo.sh (SSH)** 🔴 **[D3 ✅ SSH]**: gdy `classify_hosting==odoo_sh` → SSH `tail -n {lines}` log brancha; creds (host/użytkownik/klucz) z vaultu; read-only, argv (nie `shell=True`); zero echa creds. | `smartmyodoo/swarm/tools.py`, `smartmyodoo/swarm/vault_auth.py` | D2/D3, `db_manager.py:36` | Unit (mock SSH): wołane z `tail -n {lines}`; brak creds → błąd; creds nie w logu | ✅ done |
| T3 | **Test-guard: brak osieroconych skili** 🟡: parametryzowany test — dla każdego `SkillName` w `SKILL_REGISTRY` istnieje wejście, dla którego dispatcher zwraca ten skill (lub jawna allowlista „nie-routowalnych" z uzasadnieniem). | `tests/swarm/test_no_orphaned_skills.py` | US-WIRE-3 | FAIL gdy skill w rejestrze nieosiągalny | ✅ done |
| T-DEFER | **Kopie środowisk jako kontenery Odoo** ⏸️: POZA zakresem (D4). Tylko nota w roadmap — dziś klon bazy przez `/web/database/duplicate`. | — | — | — | ⏸️ deferred |

> **TDD/kolejność /dev:** T3 (guard — najpierw RED na 3 osieroconych) → T1 (zazielenia guard) → T2a (on-premise) → T2b (odoo.sh SSH; D3 ✅ SSH `tail`). Po każdej zmianie: pełna pytest 0 failed (baseline 303).

---

## 🛡️ Sekcja D — Security (/sec) — DO WERYFIKACJI
> /dev (2026-06-23): zaznaczone pozycje pokryte testami; finalna pieczęć należy do /sec.
- [x] SSH creds (T2b) pochodzą z vaultu (`VaultAuthProvider.get_ssh_credentials` → `vault.load_vault`, klucz `ODOO_SH_SSH`), nie z env w plaintext. Z env pobierany jest jedynie PIN (`VAULT_PIN`) — ten sam mechanizm autoryzacji co `pipeline.py:202`. *(test: `test_read_odoo_log.py::test_odoo_sh_calls_ssh_tail_with_argv` + `vault_auth` happy/missing)*
- [x] Zero echa creds/klucza/hosta do logów (wzór: `db_manager.py:36` — `cmd`/`stderr` NIE są logowane). *(test: `test_odoo_sh_does_not_echo_credentials_to_logs`)*
- [x] Komenda SSH read-only (`tail`), argv-list (`subprocess.run(cmd_list)`, bez `shell=True`, `lines` rzutowane na `int`). *(test: `test_odoo_sh_calls_ssh_tail_with_argv` — asercja `shell is False` + `isinstance(cmd, list)`)*
- [x] `read_odoo_log` nie ujawnia ścieżek/sekretów w komunikacie błędu (tylko instrukcja konfiguracji `ODOO_LOG_PATH`/`ODOO_SH_SSH`). *(test: `test_error_message_does_not_leak_secrets`, `test_missing_path_returns_explicit_error_without_simulated_word`)*
- [x] Brak nowych endpointów HTTP; zmiany tylko w warstwie narzędzi (`tools.py`), dispatchera (`dispatcher.py`) i vault-adaptera (`vault_auth.py`).

## 🔍 Sekcja B½ — Audyt Spójności (/audyt) — ZWERYFIKOWANE (2026-06-23)
> /audyt (2026-06-23, `.venv-qa`, Evidence Before Claims, zero-trust): 6 faz. Read-only na kodzie. NIE testowano funkcjonalności (/qa: 323 passed) ani luk (/sec: Sekcja D). Scope: spójność/wzorce/architektura/tech-debt/skill-usage.

### 📏 METRYKI (Faza 1)
- LOC delta: dispatcher +38, tools +103, vault_auth +58 (≈199 prod) | testy nowe: 148+152 = 300 LOC | **test ratio ≈ 1.5:1** (zdrowo, >1:1).
- God classes: **0 nowych**. Najdłuższy zmieniony plik tools.py = 271 linii (<300). `read_odoo_log` rozbity na 2 helpery (`_read_log_on_premise` 25 LOC / `_read_log_odoo_sh` 55 LOC) — funkcje krótkie, czytelne.
- Circular deps: **0 nowych** powiązanych ze swarm/. Import cykle w GRAPH_REPORT to wyłącznie `__init__.py` self-loopy w `custom_addons/` (artefakt graphify, nie WIRE-01).
- Coverage WIRE-01: **20 passed / 0 failed** (`test_no_orphaned_skills` 14 + `test_read_odoo_log` 6) w 94s. Naming ADR-91 OK (`test_*.py`, lokalizacja `tests/swarm/`).

### 🎨 PATTERN CONSISTENCY — **A**
| Element | Wzorzec ref. | Werdykt | Dowód |
|---|---|:--:|---|
| Routing intencji | `ROUTING_TABLE` + fallback (D1) | 📐 IN-PATTERN | Rozszerzony (nowe `elif` + `E_RESEARCH.skill_name`), `classify_intent` kontrakt nietknięty, `final_skill = skill_name or route` zachowany |
| Narzędzie MCP | `@register_tool` (tools.py) | 📐 IN-PATTERN | sygnatura `read_odoo_log(lines:int=50)` + nazwa NIETKNIĘTE; TOOL_REGISTRY=8; allowed_tools/pipeline.py:83 bez zmian |
| SSH subprocess | `search_odoo_code` argv-list (tools.py:268) | 📐 IN-PATTERN | `subprocess.run(cmd_list)`, ZERO `shell=True`, `lines→int(lines)` |
| Non-echo creds | `db_manager.py:36` (NIE log response.text) | 📐 IN-PATTERN | `cmd`/`stderr`/host/user/key NIE logowane; komentarz cytuje wzorzec; test `does_not_echo_credentials` |
| Sekrety SSH | Vault (`vault_auth.py`) | 📐 IN-PATTERN | `get_ssh_credentials` lustrem `authenticate`: `load_vault`+PIN, sanityzowany `PipelineError` (ADR-011) |
| Dataclass creds | `PipelineCredentials` frozen | 📐 IN-PATTERN | `SSHCredentials` `@dataclass(frozen=True)`, identyczny styl |
| Detekcja hostingu | `EnvironmentRecon.classify_hosting(url)` | ⚠️ AD-HOC | Tool używa `os.environ["ODOO_HOSTING"]` zamiast `classify_hosting` — patrz Dewiacja T2b niżej |

### 🏗️ ARCHITECTURE COMPLIANCE & ZERO-TRUST — **A**
- **D5 (God Nodes) ✅ POTWIERDZONE DOWODEM:** `grep` SkillConfig/SkillExecutor/ExecutionPipeline w 3 zmienionych = **0 trafień**. dispatcher importuje tylko `.models`+`.model_policy`; tools.py importuje `vault_auth`+`PipelineError` **lokalnie in-function** (świadomy anty-cykl, komentarz tools.py:202); vault_auth importuje `vault`+`PipelineError`. **ZERO nowych krawędzi do God Nodes.** SkillConfig 69 / SkillExecutor 64 / ExecutionPipeline 48 — niezmienione.
- **D1 ✅:** dispatcher ROZSZERZONY, nie przepisany. Kontrakt `classify_intent`/`forward_message` nietknięty. Kolejność `elif` (kod→etl→baza→audit-history→security→DEVOPS→LOGI→FINANCIAL→test→arch) czytelna, udokumentowana komentarzami, NIE spaghetti.
- **D2 ✅:** gałęzie on-prem/odoo.sh CZYSTO rozdzielone helperami; dispatcher hostingu (`read_odoo_log`) = 4 linie, deleguje. Brak „zlepka w jednej funkcji".
- **Leakage Prevention (zero-trust) ✅:** brak nowych endpointów HTTP; błędy SSH/log sanityzowane (instrukcja konfig., bez ścieżek/sekretów/stderr) — zgodne z `error_pancerz`.
- **SOLID/Rule of Three:** abstrakcja `SSHCredentials` + 2 helpery uzasadnione (osobne hosting paths). Brak feature creep — scope = T1/T2a/T2b/T3.

### 💳 TECH DEBT — **→ (neutralny, drobny nowy LOW)**
| # | Dług | Severity | Rekomendacja |
|---|------|:--:|---|
| TD-1 | **Dwa źródła prawdy o hostingu** (T2b dewiacja): `recon.classify_hosting(url)` vs `tools.ODOO_HOSTING` env. `ODOO_HOSTING` **nigdzie nie jest ustawiane w kodzie prod** → gałąź odoo.sh martwa bez ręcznej konfiguracji ENV. | 🟡 MEDIUM | Follow-up sprint: przekazać hosting z pipeline-context do warstwy tooli i wpiąć realny `classify_hosting`. W WIRE-01 akceptowalne (kontrakt zamrożony). |
| TD-2 | Boundary `content[-lines:]` (LOW, już zgłoszony przez /qa): `lines=0`→cały plik, `lines<0`→prawie cały. | 🟢 LOW | Clamp `max(0, int(lines))`. Poza kontraktem (LLM woła 50). |
| TD-3 | `remote_log` default `~/logs/odoo.log` — `~` rozwijane przez remote shell ssh (OK), ale ścieżka odoo.sh nie zweryfikowana realnym środowiskiem (cel LOKALNY, ADR-008). | 🟢 LOW | Zweryfikować przy realnym dostępie odoo.sh (poza zakresem lokalnym). |

### 🛠️ SKILL USAGE — **A**
- Wzorce z Sekcji 0D respektowane (ROUTING_TABLE rozszerzony nie przepisany; `@register_tool` ciało zmienione, kontrakt zachowany; vault dla creds; argv-list jak `search_odoo_code`). **/dev NIE wymyślił nowych wzorców** — każdy element ma referencję plik:linia.
- Zgodność z ADR: ADR-008 (Local-Only) ✅, ADR-011 (sanityzowane komunikaty vault) ✅, ADR-91 (naming testów) ✅.

### ⚖️ OCENA DEWIACJI T2b (`os.environ["ODOO_HOSTING"]` zamiast `classify_hosting`)
**WERDYKT: AKCEPTOWALNY PRAGMATYZM w ramach WIRE-01, z follow-up długiem (TD-1, MEDIUM).**
- **ZA:** `classify_hosting(url)` wymaga URL klienta, którego sygnatura `read_odoo_log(lines)` NIE ma (kontrakt zamrożony — przekazanie URL = osobna zmiana kontraktu, słusznie poza WIRE-01). Dewiacja jawnie udokumentowana w Sekcji F /dev. Selektor env jest deterministyczny i testowalny.
- **PRZECIW (dług):** to **realne dwa źródła prawdy** — `recon.py` klasyfikuje po URL i zapisuje do `EnvironmentInfo.hosting_type` (konsumowane tylko w `adp.py` jako string promptu), a tool decyduje po env. **Most NIE istnieje:** `ODOO_HOSTING` nie jest nigdzie ustawiane w kodzie prod → w praktyce gałąź odoo.sh jest osiągalna tylko po ręcznym `export ODOO_HOSTING=odoo_sh`. Niespójność jest realna, ale ograniczona (env vs URL nie kolidują, bo nie współpracują). NIE blocker dla celu LOKALNego.

### 📋 OVERALL GRADE: **A** → ✅ APPROVE

REKOMENDACJE:
1. **(MEDIUM, follow-up)** Domknąć TD-1: wpiąć `classify_hosting` przez pipeline-context → jedno źródło prawdy o hostingu; usunąć rozjazd env↔URL.
2. **(LOW, quick win ~15 min)** Clamp `lines` w `_read_log_on_premise`: `n = max(0, int(lines)); content[-n:] if n else ""`.
3. **(LOW)** Zweryfikować realną ścieżkę logu odoo.sh (`~/logs/odoo.log`) przy dostępie do środowiska (poza zakresem lokalnym ADR-008).

> **/audyt → /qa + main-gate (2026-06-23):** ✅ **APPROVE (Grade A).** Kod SPÓJNY, CZYSTY, ZGODNY z planem /arch. Zero nowych God Nodes (D5 dowiedzione grepem), kontrakty zamrożone (D1/D2), wzorce IN-PATTERN. Jedyne odchylenie (T2b env-selektor) = świadomy, udokumentowany pragmatyzm z follow-up długiem MEDIUM — NIE blokuje. Pattern-drift error-handling: BRAK (sanityzacja spójna z db_manager:36 / ADR-011) → brak ping do /sec.

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review) — ZWERYFIKOWANE PRZEZ /qa (2026-06-23)
> /qa (2026-06-23, `.venv-qa`, Evidence Before Claims): zweryfikowane realnym uruchomieniem; outputy poniżej.
- [x] **US-WIRE-1: 11/11 skili z `SKILL_REGISTRY` osiągalnych z dispatchera.** Dowód: `test_no_orphaned_skills.py` — **14 passed** (12× parametryzowany `test_skill_is_reachable_from_dispatcher[*]` + agregat + sanity + nowy NEG). Smoke 3 wcześniej osieroconych (realny `Dispatcher().classify_intent`, fallback): „pokaż logi i traceback…z deploya" → `ODOO_DEVOPS_GITHUB`; „sprawdź zaksięgowane faktury i VAT" → `FINANCIAL_AUDIT`; „zrób deploy na branch staging github" → `ODOO_DEVOPS_GITHUB`. *(Uwaga BUG-HUNT poniżej: „błąd w księgowości po deployu" → `ODOO_DEVOPS_GITHUB` — świadomy trade-off /dev, deploy > księgowość; NIE blocker.)*
- [x] **US-WIRE-2: `read_odoo_log` hosting-aware.** Sygnatura `read_odoo_log(lines: int = 50) -> str` NIETKNIĘTA; `TOOL_REGISTRY` = **8 narzędzi** (potwierdzone importem); schemat OpenAI bez „symulowane" (`'symulowane' in schema = False`). on-premise: realny plik `ODOO_LOG_PATH` zwraca ostatnie N linii (`lines=3` → L18/L19/L20). Brak pliku → jawny błąd z instrukcją `ODOO_LOG_PATH`, `'symulowane' present = False`. odoo.sh: SSH `tail -n {lines}` argv-list, `shell=False` (mock). Słowo „symulowane" w całym `swarm/` występuje TYLKO w docstringu jako opis negatywny — zero w outputach/schemacie. *(`test_read_odoo_log.py` — 6 passed.)*
- [x] **US-WIRE-3: guard + LUKA domknięta przez /qa.** /qa dodał BRAKUJĄCY test NEGATYWNY `test_guard_red_when_skill_artificially_orphaned` (META-test: monkeypatch dispatchera → sztuczne osierocenie `ODOO_SH_LOGS` → agregat guardu MUSI je wykryć). Dowód non-tautologii: `BASELINE orphaned=[]`; `CRIPPLED orphaned=['ODOO_SH_LOGS']`; `GUARD WYKRYWA REGRES=True`. Guard nie jest tautologiczny — realnie RED-uje przy regresie routingu.
- [x] **Regresja (HARD GATE): pełna `pytest -m 'not e2e' -q` → `323 passed, 2 skipped, 12 deselected (e2e), 0 failed` w 639.71s** (2026-06-23, `.venv-qa`, Py 3.14.4, pytest 9.1.0). Baseline 303 → +20 nowych (T3: 13 + 1 NEG /qa, T2a/T2b: 6). 323 = 322 (/dev) + 1 nowy test NEG /qa. **Zero regresji.**
- [x] /audyt ✅ (Sekcja B½ — Grade **A**, APPROVE; zero nowych God Nodes dowiedzione grepem; T2b dewiacja = akceptowalny pragmatyzm + follow-up dług MEDIUM). /sec ✅ (Sekcja D). *(/qa pre-walidacja Sekcji D: wszystkie 5 ścieżek błędu `VaultAuthProvider.get_ssh_credentials` zwracają sanityzowany `PipelineError` bez echa sekretów — `leaks_internal=False`; finalna pieczęć należy do /sec.)*
- [x] D3 rozstrzygnięte: T2b zaimplementowane jako SSH `tail` (zgodnie z decyzją usera 2026-06-23).

> ⚠️ **DROBNE UWAGI /qa (boundary, LOW — NIE blockery):** `_read_log_on_premise` używa `content[-lines:]`: `lines=0` → zwraca CAŁY plik (semantycznie powinno 0/pustkę); `lines=-1` → wszystko oprócz pierwszej linii. Kontrakt nie definiuje 0/ujemnych, LLM woła `lines=50` — odnotowane do utwardzenia (clamp `max(0, int(lines))`), nie wstrzymuje PASS.

### Close Checklist
- [ ] Zadania Sekcji B = ✅ (T2b/T-DEFER mogą być świadomie odroczone), status → `DONE`, `closed`.
- [ ] Lessons Learned (Sekcja F) + ewentualne instynkty.
- [ ] Zmergowane do `main`.

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa po realizacji)

### /dev (2026-06-23) — realizacja TDD T3→T1→T2a→T2b
- **Kanibalizacja słów-kluczy to realne ryzyko routingu.** Pierwsza wersja gałęzi logów używała bare `"log"` → złapała „testy dla **log**owania" (`test_forward_message`) i przeniosła ją z kategorii C do E. Fix: precyzyjne formy `logi/logu/logó/loga/logach/traceback/stacktrace` (NIE bare „log"). **Instynkt:** przy dokładaniu heurystyki słownej zawsze sprawdź kolizje z istniejącymi intencjami w testach (`grep` po keyword w `tests/`).
- **Kolejność `elif` = priorytet routingu.** DEVOPS (`deploy/branch/staging/github/odoo.sh/push`) musi być PRZED gałęzią logów, a obie PO `kto/kiedy` (AUDIT_HISTORY) i `audyt/security` (SECURITY_AUDIT), inaczej „kto zmienił fakturę" trafiłaby do FINANCIAL_AUDIT zamiast historii zmian. Świadomy trade-off: „błąd **deploy**" → DEVOPS (nie logi), bo samo słowo „deploy" jest silniejszym sygnałem operacji.
- **`E_RESEARCH` przestało być osierocone w ROUTING_TABLE.** `skill_name=None` → `ODOO_SH_LOGS` jako domyślny dla researchu logów; fallback heurystyk nadal nadpisuje bardziej specyficznym skilem (`final_skill = skill_name or route.get("skill_name")`).
- **⚠️ DEVIACJA od literalnego brzmienia D3/T2b — DO DECYZJI /arch:** artefakt mówi „gdy `classify_hosting==odoo_sh`". `EnvironmentRecon.classify_hosting(url)` wymaga URL-a połączonego klienta, którego warstwa narzędzi (`read_odoo_log(lines)`) NIE ma w sygnaturze (kontrakt zamrożony). Użyto selektora `os.environ["ODOO_HOSTING"] == "odoo_sh"` jako pragmatycznego przełącznika gałęzi. Jeśli /arch chce wpiąć realny `classify_hosting`, trzeba przekazać hosting do warstwy tooli (np. przez kontekst pipeline) — to osobna zmiana kontraktu, poza zakresem WIRE-01.
- **PIN do vaultu z env (`VAULT_PIN`), sekrety SSH z vaultu.** Wartości host/user/klucz NIGDY nie idą z env — tylko z `vault.load_vault` (klucz `ODOO_SH_SSH`). Jedynie PIN autoryzacyjny z env, spójnie z `pipeline.py:202`.
- **Stub→real bez zmiany kontraktu:** nazwa `read_odoo_log` i `lines` zachowane → `TOOL_REGISTRY` nadal 8 narzędzi, `allowed_tools`/`pipeline.py:83` bez zmian, schemat OpenAI bez „symulowane".

### /qa (2026-06-23) — weryfikacja funkcjonalna (7 kroków)
- **Guard pozytywny ≠ guard wiarygodny.** /dev dostarczył tylko test pozytywny (każdy skill osiągalny) i oznaczył US-WIRE-3 jako `[~]` z otwartą decyzją. /qa domknął lukę testem NEGATYWNYM (`test_guard_red_when_skill_artificially_orphaned`) i osobno UDOWODNIŁ non-tautologię (CRIPPLED orphaned=['ODOO_SH_LOGS'], GUARD WYKRYWA REGRES=True). **Instynkt:** każdy test-guard wymaga pary pozytyw+negatyw — bez RED-proof guard może być ślepy na regres.
- **Kanibalizacja routingu — zweryfikowane empirycznie 11 próbek granicznych.** Kolejność `elif` trzyma: `audyt`→SECURITY_AUDIT, `kto/kiedy zmienił fakturę`→ODOO_AUDIT_HISTORY (nie FINANCIAL), `etl`→ETL, `kod`→DEVELOPER, `testy dla logowania`→MAGIC_FIX (bare-„log" trap unikany). Trade-off /dev potwierdzony: „błąd w księgowości po deployu"→DEVOPS (deploy > księgowość).
- **Boundary `content[-lines:]` (LOW):** `lines=0`→cały plik, `lines=-1`→wszystko-bez-pierwszej. Edge nieobsłużony, ale poza kontraktem (LLM woła 50). Wpis do Error Registry.

### Handoff
> **/arch → /dev (2026-06-23):** zakres zatwierdzony przez usera, status **🟡 In Progress**. D3 ✅ rozstrzygnięte (SSH `tail`). /dev startuje wg kolejności TDD: T3 → T1 → T2a → T2b. Baseline regresji: pytest 303 passed / 0 failed.
> **/qa → /audyt + /sec (2026-06-23):** ⚠️ **PASS z drobnymi uwagami.** Funkcjonalność WIRE-01 zweryfikowana dowodami: regresja `323 passed / 0 failed`, guardy 14+6 zielone, US-WIRE-3 luka domknięta. Otwarte: pieczęć /sec (Sekcja D — pre-zwalidowane przez /qa, brak leaków), /audyt (spójność). Drobne LOW boundary `content[-lines:]` do utwardzenia (nie blocker).
