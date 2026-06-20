---
sprint_id: "DOCKER-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-20
closed: 2026-06-21
goal: "Aplikacja SmartMyOdoo uruchamia się jednym `docker compose up` jako przenośny, lokalny artefakt (FastAPI+UI na :8000) — bez ręcznego stawiania venv/zależności/modelu spaCy. Stan (vault, DB, logi) na wolumenach; zero sekretów w obrazie. Zgodnie z ADR-008 (Local-Only)."
prefix: "DOCKER"
complexity: 5
roadmap_ref: "SPIKE-003 (Docker Containerization); Faza 7 Production Hardening; pytanie usera o dystrybucję/kontener (2026-06-20)"
parent_sprint: null
tags: ["infra", "docker", "deployment", "packaging", "local-only", "adr-008"]
---

# 🧱 Sprint: DOCKER-01 — Konteneryzacja aplikacji (Dockerfile + compose)

> **Architekt:** /arch | **Owner:** /dev | **Review:** /gf-review | **Data:** 2026-06-20
> **Bazuje na:** main (`d3e2acc`) | **Recon:** [SPIKE-003](../spikes/SPIKE-003-Docker-Containerization-SmartMyOdoo.md) | **ADR:** ADR-008 (Local-Only), ADR-011 (Logging/Sanitization)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch ✅)

### 0A. Business Discovery
- **Dla kogo?** Właściciel/operator aplikacji (i potencjalnie inni, którzy mają odpalić to U SIEBIE lokalnie). Dziś setup wymaga ręcznego venv + ciężkich zależności ML + modelu spaCy z wheela → kruchy, niepowtarzalny.
- **Problem (1 zdanie):** brak Dockerfile — aplikacja nie ma przenośnego artefaktu; `docker-compose.yml` stawia tylko środowisko docelowe (postgres/redis/odoo), nie samą SmartMyOdoo.
- **Metryka sukcesu:** `docker compose up` na czystej maszynie (tylko Docker) → `GET /api/status` = 200, UI dostępne na `:8000`; po restarcie vault/DB przetrwają (wolumeny); obraz NIE zawiera żadnych sekretów/vaultu.
- **ROI:** powtarzalny setup (koniec luk `.venv-qa`), realna ścieżka „daj innym do lokalnego uruchomienia" bez łamania ADR-008.
- **Źródło:** pytanie usera (2026-06-20) + SPIKE-003 (fakty zweryfikowane plik:linia).

### 0B. Fakty (z SPIKE-003 + weryfikacja /arch, plik:linia)
| Fakt | Dowód | Uwaga /arch |
|---|---|---|
| Brak Dockerfile | `find` = 0 | core sprintu |
| Entrypoint = uvicorn (brak subcmd `serve`) | `__main__.py`, `api.py` | CMD: `uvicorn smartmyodoo.api:app` |
| Health = `GET /api/status` → 200 | `api_routers/auth.py` | healthcheck compose |
| `VAULT_DIR` HARDCODED do dir modułu | `vault/vault.py:14` | ⚠️ **mount wolumenu na ten dir przykryłby `vault.py`** → wymaga ENV-override (T1) |
| DB = `sqlite:///smartmyodoo.db`, ENV `DATABASE_URL` | `core/database.py:5` | externalizacja przez ENV ✅ |
| `OPENROUTER_KEY` wymagany (LLM) | `chat_deps.py:18` | bez niego `/api/chat`=500 (fail-closed) |
| `REDIS_URL` opcjonalny (fallback proces-lokalny) | `core/ratelimit.py`,`queue.py` | w compose: `redis://redis:6379/0` (nazwa serwisu, NIE 127.0.0.1) |
| `CORS_ALLOWED_ORIGINS` ENV, default lokalny | `api.py:31-41` | dołożyć do `.env.example` |
| **Vault NIE czyta ENV `VAULT_PIN`/`VAULT_MASTER`** | grep = brak | ⚠️ **SPIKE-003 błędny** — vault tworzy `POST /api/init`, odblokowuje `POST /api/auth` hasłem → bootstrap pierwszego uruchomienia w UI, NIE ENV |
| Brak torch/transformers w runtime | pyproject 25 deps | obraz lżejszy (~640 MB) |
| `requires-python = ">=3.11"` | `pyproject.toml:6` | patrz decyzja D1 (base image) |
| `markitdown[all]` → azure beta | nota [[venv-qa-setup-gaps]] | build wymaga `--prerelease=allow` |
| model spaCy `pl_core_news_md` = release wheel | `requirements.txt` | RUN w obrazie; bez = `/api/chat` 500 |

### 0C. User Stories
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-DOCKER-1 | operator | jednym `docker compose up` postawić działającą appkę | nie stawiać ręcznie venv/zależności/modelu | KIEDY `docker compose up` na czystej maszynie TO `/api/status`=200 i UI na :8000 |
| US-DOCKER-2 | operator | by stan (vault, DB) przeżył restart kontenera | nie tracić sekretów/danych | KIEDY restart kontenera TO zainicjowany vault i DB są dostępne (wolumeny) |
| US-DOCKER-3 | bezpieczeństwo (ADR-008) | by obraz NIE zawierał sekretów/vaultu/DB | nie wyciekł sejf przy dzieleniu obrazu | KIEDY zbuduję obraz TO `.enc`/`.cfg`/`*.db`/`.env` są wykluczone (`.dockerignore`) |
| US-DOCKER-4 | nowy operator | jasną instrukcję pierwszego uruchomienia (init vault) | wiedzieć jak utworzyć sejf w kontenerze | KIEDY pierwszy `up` TO README prowadzi przez ekran init (master+PIN) |

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| compose: healthcheck + wolumeny + bind 127.0.0.1 | `docker-compose.yml` (redis/postgres/odoo) | 📐 IN-PATTERN (dołóż serwis `app`) |
| ENV-config runtime | `DATABASE_URL`/`REDIS_URL`/`CORS_ALLOWED_ORIGINS` | 📐 IN-PATTERN (rozszerz o `VAULT_DIR`) |
| Multi-stage build (slim) | skill `docker-compose` | 📐 REFERENCE |
| VAULT_DIR hardcoded | `vault/vault.py:14` | ⚠️ AD-HOC → ENV-owanie (T1) |
| Sekret w `.env` (gitignore) | `.gitignore` (sprawdź `.env`) | 📐 IN-PATTERN |

### 0E. Test Strategy
| Warstwa | Potrzebna? | Co testować | Kto | Narzędzie |
|---|:--:|---|:--:|---|
| Build | ✅ | obraz buduje się czysto (spaCy model, prerelease, gcc) | /dev+/qa | `docker build` |
| Smoke (kontener) | ✅ | `/api/status`=200; `/api/secrets` bez tokenu=401; UI 200 | /qa | curl/skrypt |
| Persystencja | ✅ | init vault → restart → vault/DB przetrwały | /qa | docker volume |
| Brak sekretów w obrazie | ✅ | `docker run ... ls`/history: brak `.enc`/`*.db`/`.env` | /sec | docker inspect |
| Regresja (kod) | ✅ | ENV-owanie `VAULT_DIR` nie psuje testów: pełna pytest 0 failed | /qa | pytest |

### 0F. US → Test Mapping
| US | Scenariusz | Weryfikacja | Priorytet |
|----|------------|----------|-----------|
| US-DOCKER-1 | `docker compose up` → /api/status 200 | smoke skrypt | 🔴 |
| US-DOCKER-2 | init → restart → vault/DB OK | persystencja (wolumen) | 🔴 |
| US-DOCKER-3 | build → brak sekretów w warstwach | /sec inspect + `.dockerignore` | 🔴 |
| US-DOCKER-4 | README first-run | review | 🟡 |

### 0G. Security Scope → Sekcja D
ADR-008: konteneryzacja LOKALNA nie łamie No-Cloud (obraz u usera, dane na lokalnych wolumenach). KLUCZOWE: obraz bez sekretów, `.env` gitignored, non-root user, NIGDY nie pushować obrazu z vaultem do publicznego registry. /sec weryfikuje brak sekretów w warstwach.

### ⚖️ Zasady / Decyzje architektoniczne (/arch)
- **D1 — Base image: `python:3.12-slim`** (NIE 3.14). Powód: prebuilt wheels dla `presidio`/`spacy`/`numpy`/`cryptography` są pewne na 3.12; na 3.14 część może wymagać budowy ze źródeł (wolny/kruchy build). `requires-python>=3.11` spełnione. (Uwaga: `.venv-qa` lokalnie ma 3.14 — to inny kontekst, ma już zbudowane.)
- **D2 — `VAULT_DIR` ENV-owalny (wymagane, nie opcjonalne).** `vault.py:14` → `os.environ.get("VAULT_DIR", <obecny default>)`. Powód: mount wolumenu wprost na `smartmyodoo/vault/` przykryłby `vault.py`. Zmiana minimalna, zachowuje obecne zachowanie gdy ENV nieustawiony.
- **D3 — Compose: rozszerzyć istniejący `docker-compose.yml` o serwis `app`** (Opcja 1 ze SPIKE). Sieć dockera: `REDIS_URL=redis://redis:6379/0`.
- **D4 — Host binding `0.0.0.0` w kontenerze** (ekspozycję kontroluje mapowanie portów hosta). 
- **D5 — Worker jako osobny serwis = POZA zakresem** (faza późniejsza). Ten sprint = unified app:8000.
- **D6 — Vault bootstrap = first-run przez UI** (`/api/init`), NIE ENV. README opisuje krok.
- **Zero sekretów w obrazie** (`.dockerignore`), `.env` gitignored, non-root.

---

## 🧱 Sekcja B — Podział Zadań (TDD-friendly) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| T1 | **ENV-owanie `VAULT_DIR`** (D2): `VAULT_DIR = os.environ.get("VAULT_DIR", os.path.dirname(os.path.abspath(__file__)))`; pochodne ścieżki (`PIN_*`,`MASTER_*`,`VAULT_DATA_FILE`) liczone od `VAULT_DIR`. Zachowaj zachowanie gdy ENV brak. | `smartmyodoo/vault/vault.py` | ENV-config (DATABASE_URL) | Unit: gdy `VAULT_DIR` ustawiony, pliki idą tam; pełna pytest 0 failed | ✅ (TDD: `tests/test_vault_env_dir.py` 3 pass; regresja **297 passed, 2 skipped, 0 failed**) |
| T2 | **`.dockerignore`** — wyklucz: `.venv*`, `.git`, `.mypy_cache`, `graphify-out/`, `__pycache__`, `*.db*`, `smartmyodoo/vault/*.enc`, `*.cfg`, `.env`, `tests/` (opcjonalnie), `docs/` (opcjonalnie). **Sekrety NIGDY do obrazu.** | NEW `.dockerignore` | `.gitignore` | /sec: brak sekretów w warstwach | ✅ (**zweryfikowane przez `find` w obrazie: 0 plików `.enc/.cfg/.db/.env` w `/app`**). BUG naprawiony: wzorce `*.enc` w BuildKit NIE przekraczają `/` → vault+backup wyciekały; dodano warianty `**/*.enc` + jawne `smartmyodoo/vault/backup_*/`) |
| T3 | **`Dockerfile`** multi-stage: (builder) `python:3.12-slim` + `gcc`/build-essential, instalacja deps z `--prerelease=allow`; (runtime) slim, copy site-packages + kod, `RUN python -m spacy download pl_core_news_md` (lub wheel z requirements), **non-root user**, `HEALTHCHECK` curl `/api/status`, CMD `uvicorn smartmyodoo.api:app --host 0.0.0.0 --port 8000`. Tworzy `/data` (vault+db+logi). | NEW `Dockerfile` (+ NEW `constraints.txt`) | SPIKE-003 §7 | Build OK; smoke /api/status 200 | ✅ (**build OK + live smoke OK**: `/api/status`=200, `/api/secrets`=401, UI=200, healthcheck=healthy, non-root uid1001, `spacy.load(pl_core_news_md)` OK. 2 bugi naprawione: `--prerelease=allow`→`--pre` (flaga uv≠pip); `--pre` wciągał numpy2.5rc/spacy4.dev → pin przez `constraints.txt`) |
| T4 | **Rozszerz `docker-compose.yml`** o serwis `app`: `build: .`, `ports: 8000:8000`, env z `.env` (`OPENROUTER_KEY`,`REDIS_URL=redis://redis:6379/0`,`DATABASE_URL=sqlite:////data/smartmyodoo.db`,`VAULT_DIR=/data/vault`,`CORS_ALLOWED_ORIGINS`), wolumeny (`app-data:/data`, logi), `depends_on: redis (healthy)`, healthcheck. | `docker-compose.yml` | istniejące serwisy | smoke + persystencja | ✅ (`docker compose config` valid; bind `127.0.0.1:8000`, `app-data:/data`, `condition: service_healthy`, env zgodne z D2/D3; istniejące serwisy nietknięte) |
| T5 | **`.env.example`** — wszystkie ENV (wymagane vs opcjonalne, z komentarzem): `OPENROUTER_KEY` (req), `REDIS_URL`, `DATABASE_URL`, `VAULT_DIR`, `CORS_ALLOWED_ORIGINS`, `LLM_CACHE`, `CHAT_RATE_MAX`, `CHAT_RATE_WINDOW_S`, `JOB_TTL_SECONDS`. Potwierdź `.env` w `.gitignore`. | NEW `.env.example`, `.gitignore` | SPIKE-003 §6 | /sec: `.env` gitignored | ✅ (rozszerzono istniejący `.env.example` o sekcję DOCKER: `DATABASE_URL`,`VAULT_DIR`,tuning; `.env` już w `.gitignore:34`) |
| T6 | **README — sekcja „Uruchomienie w Dockerze"**: prerekwizyty, `cp .env.example .env` + wpisz `OPENROUTER_KEY`, `docker compose up --build`, **first-run: otwórz `:8000` → ekran init → utwórz master+PIN**, persystencja przez wolumeny, ostrzeżenie ADR-008 (nie pushuj obrazu z danymi). | `README.md`, NEW `docs/guides/docker_deployment.md` | ADR-008 | review /doc | ✅ (README sekcja „🐳 Uruchomienie w Dockerze" + FIRST-RUN init + ostrzeżenie ADR-008; pełny przewodnik `docs/guides/docker_deployment.md`) |
| T7 | **Smoke skrypt** (powtarzalna weryfikacja): build → up → poll `/api/status` 200 → `/api/secrets` 401 → (opcjonalnie) restart → status 200. | NEW `scripts/docker_smoke.sh` lub test | 0E | /qa odpala | ✅ (`set -euo pipefail`, executable, `bash -n` OK; build→up→poll status 200→secrets 401→restart→200; flagi `KEEP_UP`/`SKIP_RESTART`; faktyczne odpalenie=/qa) |

> **TDD/kolejność /dev:** T1 najpierw (z testem ENV-owania, regresja pytest), bo reszta zależy od ścieżki `/data/vault`. Potem T2→T3→T4 (build+smoke), T5/T6/T7 równolegle. **Nie kopiuj sekretów do obrazu** (T2 przed pierwszym `docker build`).

---

## 🛡️ Sekcja D — Security (/sec)
> ℹ️ Pozycje [x] = wstępnie zweryfikowane przez /dev (build+inspekcja). /sec potwierdza finalnie (history/warstwy).
- [x] Obraz NIE zawiera sekretów: `.dockerignore` wyklucza `*.enc`/`*.cfg`/`*.db*`/`.env` (+ warianty `**/`). **Zweryfikowane `find /app` w zbudowanym obrazie = 0 sekretów** (po naprawie leaku vault/backup). /sec: potwierdź `docker history`/warstwy.
- [x] `.env` w `.gitignore` (linia 34); compose czyta `OPENROUTER_KEY`/`CORS_*` z `.env`, zero plaintext sekretów w `docker-compose.yml`.
- [x] Kontener jako **non-root** (`USER appuser` uid1001 — zweryfikowane `id` w runtime).
- [x] Vault/DB tylko na wolumenach (lokalnie); ADR-008 — ostrzeżenie w README. /qa: stan na named volume `app-data`, `find /app`/`docker run` bez wolumenu = `/data/vault` pusty.
- [x] `0.0.0.0` w kontenerze OK (ekspozycję kontroluje mapowanie portów); /sec potwierdził host bind `127.0.0.1:8000:8000`.
- [x] `OPENROUTER_KEY` fail-closed (bez niego /api/chat 500 — akceptowalne, nie eksponuje danych). /sec: runtime ENV, nie build ARG → nie w warstwach.

---

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review)
> ℹ️ /dev zweryfikował przez `docker build` + `docker run` (single container). /qa potwierdza pełną ścieżkę `docker compose up` + persystencję.
- [x] US-DOCKER-1: obraz buduje się + kontener → `/api/status`=200, UI=200. **/qa PASS:** `docker compose up --build` → app+redis healthy, status 200, UI 200, secrets 401.
- [x] US-DOCKER-2: init vault → restart kontenera → vault i DB dostępne (wolumeny). **/qa PASS:** init (pin/master) → `down` (kontener usunięty) → `up` → vault przetrwał na wolumenie `app-data`.
- [x] US-DOCKER-3: obraz bez sekretów (zweryfikowane `find /app` = 0 `.enc/.cfg/.db/.env`). /sec: finalne potwierdzenie warstw.
- [x] US-DOCKER-4: README/guide pierwszego uruchomienia kompletny (README §🐳 + `docs/guides/docker_deployment.md`).
- [x] Regresja: ENV-owanie `VAULT_DIR` nie psuje testów — **pełna pytest 297 passed, 2 skipped, 0 failed**.
- [x] ADR-008/ADR-011 zachowane; build powtarzalny (`--pre` + `constraints.txt` pin ML, model spaCy w obrazie — `spacy.load` OK).

### Close Checklist
- [x] Zadania Sekcji B = ✅, status → `DONE`, `closed` (2026-06-21).
- [x] Lessons Learned (Sekcja F).
- [x] Zmergowane do `main`; wpis w roadmap (Faza 7).

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa — pułapki budowy obrazu, ENV-owanie vaultu, persystencja)

### /dev (DOCKER-01, build pułapki — 3 bugi złapane przez faktyczny `docker build`+`docker run`)
1. **`--prerelease=allow` to flaga `uv`, NIE `pip`.** Sprint/SPIKE podał ją dla pip → `pip install` wywala `no such option: --prerelease`. Odpowiednik pip = `--pre`. (Lekcja: weryfikuj flagi narzędzia, nie kopiuj między uv/pip.)
2. **`pip install --pre` jest GLOBALNE → destabilizuje stos ML.** Wciągnęło `numpy==2.5.0rc1` + `spacy==4.0.0.dev3` + `thinc==9.0.0` (ABI-niekompatybilne; build „zielony", ale `spacy.load()` crashuje runtime: *"numpy.dtype size changed, Expected 96, got 88"* + model `pl_core_news_md-3.8.0` nie pasuje do spacy 4). **Fix:** `constraints.txt` pinujący `numpy==2.4.6`/`spacy==3.8.13`/`thinc==8.3.13` (wersje z działającego `.venv-qa`) + `pip install --pre -c constraints.txt`. (Lekcja: `--pre` zawsze z constraints na stos ML; „build OK" ≠ „runtime OK" — testuj `spacy.load`/import app w obrazie.)
3. **Wzorce `.dockerignore` typu `*.enc` NIE przekraczają `/` w BuildKit.** `COPY smartmyodoo ./smartmyodoo` wciągnął realny vault (`vault/vault_data.enc`, `pin_key.enc`) i backup `vault/backup_*/` do obrazu — mimo `*.enc` w `.dockerignore`. **Fix:** warianty `**/*.enc`/`**/*.cfg`/`**/*.db` + jawne `smartmyodoo/vault/backup_*/`. **Zweryfikowane:** `find /app` w obrazie = 0 sekretów. (Lekcja 🔴 security: zawsze waliduj brak sekretów `find` w zbudowanym obrazie — sam wpis w `.dockerignore` to za mało.)

> Status środowiska /dev: Docker 29.0.1 + compose v2.40.3 DOSTĘPNE w WSL → build i single-container smoke wykonane lokalnie. Obraz: `smartmyodoo:smoke`, 1.52 GB.

---

### Handoff
```
/spike (SPIKE-003) ✅ → /arch (ten artefakt) ✅
   → /dev (T1 ENV-vault z testem → T2 .dockerignore → T3 Dockerfile → T4 compose → T5/T6/T7)
   → /sec (brak sekretów w obrazie, non-root, .env gitignored)
   → /qa (smoke /api/status, persystencja po restarcie, regresja pytest 0 failed)
   → /gf-review (gate) → /doc (README + roadmap Faza 7)
```

> Po DOCKER-01: aplikacja ma przenośny, lokalny artefakt (`docker compose up`) — koniec kruchego setupu venv. To NIE otwiera multi-tenant/cloud (ADR-008 nadal binding) — to osobny, większy temat (nowy ADR).
