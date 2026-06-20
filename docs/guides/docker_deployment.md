# 🐳 Wdrożenie w Dockerze — SmartMyOdoo

> **Tagi:** `[#docker, #deployment, #local-only, #adr-008, #vault]`
> **Sprint:** DOCKER-01 | **ADR:** ADR-008 (Local-Only), ADR-011 (Logging/Sanitization)

Ten przewodnik opisuje uruchomienie SmartMyOdoo jako **przenośnego, lokalnego
artefaktu**: jeden `docker compose up` stawia FastAPI + UI na `:8000`, bez ręcznego
venv, zależności ML i modelu spaCy. Stan (vault, baza, logi) żyje na wolumenach;
**obraz nie zawiera żadnych sekretów**.

---

## 1. Prerekwizyty

- Docker Engine + **Docker Compose v2** (sprawdź: `docker compose version`).
- Klucz **OpenRouter** (`OPENROUTER_KEY`) — wymagany do czatu/LLM. Bez niego
  `/api/chat` zwraca 500 (fail-closed); reszta API działa.
- ~2–3 GB miejsca (obraz ~1.5 GB: zależności ML + model PL spaCy).

---

## 2. Konfiguracja sekretów (`.env`)

```bash
cp .env.example .env
```

Otwórz `.env` i ustaw co najmniej:

```dotenv
OPENROUTER_KEY=sk-or-...
```

> 🔒 **`.env` jest gitignored oraz wykluczony z obrazu** (`.dockerignore`). Sekrety
> nigdy nie wchodzą do warstw obrazu — compose czyta je z `.env` w czasie uruchomienia.

### Zmienne środowiskowe (serwis `app` w `docker-compose.yml`)

| Zmienna | Wymagane | Domyślne (compose) | Opis |
|---|:---:|---|---|
| `OPENROUTER_KEY` | ✅ | — (z `.env`) | Klucz LLM. Bez niego `/api/chat`=500. |
| `REDIS_URL` | — | `redis://redis:6379/0` | Współdzielony rate-limit/cache/lock. **Nazwa serwisu `redis`, NIE `localhost`** (sieć dockera). |
| `DATABASE_URL` | — | `sqlite:////data/smartmyodoo.db` | Baza na wolumenie `/data` (4 ukośniki = ścieżka absolutna). |
| `VAULT_DIR` | — | `/data/vault` | Katalog stanu vaultu na wolumenie. |
| `CORS_ALLOWED_ORIGINS` | — | `http://127.0.0.1:8000,http://localhost:8000` | Lista originów CORS (CSV). |

---

## 3. Uruchomienie

```bash
docker compose up --build
```

Pierwszy build jest wolniejszy: kompiluje ciężkie zależności (`pip install --pre`
dla `markitdown[all]`/azure beta, pinowane przez `constraints.txt`) i pobiera model
PL spaCy (`pl_core_news_md`).
Kolejne uruchomienia korzystają z cache warstw.

Po starcie:

- UI: **http://127.0.0.1:8000**
- Health: `GET http://127.0.0.1:8000/api/status` → `200 {"initialized": <bool>}`

> Compose publikuje port tylko na `127.0.0.1:8000` (lokalnie). W kontenerze uvicorn
> słucha na `0.0.0.0:8000` — ekspozycję na zewnątrz kontroluje WYŁĄCZNIE mapowanie portów.

---

## 4. Pierwsze uruchomienie — utworzenie sejfu (FIRST-RUN)

Aplikacja startuje **bez vaultu** (`initialized: false`). Sejf tworzysz przez UI:

1. Otwórz `http://127.0.0.1:8000`.
2. Pojawi się ekran inicjalizacji.
3. Ustaw **hasło master** (odblokowuje pełny dostęp) oraz **PIN** (szybki dostęp).
4. Gotowe — sejf zapisany na wolumenie `app-data` (`/data/vault`).

> Vault **nie** jest tworzony przez zmienne środowiskowe. Bootstrap odbywa się
> wyłącznie przez ekran init w UI (endpoint `POST /api/init`).

---

## 5. Persystencja (przeżycie restartu)

Stan trzymany jest na nazwanym wolumenie `app-data` zamontowanym jako `/data`:

```
/data/vault/   → pin_salt.cfg, master_salt.cfg, *_key.enc, vault_data.enc
/data/smartmyodoo.db  (+ -wal / -shm)
/data/logs/
```

| Operacja | Skutek dla danych |
|---|---|
| `docker compose restart app` | ✅ vault + baza zachowane |
| `docker compose down` + `up` | ✅ zachowane (wolumen trwa) |
| `docker compose down -v` | ❌ **kasuje wolumeny — utrata vaultu i bazy** |

---

## 6. Smoke-test (weryfikacja)

Powtarzalny skrypt (build → up → poll `/api/status` 200 → `/api/secrets` 401 →
restart → 200):

```bash
./scripts/docker_smoke.sh
```

Ręcznie:

```bash
curl -i http://127.0.0.1:8000/api/status      # → 200
curl -i http://127.0.0.1:8000/api/secrets     # → 401 (brak tokenu autoryzacji)
```

---

## 7. Bezpieczeństwo (ADR-008)

- Obraz budowany **bez sekretów**: `.dockerignore` wyklucza `*.enc`, `*.cfg`,
  `*.db*`, `.env`, vault. Weryfikacja: `docker history <obraz>` / inspekcja warstw.
- Kontener działa jako **non-root** (`USER appuser`, uid 1001).
- Vault i baza wyłącznie na lokalnych wolumenach.
- ⚠️ **NIGDY nie pushuj zbudowanego obrazu z danymi ani wolumenu `app-data` do
  publicznego registry.** Konteneryzacja jest LOKALNA — nie otwiera trybu
  cloud/multi-tenant (to osobny, większy temat — nowy ADR).

---

## 8. Troubleshooting

| Objaw | Przyczyna / Naprawa |
|---|---|
| `/api/chat` → 500 | Brak `OPENROUTER_KEY` w `.env` lub niepobrany model spaCy (build). |
| `/api/status` długo nie 200 | Pierwszy start ładuje spaCy/presidio — `start_period=40s` w healthcheck. |
| Rate-limit/cache nie działa między procesami | `REDIS_URL` musi wskazywać `redis://redis:6379/0` (nazwa serwisu). |
| Vault znika po `down -v` | `-v` kasuje wolumeny. Używaj `down` bez `-v`, by zachować dane. |
| Build wolny/kruchy na nowszym Pythonie | Trzymaj `python:3.12-slim` (D1) — pewne wheels ML. |
