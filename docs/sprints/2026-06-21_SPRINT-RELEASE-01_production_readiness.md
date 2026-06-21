---
sprint_id: "RELEASE-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-21
closed: 2026-06-21
goal: "Podnieść gotowość produkcyjną 76→≥80 (SHIP dla celu LOKALNEGO) i domknąć ścieżkę dystrybucji: CI gatuje build+testy+smoke, FastAPI lifespan zamiast deprecated on_event, E2E bez flaky-timeoutów + mapa P0, test down-migration, wersjonowanie + LICENSE/SECURITY + instrukcja wydania. Higiena statusów sprintów."
prefix: "RELEASE"
complexity: 6
roadmap_ref: "Production Readiness Audit 2026-06-21 (76/100 CONDITIONAL); Faza 7; po DOCKER-01"
parent_sprint: null
tags: ["release", "ci", "ops", "production-readiness", "distribution", "local-only", "adr-008"]
---

# 🧱 Sprint: RELEASE-01 — Production Readiness → SHIP + dystrybucja

> **Architekt:** /arch | **Owner:** /dev | **Review:** /gf-review | **Data:** 2026-06-21
> **Bazuje na:** main (`40c8fd3`) | **Recon:** Production Readiness Audit (76/100) + graphify (2908 węzłów) | **ADR:** ADR-008 (Local-Only), ADR-009 (Gitignore), ADR-010 (Migrations), ADR-011 (Logging)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch ✅)

### 0A. Business Discovery
- **Dla kogo?** Operator/maintainer + odbiorcy lokalnej dystrybucji (clone/obraz). 
- **Problem (1 zdanie):** aplikacja jest na **76/100 (CONDITIONAL)** — działa i jest skonteneryzowana, ale brak CI (nic nie gatuje wydania), deprecated startup, flaky e2e, brak rollback-testu i metadanych wydania (LICENSE/SECURITY/wersja).
- **Metryka sukcesu:** ponowny Production Readiness Audit ≥ **80/100 (SHIP)** dla celu LOKALNEGO; CI zielone na push/PR; `docker compose up` z czystego clone'a działa; wydanie ma tag + LICENSE + instrukcję.
- **ROI:** zamienia „mamy kontener" w „inni mogą bezpiecznie wziąć i uruchomić"; CI łapie regresje zanim wyjdą.
- **Źródło:** Production Readiness Audit (2026-06-21) — sekcje 🔴/🟡.
- **Zakres:** cel **LOKALNY** (ADR-008). SaaS/multi-tenant = POZA zakresem (osobny ADR — hard-cap RLS).

### 0B. Fakty (z audytu + recon /arch, plik:linia)
| Fakt | Dowód | Zadanie |
|---|---|---|
| Brak CI | `.github/workflows/` nie istnieje | T1 |
| `@app.on_event("startup")` deprecated | `api.py:22` | T2 |
| 3× `wait_for_timeout` (flaky) | `test_audit_loads_on_reload_e2e.py:67`, `test_auth_ready_loading_e2e.py:59,96` | T3 |
| Brak testu down-migration | `tests/test_schema_migrations.py` (brak `downgrade`) | T4 |
| `version = "0.1.0"`, brak tagów git | `pyproject.toml:3`, `git tag` puste | T5 |
| Brak LICENSE/SECURITY.md | `ls` = brak | T6 |
| Statusy sprintów ≠ roadmapa | DOC-01/02, FIX-02-S3.x/S5.x, KEY-02 = IN_PROGRESS mimo „done" w roadmap | T7 |
| God Nodes (graphify) | SkillConfig 69, SkillExecutor 64, ExecutionPipeline 48 | dług — POZA zakresem (tylko nota) |
| Testy zielone | pytest 297 passed, 0 failed | baseline regresji |

### 0C. User Stories
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-REL-1 | maintainer | by CI automatycznie gatował build+testy+smoke | nie wypuścić zepsutego wydania | KIEDY push/PR na main TO CI: pytest + docker build + smoke = zielone, inaczej blok |
| US-REL-2 | operator | by serwer startował/zamykał się czysto (lifespan) | brak deprecation + graceful shutdown | KIEDY SIGTERM/stop kontenera TO FastAPI kończy czysto (lifespan, nie on_event) |
| US-REL-3 | QA | by E2E były deterministyczne (bez sleepów) | brak flaków na CI | KIEDY e2e w CI TO zero `wait_for_timeout`; mapa US→E2E P0 kompletna |
| US-REL-4 | operator | by rollback migracji był udowodniony | bezpieczny downgrade | KIEDY downgrade→upgrade TO schemat wraca do spójnego stanu (test) |
| US-REL-5 | odbiorca | by wydanie miało wersję, LICENSE i instrukcję | wiedzieć co dostał i na jakich zasadach | KIEDY tag `vX.Y.Z` TO LICENSE + SECURITY.md + sekcja „Wydanie" w README |
| US-REL-6 | zespół | by statusy sprintów odzwierciedlały rzeczywistość | roadmapa nie kłamała | KIEDY przegląd TO każdy sprint ma status zgodny ze stanem (DONE/otwarty) |

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| CI GitHub Actions | brak — NOWY (skill `github-actions-ci` jako referencja) | 🆕 |
| Healthcheck/smoke | `scripts/docker_smoke.sh` (DOCKER-01) | 📐 IN-PATTERN (użyj w CI) |
| FastAPI lifespan | `@asynccontextmanager` (FastAPI ≥0.93) | 📐 REFERENCE (zastąp on_event) |
| Migracje Alembic | ADR-010, `migrations/versions/` | 📐 IN-PATTERN (dołóż test downgrade) |
| E2E deterministyczne | `expect()`/`wait_for_function`/`page.expect_response` (UX-10) | 📐 IN-PATTERN (zastąp `wait_for_timeout`) |

### 0E. Test Strategy
| Warstwa | Potrzebna? | Co testować | Kto | Narzędzie |
|---|:--:|---|:--:|---|
| CI | ✅ | pytest(non-e2e)+lint+docker build+smoke = zielone na push | /dev+/qa | GitHub Actions |
| Unit/integ | ✅ | lifespan startup/shutdown; downgrade→upgrade round-trip | /dev | pytest |
| E2E | ✅ | te same scenariusze BEZ `wait_for_timeout`, deterministycznie | /qa | Playwright |
| Regresja | ✅ | pełna pytest 0 failed; e2e 11/11 | /qa | pytest |
| Smoke | ✅ | `docker compose up` z czystego clone'a → /api/status 200 | /qa | docker_smoke.sh |

### 0F. US → Test Mapping
| US | Scenariusz | Plik/Weryfikacja | Priorytet |
|----|------------|----------|-----------|
| US-REL-1 | push → CI zielone (pytest+build+smoke) | `.github/workflows/ci.yml` + run | 🔴 |
| US-REL-2 | lifespan startup/shutdown | unit + `/api/status` po starcie | 🔴 |
| US-REL-3 | e2e bez sleepów | `grep wait_for_timeout` = 0; e2e 11/11 | 🟡 |
| US-REL-4 | downgrade→upgrade | `tests/test_schema_migrations.py` (nowy case) | 🟡 |
| US-REL-5 | tag + LICENSE + SECURITY + README | review /doc | 🟡 |
| US-REL-6 | statusy spójne | przegląd plików sprintów | 🟢 |

### 0F-bis. Mapa US → E2E P0 (formalna, RELEASE-01 T3 /dev)

> Kompletna mapa scenariuszy P0 na testy E2E (11/11). Wszystkie testy są **deterministyczne**
> (zero `wait_for_timeout` — `page.expect_response` / `wait_for_function`; RELEASE-01 T3).

| US (źródłowa) | Scenariusz P0 | Plik E2E :: funkcja | Det. mechanizm |
|---|---|---|---|
| US-UX10-1 | po loginie vault sam renderuje (bez 401) | `test_auth_ready_loading_e2e.py::test_secrets_load_after_login_without_manual_click` | `expect_response(/api/secrets)` + `wait_for_function(flex)` |
| US-UX10-1 | po loginie audyt sam odpytuje (200) | `test_auth_ready_loading_e2e.py::test_audit_loads_after_login_on_activity_tab` | `expect_response(/api/audit)` |
| US-UX10-2 | reload na zakładce Aktywność → audyt ładuje po loginie | `test_audit_loads_on_reload_e2e.py::test_audit_loads_after_login_on_restored_activity_tab` | `expect_response(/api/audit)` + marker renderu |
| US-UX10-2 | reload na zakładce Skarbiec → vault ładuje po loginie | `test_vault_loads_on_reload_e2e.py::test_vault_renders_after_login_on_restored_settings_tab` | network spy + marker renderu |
| US-CHAT | layout czatu + interakcja | `test_chat_e2e.py::test_chat_layout_and_interaction` | expect/locator |
| US-UX08 | badge zadania w nagłówku (workspace związany) | `test_chat_task_badge_e2e.py::test_chat_header_shows_task_badge_for_bound_workspace` | expect/locator |
| US-UX08 | brak badge dla niezwiązanego workspace | `test_chat_task_badge_e2e.py::test_chat_header_shows_no_task_for_unbound_workspace` | expect/locator |
| US-UX08 | zmiana zadania z poziomu badge czatu | `test_chat_task_change_e2e.py::test_change_task_from_chat_badge` | expect/locator |
| US-PROJ | zakładka Projekt renderuje DOKŁADNIE jeden stan | `test_project_tab_e2e.py::test_project_tab_renders_exactly_one_state` | `wait_for_function` |
| US-UX08 | workspace przeżywa nawigację między zakładkami | `test_workspace_persistence_e2e.py::test_workspace_persists_across_tab_navigation` | expect/locator |
| US-UX08 | workspace przeżywa reload | `test_workspace_persistence_e2e.py::test_workspace_persists_across_reload` | expect/locator |

**Pokrycie P0:** 11/11 testów E2E zmapowanych na US. `grep -rn "\.wait_for_timeout(" tests/e2e` = **0**.

### 0G. Security Scope → Sekcja D
ADR-008/009 zachowane. CI NIE może mieć sekretów w logach/artefaktach (build bez `OPENROUTER_KEY`; smoke testuje ścieżki nie-LLM). SECURITY.md = polityka zgłaszania luk. LICENSE = decyzja prawna (open decision D3). Brak nowych powierzchni ataku.

### ⚖️ Zasady / Decyzje architektoniczne (/arch)
- **D1 — Dystrybucja: clone + `docker compose up` jako PRIMARY** (najprostsze, ADR-008-safe). Publikacja obrazu na ghcr = OPCJONALNE/później (obraz bez sekretów, więc dozwolone, ale wymaga decyzji o publiczności repo).
- **D2 — CI = GitHub Actions** (repo na GitHub). Joby: `lint+test` (ruff/mypy jeśli dostępne + pytest non-e2e), `docker` (build + `scripts/docker_smoke.sh`). **E2E w CI = osobny job opcjonalny** (chromium ciężki — na początek nie blokujący; pytest non-e2e jest hard-gate). Hosted runner ma docker.
- **D3 — LICENSE = OTWARTA DECYZJA USERA** (prawna). Nie wybieram licencji. Opcje: brak/proprietary (zachowuje ADR-008-DNA „nie do publicznego dzielenia"), MIT/Apache-2.0 (open). **Blokuje T6 do czasu decyzji.**
- **D4 — Wersjonowanie: semver z `pyproject.toml`** (`0.1.0`); tag `v0.1.0` po merge RELEASE-01. Dodać `/api/version` (czyta wersję pakietu) — drobne, opcjonalne.
- **D5 — God Nodes (graphify) = POZA zakresem** (dług architektoniczny; tylko nota — nie dokładać zależności do Executora/Pipeline).

---

## 🧱 Sekcja B — Podział Zadań (TDD-friendly) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| T1 | **CI GitHub Actions** 🔴: `lint+test` (pytest `-m 'not e2e'`) + `docker` (build + `scripts/docker_smoke.sh`). Triggery: push/PR na main. Concurrency group, cache pip. Bez sekretów. | NEW `.github/workflows/ci.yml` | skill `github-actions-ci`, `docker_smoke.sh` | CI zielone na push; czerwone gdy test fail | ✅ (yaml waliduje; realny run po pushu) |
| T2 | **FastAPI lifespan** 🔴: zastąp `@app.on_event("startup")` (api.py:22) `@asynccontextmanager` lifespan + graceful shutdown (startup: log backend modes/alembic; shutdown: czyste zamknięcie). | `smartmyodoo/api.py` | FastAPI lifespan | Unit: app startuje przez lifespan; `/api/status`=200; brak DeprecationWarning | ✅ (2 testy pass) |
| T3 | **E2E hardening** 🟡: zastąp 3× `wait_for_timeout` deterministycznym `page.expect_response("/api/...")`/`wait_for_function`. Dodaj `docs/sprints/.../US-E2E-mapping` lub sekcję — formalna mapa 100% P0. | `tests/e2e/test_audit_loads_on_reload_e2e.py`, `test_auth_ready_loading_e2e.py` | UX-10 (expect_response) | `grep wait_for_timeout tests/e2e` = 0; e2e 11/11 | ✅ (grep=0, mapa P0; live 11/11 → /qa) |
| T4 | **Test down-migration** 🟡: `tests/test_schema_migrations.py` — case `downgrade` (np. `base`) → `upgrade head` round-trip, schemat spójny. | `tests/test_schema_migrations.py` | ADR-010 | nowy test przechodzi; pełna pytest 0 failed | ✅ (round-trip pass) |
| T5 | **Wersjonowanie**: potwierdź `version` SSoT (`pyproject.toml`); dodaj `GET /api/version` (czyta wersję pakietu); README „Wydanie" (jak tagować, semver). | `pyproject.toml`, `smartmyodoo/api_routers/*`, `README.md` | D4 | Unit: `/api/version` zwraca wersję | ✅ (3 testy pass; README „Wydanie") |
| T6 | **LICENSE + SECURITY.md** 🟡 — **ODROCZONE (decyzja usera 2026-06-21: licencja później).** Do zrobienia w osobnym follow-upie gdy user wybierze licencję. SECURITY.md może powstać niezależnie, ale wiążemy z T6 dla spójności wydania. | NEW `LICENSE`, `SECURITY.md` | — | — | ⏸️ DEFERRED |
| T7 | **Higiena statusów sprintów** 🟢: przejrzyj `docs/sprints/*` — ustaw realny `status` (DONE dla zakończonych wg roadmapy: FIX-02-S3.x/S5.x, KEY-01/02, DOC-01/02 — zweryfikuj kodem/gitem przed zmianą). NIE zmieniaj treści, tylko frontmatter zgodnie ze stanem. | `docs/sprints/*.md` | — | przegląd; spójność z roadmap | ✅ (11 sprintów zweryf. kodem+git → DONE) |

> **TDD/kolejność /dev:** T2 (lifespan, z testem) → T4 (downgrade) → T3 (e2e) → T1 (CI — gatuje resztę) → T5 → T7. T6 czeka na decyzję D3 (licencja). Po każdej zmianie kodu: pełna pytest 0 failed.

---

## 🛡️ Sekcja D — Security (/sec ✅)
- [x] CI nie loguje/nie zapisuje sekretów; build bez `OPENROUTER_KEY` (atrapa `ci-dummy-not-used`); zero `${{ secrets.* }}`, brak upload-artifact z sekretami.
- [x] `/api/version` nie eksponuje wrażliwych danych (tylko numer wersji; publiczny jak /api/status).
- [ ] SECURITY.md ma kanał zgłaszania luk + scope. — ⏸️ **DEFERRED (część T6, decyzja usera)**
- [ ] LICENSE zgodny z intencją ADR-008. — ⏸️ **DEFERRED (część T6, decyzja usera)**
- [x] Brak nowych endpointów wystawiających dane; lifespan nie zmienia modelu auth.

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review ✅)
- [x] US-REL-1: CI yaml waliduje, joby (lint-test hard-gate + docker + e2e non-blocking) bez sekretów. Realny run zielony — po pushu.
- [x] US-REL-2: lifespan działa; `/api/status`=200; zero DeprecationWarning z on_event.
- [x] US-REL-3: `grep wait_for_timeout tests/e2e` = 0; **e2e 11/11 LIVE**; mapa P0 (0F-bis).
- [x] US-REL-4: downgrade→upgrade round-trip przechodzi (realne `op.drop_*`, zweryf. /gf-review).
- [x] US-REL-5: `/api/version`={"version":"0.1.0"}; README „Wydanie"; tag `v0.1.0` przy merge.
- [x] US-REL-6: 11 sprintów status→DONE (zweryfikowane kod+git).
- [x] Regresja: pełna pytest **303 passed, 0 failed**; e2e 11/11.
- [x] **Ponowny Production Readiness Audit = 85/100 (SHIP, cel lokalny)** vs baseline 76.
- [x] T6 (LICENSE/SECURITY) — świadomie ODROCZONE (decyzja usera 2026-06-21).

### Close Checklist
- [x] Zadania Sekcji B = ✅ (T6 świadomie odroczone), status → `DONE`, `closed`.
- [x] Lessons Learned (Sekcja F) + instynkty (instincts.md INS-005 cold-start).
- [x] Zmergowane do `main`; tag `v0.1.0`; wpis w roadmap (Faza 7).

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa — CI, lifespan, deterministyczne e2e, rollback migracji, wydanie)

### /dev (RELEASE-01, 2026-06-21)
- **T2 lifespan — ukryta regresja kontraktu testowego.** Usunięcie `@app.on_event('startup')`
  zepsuło `tests/test_runtime_info.py::test_startup_hook_registered`, który asertował
  `hasattr(api, '_log_backend_modes')` (nazwę usuwanej funkcji). **Instynkt:** przy migracji
  deprecated API grepuj testy po NAZWIE usuwanego symbolu, nie tylko po zachowaniu —
  test może pinować implementację, nie kontrakt. Naprawa: przepisany na kontrakt lifespanu
  (lifespan ustawiony + on_startup puste + `log_backend_modes` wołane przez TestClient context).
- **CRLF w plikach sprintów (T7).** `docs/sprints/*.md` mają zakończenia CRLF — `sed`
  z `$` nie matchował (zostawał `\r`). **Instynkt:** na tym repo używaj `sed -E 's/...\r?$/...\r/'`
  i weryfikuj `file` po edycji, by nie zmienić zakończeń linii.
- **CI bez sekretów (T1).** `docker_smoke.sh` wymaga `.env` z `OPENROUTER_KEY`, ale build
  i testowane ścieżki (status 200 / secrets 401) są nie-LLM → w CI wstrzykujemy ATRAPĘ
  klucza (nie sekret), zgodnie z D2/Sekcją D. Hard-gate = pytest non-e2e + docker; e2e
  `continue-on-error` (chromium ciężki).
- **Deterministyczne e2e (T3).** `page.expect_response(lambda r: "/api/..." in r.url)` jako
  context manager wokół akcji domyka okno wyścigu bez magicznego sleepa — vault render
  ZAWSZE woła `/api/secrets` (project.js:82), więc anchor jest niezawodny.

---

### Handoff
```
/arch (ten artefakt) ✅
   → DECYZJA USERA: D3 (licencja) — odblokuje T6
   → /dev (T2 lifespan → T4 downgrade → T3 e2e → T1 CI → T5 wersja → T7 statusy)
   → /sec (CI bez sekretów, SECURITY.md, LICENSE zgodny z ADR-008)
   → /qa (CI zielone, lifespan, e2e bez sleepów 11/11, downgrade, ponowny audyt ≥80)
   → /gf-review (gate) → merge → tag v0.1.0 → /doc (README Wydanie + roadmap)
```

> Po RELEASE-01: gotowość ≥80 (SHIP lokalny), CI gatuje regresje, wydanie ma wersję+LICENSE+instrukcję.
> SaaS/multi-tenant nadal POZA (ADR-008 — wymaga osobnego ADR + redesignu izolacji).
