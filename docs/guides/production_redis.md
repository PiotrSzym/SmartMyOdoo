# 🚀 Produkcja: Redis i wiele workerów (`REDIS_URL`)

> Dlaczego i jak włączyć współdzielony stan między procesami. Dotyczy: **rate-limit**, **cache LLM**,
> **distributed lock** (approve propozycji) i **kolejki zadań**.

## TL;DR
- **1 proces (dev)** — nic nie musisz robić; działa tryb proces-lokalny.
- **Wiele workerów / kontenerów (prod)** — **ustaw `REDIS_URL`**, inaczej:
  - rate-limit liczy się **per-worker** (realny limit × liczba workerów),
  - **distributed lock NIE chroni** approve między procesami (ryzyko podwójnego wykonania),
  - cache LLM nie jest współdzielony (niższy hit-rate).

## Jak to działa
Komponenty same wykrywają Redis (lazy ping, timeout 0.5s):
| Komponent | Plik | Z `REDIS_URL` | Bez (fallback) |
|---|---|---|---|
| Rate-limit | `core/ratelimit.py` | `INCR`+`EXPIRE` (wspólny licznik) | licznik w pamięci procesu |
| Distributed lock | `core/lock.py` | `SET NX PX` + token | `threading.Lock` (jeden proces) |
| Cache LLM | `core/llm_cache.py` + `chat_deps.get_llm_cache()` | `RedisLLMCache` | `InMemoryLLMCache` |
| Kolejka zadań | `core/queue.py` | Redis (wymagany) | — |

Awaria/brak Redisa = **degradacja**, nie crash (z ostrzeżeniem w logach).

## Włączenie
1. Uruchom Redis (jest w `docker-compose.yml`, port `127.0.0.1:6379`).
2. Ustaw zmienną środowiskową aplikacji:
   ```
   REDIS_URL=redis://localhost:6379/0
   ```
   (produkcyjnie z hasłem: `redis://:HASLO@host:6379/0` + odkomentuj `requirepass` w compose).
3. Zrestartuj aplikację. W logach na starcie zobaczysz tryb:
   - ✅ `[runtime] Redis AKTYWNY (...) — tryb ROZPROSZONY (bezpieczny dla wielu workerów).`
   - ⚠️ `[runtime] Brak REDIS_URL — ... tryb PROCES-LOKALNY ...`

## Konfiguracja powiązana (ENV)
| Zmienna | Domyślna | Opis |
|---|---|---|
| `REDIS_URL` | — (fallback) | adres Redisa dla rate-limit/cache/lock/queue |
| `CHAT_RATE_MAX` | `30` | maks. żądań czatu / okno |
| `CHAT_RATE_WINDOW_S` | `60` | długość okna rate-limitu (s) |
| `LLM_CACHE` | `on` | `off` wyłącza cache LLM |
| `MAX_BUDGET_USD` | `1.0` | budżet sesji (TokenGovernor; wpływa na degradację modelu) |

> Uwaga: kolejka/workery (`core/queue.py`) i tak wymagają Redisa na produkcji — lock/rate-limit/cache
> po prostu dołączają do tego samego Redisa po ustawieniu `REDIS_URL`.
