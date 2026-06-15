# 🐳 Odoo: Docker, Edycje i Hosting — kompendium

> Przewodnik stawiania i obsługi środowiska Odoo dla SmartMyOdoo: Docker, bazy danych,
> matryca wersji 16/18/19, edycja Community vs Enterprise, typy hostingu i pułapki.
> Źródła: `docker-compose.yml`, `.env.example`, `smartmyodoo/swarm/recon.py` (auto-detekcja).

## 🥇 Złota zasada — Empty Shell Policy
NIE rozbudowuj chaotycznych `docker-compose`. Bazuj na czystym szablonie; custom kod montuj
jako wolumen do `/mnt/extra-addons`, nie wgrywaj go do obrazu.

## Realna konfiguracja projektu (`docker-compose.yml`, po hardeningu S1.4)
| Serwis | Obraz | Port | Uwagi |
|---|---|---|---|
| `odoo` | `odoo:16` | 8069 | `HOST=db`, `USER/PASSWORD` z ENV, `./custom_addons → /mnt/extra-addons` |
| `db` | `postgres:16-alpine` | (wewn.) | `POSTGRES_*` z ENV (`${POSTGRES_PASSWORD:-...}`), wolumen `odoo-db-data` |
| `redis` | `redis:7-alpine` | **127.0.0.1**:6379 | kolejka zadań (F7-03); bind tylko do localhost, wolumen `redis-data` |

Sekrety: zobacz `.env.example` (skopiuj do `.env`, które jest gitignored). Zero haseł
wprost w `docker-compose.yml`. Produkcyjnie ustaw `REDIS_PASSWORD` i odkomentuj `--requirepass`.

## Matryca wersji Odoo
| Wersja | Port HTTP | Specyfika składni/API |
|---|---|---|
| Odoo 16 | 8069 | ostatnia z `attrs` w XML i magic tuples `(0,0,{})` |
| Odoo 17/18 | 5434 (18) | **zakaz `attrs`** (inline `invisible="..."`), `odoo.Command`, `<list>` zamiast `<tree>`, `_read_group()` |
| Odoo 19 | (Clean Core) | praca wyłącznie w `/mnt/extra-addons`; integracje przez **JSON-2 (`/json2`)** + Bearer; `osv`/`record._cr`/`_context` zdeprecjonowane |

⚠️ Kod z Odoo 16 (`attrs`, krotki) **wybucha** na 17/18/19 — ustal wersję ZANIM piszesz.

## Edycja: Community vs Enterprise (KRYTYCZNE)
Auto-detekcja w runtime: `recon.py::detect_edition()`.

- **Jak wykryć:** licencja modułu `base_setup` —
  `search_read('ir.module.module', [('name','=','base_setup')], ['license'])` →
  `OEEL-1` = **Enterprise**, w przeciwnym razie **Community** (fallback: Community).
- **🔴 Reguła:** klientowi **Community** NIGDY nie proponuj funkcji/modułów **Enterprise**
  (pełna księgowość, Studio, podpisy, MRP/PLM enterprise…) — proponuj odpowiedniki Community lub OCA.
- **Docker:** obraz publiczny `odoo:N` = **Community**. Enterprise wymaga prywatnego repo
  `enterprise/` zamontowanego do `addons_path` + ważnej subskrypcji (kodu Enterprise nie ma w publicznym obrazie).

## Hosting: SaaS vs Odoo.sh vs On-Premise (co wolno)
Auto-detekcja: `recon.py::classify_hosting(url)` — po URL instancji.

| Hosting | URL | Co wolno |
|---|---|---|
| **SaaS** | `*.odoo.com` | ❌ brak Pythona/custom kodu — **tylko Studio** i konfiguracja |
| **Odoo.sh** | `*.odoo.sh` | ✅ Python + custom moduły (Git, staging) |
| **On-Premise** | własny host | ✅ pełna kontrola (Docker, custom kod, master password) |

→ Przed pisaniem kodu ustal hosting: na **SaaS** rozwiązaniem jest konfiguracja, nie kod.

## Stawianie bazy danych
- Nowa baza: `-d <nazwa> -i base` (inicjalizacja). Aktualizacja modułu: `-u <modul> -d <baza>`.
- **Master/DB password:** wstrzykuj z sekretów (`ODOO_MASTER_PASSWORD`/Vault) — nigdy plaintext.
  Sandbox agenta jest **fail-closed**: bez `ODOO_MASTER_PASSWORD` operacje na bazie są blokowane.
- Demo data: na produkcji `--without-demo=all`.

## Dockerized TDD (izolacja)
- Testy na **wyizolowanym porcie** `--http-port=8070` (brak kolizji z 8069).
- Parsowanie `__manifest__.py` **czystym regex** — ZAKAZ `eval()`.

## ⚠️ Pułapki (najczęstsze)
1. **Utrata danych** — brak wolumenu na `/var/lib/postgresql/data` (DB) i filestore Odoo
   (`/var/lib/odoo`). `docker compose down -v` kasuje dane; backupuj DB i filestore razem (muszą być spójne).
2. **addons_path** — moduł niewidoczny: nie zamontowany w `/mnt/extra-addons`, brak `__manifest__.py`
   lub zły `depends`. Po dodaniu: restart + `-u` (lub instalacja z UI).
3. **Konflikt portów** — kilka wersji naraz (16=8069, 18, 19, testy=8070) → różne porty hosta.
4. **DB Manager** — odsłonięty `/web/database/manager` na produkcji = krytyczna luka.
   Ustaw `admin_passwd`, `list_db = False`.
5. **`database not initialized`** — pierwszy start wymaga `-i base -d <baza>`.
6. **Migracja 18→19** — łamanie kompatybilności API; testuj na staging, nigdy wprost na prod.
7. **Healthcheck/timing** — Odoo startuje przed gotowością Postgresa; `depends_on` nie czeka na health —
   dodaj retry/healthcheck na `db`.

## 🛡️ Bezpieczeństwo
- Sekrety przez `.env`/Vault, zero w `docker-compose.yml` (S1.4).
- Redis tylko na `127.0.0.1` (+ `requirepass` na produkcji).
- Izolacja staging vs produkcja.

---
*Ten przewodnik jest repo-widoczną wersją wewnętrznego skilla agenta `odoo-docker-environment`.*
