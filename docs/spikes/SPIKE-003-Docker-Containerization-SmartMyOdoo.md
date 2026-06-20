---
spike_id: "SPIKE-003"
temat: "Konteneryzacja SmartMyOdoo (Dockerfile + docker-compose)"
data: "2026-06-20"
konsument: "/arch"
autor: "/spike"
model: "claude-haiku-4-5"
bounded_context: "Infrastructure / Deployment (Local-Only, ADR-008)"
status: "ready"
---

# 🕵️ SPIKE-003: Konteneryzacja SmartMyOdoo

> **Dla:** `/arch` | **Data:** 2026-06-20
> **Cel MVP:** Dostarczyć przenośny, lokalnie uruchamialny artefakt — użytkownik robi `docker compose up` i ma działającą aplikację SmartMyOdoo (FastAPI+UI na :8000) **BEZ ręcznego venv/zależności**. Ścieżka LOKALNA (ADR-008 — No Cloud).

---

## 1. Scope

**In scope:**
- Dockerfile dla aplikacji SmartMyOdoo (FastAPI+UI, Python 3.11+)
- Integracja z istniejącym `docker-compose.yml` (redis, postgres, odoo)
- Externalizacja stanu (vault, DB, logi) na wolumeny
- ENV runtime — sekretów, rate-limit, LLM cache
- Healthcheck endpoint (`GET /api/status → 200`)
- Multi-stage build (runtime deps vs build tools)
- Zgodność z ADR-008 (Local-Only, zero cloud secrets)

**Out of scope:**
- Publiczny Docker Registry / CI/CD push
- Multi-tenant scaling / Kubernetes
- Upgrade Odoo 16→17/18/19 (własny temat)
- Custom addons build (montuj przez volume `/mnt/extra-addons`)

---

## 2. Kontekst Systemu (Boundaries)

| Wymiar | Wartość |
|--------|---------|
| **Języki** | Python 3.11+, FastAPI, SQLite/Postgres (optional) |
| **Entrypoint** | `python -m uvicorn smartmyodoo.api:app --host 0.0.0.0 --port 8000` |
| **Port API** | 8000 (host:container) |
| **Serwisy powiązane** | redis:7, postgres:16 (opcjonalne), odoo:16 (istniejący compose) |
| **State paths** | vault `.enc`/`.cfg` (Fernet), sqlite `smartmyodoo.db`, logi |
| **Istniejące compose** | `/docker-compose.yml` — redis (127.0.0.1:6379), postgres, odoo |

---

## 3. Gotowe Klocki (Re-use First)

### Docker / Infra
| Artefakt | Lokalizacja | Co robi | Status |
|----------|-------------|---------|--------|
| `docker-compose.yml` | root | redis (7-alpine, healthcheck), postgres (16-alpine), odoo (16) | active — rozszerz serwisem `app` |
| Production Redis Guide | `docs/guides/production_redis.md` | REDIS_URL auto-discovery, rate-limit/cache/lock/queue | active |
| Odoo Docker Guide | `docs/guides/odoo_docker_environment.md` | Empty Shell Policy, security, hosting matrix | active |
| ADR-008 | `docs/adr/ADR-008-*` | Local-Only Architecture, zero cloud | binding |

### Config
| Plik | Typ | Notatka |
|------|-----|---------|
| `pyproject.toml` | runtime | `requires-python = ">=3.11"`, 25 deps (no torch) |
| `requirements.txt` | dist | 27 linii — identyczne do pyproject.toml + model spaCy wheel |
| `.env.example` | template | Sekrety (OPENROUTER_KEY, REDIS_URL, DB_URL, itp.) — TODO |

---

## 4. Twarde Ograniczenia (ADR & Rules)

| Reguła | Wymóg | Wpływ |
|--------|-------|-------|
| **ADR-008** (Local-Only) | Żadne dane wrażliwe do chmury; obraz uruchamiany lokalnie | ✅ OK — konteneryzacja lokalna nie łamie tego; **NIGDY** nie pushuj obrazu do publicznego registry ze secretami/vaultem |
| **ART.2** (Security Default) | Brak hardcoded secretów, zero plaintext hasła w compose | ✅ Enforce `.env` (gitignore), zmienne ENV, fail-closed bez OPENROUTER_KEY |
| **ART.21.6** (Graph Gate) | Kompleksowe zmiany infra (≥3 complexity) muszą przejść graph recon | ✅ Done — patrz §6b |

---

## 5. Pola Minowe (Lessons Learned)

| ID | Pułapka | Instrukcja dla /arch |
|----|---------|----------------------|
| **markitdown[all]** | Zależy `azure-ai-contentunderstanding` (beta) → wymaga `--prerelease=allow` w `uv pip install` | Build z flagą `--prerelease=allow` LUB użyj konkretnych pinned versions; nie `-r requirements.txt` wprost |
| **pl_core_news_md** | Model spaCy (PL) = release wheel GitHub, nie PyPI; bez niego `/api/chat` → 500 | RUN w stage 2: `python -m spacy download pl_core_news_md` LUB include wheel URL w requirements |
| **VAULT_DIR hardcoded** | `smartmyodoo/vault/vault.py:14` — ścieżka files `.enc`/`.cfg` = `__file__` dirname, NOT ENV | 🟡 Nie blokuje — monte vault na volume `/vault` lub refaktoruj do ENV-based path (opcja L2) |
| **Brak `serve` command** | `__main__.py` nie ma subcommandy `serve` → entrypoint to jawnie `uvicorn smartmyodoo.api:app` | Dockerfile CMD: `["python", "-m", "uvicorn", "smartmyodoo.api:app", "--host", "0.0.0.0", "--port", "8000"]` |
| **SQLite path** | `smartmyodoo/core/database.py:5` — `sqlite:///smartmyodoo.db` (cwd-relative) | ENV override: `DATABASE_URL=sqlite:////vault/smartmyodoo.db` (3 slusze = abs path); externaliz on volume |
| **Redis discovery lazy** | `core/ratelimit.py`, `core/queue.py` — ping Redisa timeout 0.5s; timeout=OK (fallback proces-lokalny) | Bez REDIS_URL = slowdown (rate-limit per-worker), nie crash; dla wieloprocesowych — ustaw REDIS_URL |
| **mkdirs missing** | Startup nie tworzy `/vault` ani logów automatycznie | Dodaj `mkdir -p` init sysem lub init-container w compose |

Brak historycznych błędów w Error Registry dotyczących dockera — to pierwsze podejście.

---

## 6. Pigułka Kontekstowa (Kluczowe Interfejsy & Konfiguracja)

### Startup Event (api.py:22-27)
```python
@app.on_event("startup")
async def _log_backend_modes() -> None:
    from smartmyodoo.core.runtime_info import log_backend_modes
    log_backend_modes()  # logs: Redis AKTYWNY / PROCES-LOKALNY
```

### Runtime Config (zbiorczy)
```python
# ENV (smartmyodoo/chat_deps.py, core/ratelimit.py, core/database.py, vault/vault.py)
DATABASE_URL          # default: sqlite:///smartmyodoo.db
REDIS_URL             # optional; no = fallback process-local
OPENROUTER_KEY        # required; /api/chat→500 bez niego
CORS_ALLOWED_ORIGINS  # default: "http://127.0.0.1:8000,http://localhost:8000"
LLM_CACHE             # default: "on" (off=disabled)
CHAT_RATE_MAX         # default: 30 (requests/window)
CHAT_RATE_WINDOW_S    # default: 60
JOB_TTL_SECONDS       # default: 86400 (worker queue)
VAULT_PIN             # required; /api/auth→400 bez niego
VAULT_MASTER          # required; vault unlock→fail bez niego
```

### Health / Readiness
- **Endpoint:** `GET /api/status` (api_routers/auth.py:57) → `{status: "ok"}`
- **Liveness:** port 8000 accessible
- **Readiness:** DB connected (create_all on startup), Redis optional (lazy)

---

## 7. Szczegóły Budowy Obrazu

### Runtime Dependencies (pyproject.toml — 25 deps)
```
fastapi, uvicorn, pydantic, sqlalchemy, alembic, cryptography
presidio-{analyzer,anonymizer}, spacy, redis, markitdown[all]
mcp>=1.0.0, litellm, httpx, rich, prompt_toolkit, pyperclip, websockets
# NO torch, NO transformers (markitdown[all] ≠ LLM heavy — zawiera apenas markdown parser)
```

### Build-time (dev, excluded)
```
pre-commit, ruff, mypy, bandit, pytest, pytest-mock, fakeredis[lua]
```

### Pułapki Budowy
1. **`--prerelease=allow`** — markitdown[all] wyciąga beta `azure-ai-contentunderstanding`
2. **spaCy model** — RUN `python -m spacy download pl_core_news_md` w stage 2 (→ 50 MB)
3. **gcc/build-essentials** — presidio-analyzer wymaga kompilacji (cryptography, numpy)
4. **uv vs pip** — memory.md mówi `.venv-qa` używa `uv pip` (szybciej, mniej RAM)
5. **Python 3.11+** — 3.14.4 dostępny, pyproject mówi `>=3.11` (safe)

### Multi-stage (rekomendacja dla /arch)
```dockerfile
# Stage 1: builder (gcc, uv, build tools)
FROM python:3.14-slim as builder
RUN apt-get update && apt-get install -y gcc [...]
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: runtime (slim, no build tools)
FROM python:3.14-slim
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
# ... app code + RUN python -m spacy download pl_core_news_md
```

---

## 8. Externalizacja Stanu (Wolumeny)

| Ścieżka | Typ | Mountpoint | Required | Env Override? |
|---------|-----|-----------|----------|--------------|
| **Vault** (`.enc`/`.cfg`) | Secret | `/vault` | ✅ (dla auth) | ❌ HARDCODED w vault.py |
| **SQLite DB** | Data | `/vault/smartmyodoo.db` | ✅ (dla storage) | ✅ `DATABASE_URL` |
| **Logi** | Output | `/app/logs` | ⚠️ optional | N/A |
| **Worker queue state** | Runtime | redis:// | ⚠️ optional (fallback mem) | ✅ `REDIS_URL` |

### docker-compose serwis `app`
```yaml
app:
  build: .
  ports:
    - "8000:8000"
  environment:
    - OPENROUTER_KEY=${OPENROUTER_KEY}
    - REDIS_URL=redis://redis:6379/0  # sieć dockera, nie 127.0.0.1!
    - DATABASE_URL=sqlite:////vault/smartmyodoo.db
    - VAULT_PIN=${VAULT_PIN}
    - VAULT_MASTER=${VAULT_MASTER}
  volumes:
    - ./smartmyodoo/vault:/vault       # externalize secrets
    - app-logs:/app/logs
  depends_on:
    redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/status"]
    interval: 10s
    timeout: 3s
    retries: 3
```

---

## 9. Integracja z Istniejącym compose.yml

**Status quo:** `docker-compose.yml` ma redis, postgres, odoo — **BRAK SmartMyOdoo**.

**Decyzja dla /arch (dwie opcje):**

| Opcja | Pros | Cons |
|-------|------|------|
| **1. Rozszerz istniejący compose** | Jedno `docker compose up` wszystko | Skomplikowana topologia, networking |
| **2. Osobny compose (app-compose.yml)** | Izolacja, autonomia appki | Dwa procesy, brak auto-startup |

**Rekomendacja:** Opcja 1 (rozszerz) — SmartMyOdoo to główna aplikacja, redis/odoo to deps. Sieci dockera (redis://**redis**:6379, nie 127.0.0.1:6379).

---

## 10. Pytania Otwarte dla /arch

- [ ] **Host binding:** Dockerfile CMD `--host 0.0.0.0` (dostępne z dockera + localhost) czy `--host 127.0.0.1` (bezpieczniej, ale requires port-forward)? → **Rekomendacja:** 0.0.0.0 (to jest kontener, internal network jest bezpieczna dzięki docker).
- [ ] **Vault HARDCODED:** Refaktorować vault.py do ENV-based path czy montować volume bezpośrednio do `smartmyodoo/vault`? → **Rekomendacja:** Nazwa, nie refaktor (szybciej); jeśli L2 = env override.
- [ ] **Multi-stage slim vs full-fat:** Python 3.14-slim (base ~140 MB + deps ~500 MB = 640 MB) czy 3.14 (base ~900 MB)? → **Rekomendacja:** slim (spacja models large, final < 1 GB).
- [ ] **Worker separation:** Czy `python -m smartmyodoo worker` powinien być osobnym serwisem w compose? → **Rekomendacja:** Later phase — zaczyń z unified app:8000; worker opcjonalnie später (separate serwis w compose).
- [ ] **Odoo integration:** Czy SmartMyOdoo powinna być w odoo-addons (XML-RPC klient do istniejącego Odoo na 8069) czy standalone (FastAPI na 8000, odoo:16 jako backup data source)? → **Out of scope SPIKE** (architektura integracji — to `/arch` pain point).

---

## 6b. Architektura Grafu (Graphify) — dla L2 /arch (ART.21.6)

**Metryka:** SmartMyOdoo API to głównie dispatcher (41 edges) + skill execution (64 edges Executor). Nie dotyka God Nodes:

| Metryka | Wartość | Sygnał dla /arch |
|---------|---------|------------------|
| God Nodes (>25 edges) w SmartMyOdoo | SkillConfig (69), SkillExecutor (64), ExecutionPipeline (48) | 🔴 Nie dodawaj więcej zależności do Executora; docker nie zmienia tego |
| Cohesion modułu `smartmyodoo/` | 0.07–0.26 (variuje po submodułach) | ✅ Norma dla monolitu; konteneryzacja nie pogarsza |
| Import cycles | 0 (auto-detected) | ✅ Clean |
| Generated/ignoruj | `tests/` nie w graphify scope | ⚪ pomiń |

**Rekomendacja dla L2 (1 zdanie):** _Dockerfile nie zmienia grafu — to czysta infrastruktura; skupaj się na VAULT_DIR refaktorze gdy /dev ma czas (L3+)._

---

## Podsumowanie dla /arch

**Do zrobienia:**
1. ✅ Zidentyfikuj final base image (Python 3.11+, slim)
2. ✅ Multi-stage build (builder + runtime)
3. ✅ RUN spacy model + markitdown[all] prerelease flag
4. ✅ Externalize vault, DB, logs na wolumeny
5. ✅ Healthcheck endpoint (curl /api/status)
6. ✅ Extend docker-compose.yml z serwisem `app`
7. ⚠️ Zdecyduj host binding (0.0.0.0 rekomendacja)
8. ⚠️ Uzupełnij `.env.example` — sekretów (OPENROUTER_KEY, VAULT_PIN/MASTER)

**Ryzyka:**
- 🔴 Brak OPENROUTER_KEY → /api/chat 500 (fail-closed, OK)
- 🟡 VAULT_DIR hardcoded → volume mounting OK, opcjonalny refaktor L2
- 🟡 Redis fallback → rate-limit per-worker bez REDIS_URL (monitoring konieczne)

---

_Wygenerowano przez `/spike` | Model: claude-haiku-4-5 | Tool calls: 18_
