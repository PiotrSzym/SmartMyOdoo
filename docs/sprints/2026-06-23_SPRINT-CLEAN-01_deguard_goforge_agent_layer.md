---
sprint_id: "CLEAN-01"
workspace: "SmartMyOdoo"
status: "🟡 In Progress"
created: 2026-06-23
closed: null
goal: "Odgoforge'owić warstwę agentów/skili: wynieść 27 skili-widm (15 Go + 12 React/Next) z .claude/skills/ do kwarantanny (poza discovery), zaadaptować gf-review.md (fazy F5A Go / F5B React → N/A; F9 go build → pytest/ruff/bandit/docker) i production-readiness (hard-capy RLS/tenant + go build → local-first/Python), dorobić brakujące pliki scaffoldingu (00_lessons_learned.md, docs/adr/INDEX.md) blokujące KROK 0 agentów. Guard: żaden zachowany agent nie traci referencji do wyniesionego skila. Cel LOKALNY (ADR-008)."
prefix: "CLEAN"
complexity: 5
roadmap_ref: "Audyt warstwy agentów 2026-06-23 (75 skili+7 agentów: 27 N/A GoForge=36%, 4 do adaptacji, 44 fit)"
parent_sprint: null
tags: ["cleanup", "agents", "skills", "goforge-debt", "tooling", "dx", "local-only", "adr-008"]
---

# 🧱 Sprint: CLEAN-01 — Odgoforge'owienie warstwy agentów/skili

> **Architekt:** /arch | **Owner:** /dev | **Review:** /gf-review | **Data:** 2026-06-23
> **Bazuje na:** main (`90d7e5e`) | **Recon:** Audyt warstwy agentów 2026-06-23 (klasyfikacja 75 skili + 7 agentów) | **ADR:** ADR-006 (Vanilla-JS Frontend), ADR-008 (Local-Only)

---

## 📋 Sekcja A — Business Discovery & Rules (/arch)

### 0A. Business Discovery
- **Dla kogo?** Maintainer + każdy agent/LLM korzystający z pickera skili w tym repo.
- **Problem (1 zdanie):** warstwa narzędzi (TeamEngine) została **skopiowana 1:1 z projektu GoForge (Go + React/Next)** z zasadą „źródło nietknięte" — przez co **36% skili (27/75) to martwy balast** (język Go, frontend React), który zaśmieca picker, grozi mis-routingiem (np. `go-ddd` do zadania Odoo) i wkłada fazy Go/React do review.
- **Metryka sukcesu:** picker skili widzi **0 skili Go/React** (27 wyniesionych); `gf-review` i `production-readiness` nie wołają `go build`/`golangci-lint` ani faz React; każdy zachowany agent ma komplet referencji (guard zielony); KROK 0 `gf-review` nie wywala się na braku pliku.
- **ROI:** czysty picker = trafniejszy routing i tańsze sesje; review przestaje być teatrem (fazy-widmo) i realnie gatuje Pythona.
- **Źródło:** Audyt warstwy agentów (2026-06-23) — dowody pochodzenia: „Źródło .agents/ nietknięte — Antigravity", „GoForge alias dla skilla code-review".
- **Zakres:** warstwa `.claude/` (wrappery + skile). Źródło `.agents/` (50 plików, SSoT współdzielony) = **NIE przepisujemy** (D2) — tylko nadpisujemy w wrapperach. Cel LOKALNY (ADR-008).

### 0B. Fakty (z audytu + recon /arch)
| Fakt | Dowód | Zadanie |
|---|---|---|
| 75 skili w `.claude/skills/`, 7 agentów | `ls .claude/skills/`, `.claude/agents/` | baseline |
| 15 skili Go = N/A | `go-*` (10), `golangci-lint`, `buf-protobuf`, `makefile-patterns`, `multitenancy`, `plugin-architecture` | T1 |
| 12 skili React/Next = N/A (vanilla JS, ADR-006) | `atomic-design`, `goforge-ui-atomic`, `nextjs-best-practices`, `react-patterns`, `dnd-kit-patterns`, `tailwind-v4`, `vitest-testing`, `testing-library`, `vercel-composition`, `vercel-react-perf`, `zustand-state`, `zod-validation` | T1 |
| `gf-review.md` ma fazy F5A Go / F5B React + F9 `go build`/`go test -race`/`golangci-lint` | `.claude/agents/gf-review.md:72` | T2 |
| `production-readiness` ma hard-cap RLS/tenant + „`go build` fails" | `.claude/skills/production-readiness/SKILL.md` (Hard Caps) | T3 |
| KROK 0 `gf-review` wymaga `docs/blueprint/00_lessons_learned.md` — BRAK | `gf-review.md:37` + `ls` = brak | T4 |
| F4 zakłada `docs/adr/INDEX.md` — BRAK (ADR-y płaskie) | `gf-review.md:46` + `ls docs/adr/` | T4 |
| Zero kodu Go / brak `package.json` (nie React) | `find . -name '*.go'` = 0 prod; brak `package.json` | uzasadnienie T1 |
| `.agents/` = 50 plików skażonych Go/React (SSoT, nietykane) | `grep -rilE 'goforge|golangci|react' .agents/` = 50 | D2 (poza zakresem) |
| Testy zielone (baseline) | pytest 323 passed / 0 failed (po WIRE-01) | baseline regresji |

### 0C. User Stories
| ID | JAKO | CHCĘ | ŻEBY | KIEDY → TO |
|----|------|------|------|------------|
| US-CLEAN-1 | agent/LLM w repo | by picker skili pokazywał tylko skile istotne dla stacku | nie mis-routować do Go/React | KIEDY agent szuka skila TO nie widzi żadnego z 27 Go/React |
| US-CLEAN-2 | maintainer | by `gf-review` recenzował Pythona, nie Go | review realnie gatował, nie udawał | KIEDY `gf-review` dojdzie do F5/F9 TO fazy Go/React=N/A, build=`pytest`/`ruff`/`bandit`/docker |
| US-CLEAN-3 | maintainer | by agenty nie wywalały się na braku plików GoForge | bramki działały od pierwszego uruchomienia | KIEDY agent wykonuje KROK 0 TO wszystkie wymagane pliki istnieją |
| US-CLEAN-4 | maintainer | by wyniesienie skila nie zepsuło żadnego agenta | brak osieroconych referencji | KIEDY skill wyniesiony TO żaden zachowany agent/workflow go nie woła (lub woła z jawnym N/A) |

### 0D. Pattern Registry
| Element | Wzorzec | Status |
|---|---|---|
| Wrapper override | sekcja „KOREKTY ŚCIEŻEK I NAZW" w `gf-review.md` | 📐 IN-PATTERN (rozszerz override, NIE ruszaj `.agents/`) |
| Kwarantanna artefaktów | brak — NOWY (`.claude/_graveyard/`) | 🆕 (reversible move, nie delete) |
| Adaptacja skilla pod stack | `production-readiness` adaptowany live 2026-06-23 (audyt 85→84) | 📐 REFERENCE (utrwal w pliku) |
| Lessons/Error registry | `docs/blueprint/tom1-wiedza/error_registry.md` istnieje | 📐 IN-PATTERN (dorób brakujący `00_lessons_learned.md` obok) |

### 0E. Test Strategy
| Warstwa | Potrzebna? | Co testować | Kto | Narzędzie |
|---|:--:|---|:--:|---|
| Guard (refs) | ✅ | dla każdego wyniesionego skila: zero referencji w zachowanych `.claude/agents/*.md` i workflowach (poza jawnym N/A) | /dev | grep |
| Discovery | ✅ | po wyniesieniu picker/`ls .claude/skills/` = 48, brak 27 Go/React | /dev | ls + count |
| Scaffolding | ✅ | KROK 0 `gf-review`: 4 wymagane pliki istnieją | /dev | test_exists |
| Regresja | ✅ | pełna pytest 0 failed (balast nie dotyka kodu app) | /qa | pytest |
| Smoke | ✅ | agent `odoo`/`qa`/`dev` startuje, picker bez Go/React | /qa | manual smoke |

### 0F. US → Test Mapping
| US | Scenariusz | Plik/Weryfikacja | Priorytet |
|----|------------|----------|-----------|
| US-CLEAN-1 | 27 skili poza discovery | `ls .claude/skills/` = 48; `.claude/_graveyard/skills/` = 27 | 🔴 |
| US-CLEAN-2 | review bez Go/React | diff `gf-review.md` F5/F9; `production-readiness` bez `go build` | 🔴 |
| US-CLEAN-3 | KROK 0 nie wywala | 4 pliki istnieją (`00_lessons_learned.md`, `INDEX.md`, +2) | 🟡 |
| US-CLEAN-4 | brak osieroconych refs | grep refs = 0 (lub N/A) | 🔴 |

### 0G. Security Scope → Sekcja D
Zmiany dotyczą WYŁĄCZNIE warstwy narzędzi/dokumentacji (`.claude/`, `docs/`) — **zero zmian w kodzie aplikacji** (`smartmyodoo/`). Brak nowej powierzchni ataku. Ryzyko: przypadkowe wyniesienie skila używanego przez kod runtime (nie powinno — to skile Claude Code, nie importy Pythona; T-guard to potwierdza grep-em w `smartmyodoo/`).

### ⚖️ Zasady / Decyzje architektoniczne (/arch)
- **D1 — Kwarantanna, NIE delete.** 27 skili → `.claude/_graveyard/skills/` (poza ścieżką discovery `.claude/skills/*/`, ale w repo — reversible). `git mv` zachowuje historię. Powód: gdyby projekt kiedyś dorobił komponent Go/React, wracają jednym `mv`.
- **D2 — `.agents/` NIETKNIĘTE (50 plików SSoT).** NIE przepisujemy źródła (zasada wrappera). Korekty Go→Python robimy w **wrapperze** `.claude/agents/gf-review.md` (sekcja override już istnieje — rozszerzamy ją). To samo dla `audyt` jeśli trzeba.
- **D3 — Scaffolding zamiast wyłączania bramki.** Brakujące pliki KROK 0 (`docs/blueprint/00_lessons_learned.md`) TWORZYMY (stub z linkiem do error_registry + lessons z dotychczasowych sprintów), `docs/adr/INDEX.md` generujemy z istniejących `ADR-001..010`. Lepsze niż „każ agentowi pomijać".
- **D4 — Lista dozwolonych jako artefakt.** Zapisz `PROJECT_SKILLS.md` (lub aktualizuj istniejący) z jawną listą 48 dozwolonych — żeby przyszłe sesje/agenci mieli źródło prawdy „co jest nasze".
- **D5 — `production-readiness`: adaptuj w miejscu.** To plik, który posiadamy (`.claude/skills/`). Hard-cap „RLS/tenant" → oznacz N/A dla single-tenant-local (ADR-008); „`go build` fails" → „testy/import-fail"; lenses Go → pytest/ruff/bandit/docker. (Wzór: adaptacja live z 2026-06-23.)

---

## 🧱 Sekcja B — Podział Zadań (TDD-friendly) (/dev)

| # | Zadanie | Pliki | Wzorzec ref. | Wymagane testy | Status |
|---|---------|-------|--------------|----------------|--------|
| T0-guard | **Guard referencji (RED first)** 🔴: przed wyniesieniem — grep 27 nazw skili w `.claude/agents/*.md`, `.agents/workflows/*.md` ORAZ `smartmyodoo/` (runtime). Wypisz każdą referencję. Te w fazach F5A/F5B `gf-review` są OK (znikną z T2); jakakolwiek inna referencja z zachowanego agenta = ZATRZYMAJ i zgłoś /arch. | grep-only | D1 | lista referencji; zero „twardych" poza F5/N/A | ✅ done (GREEN — `smartmyodoo/`=0; `.claude/agents/`=tylko soft inventory/F5; `.agents/`=SSoT D2) |
| T1 | **Wyniesienie 27 skili Go/React** 🔴: `git mv` 15 Go + 12 React/Next z `.claude/skills/<name>/` do `.claude/_graveyard/skills/<name>/`. Dopisz `.claude/_graveyard/README.md` (dlaczego, jak przywrócić). | `.claude/skills/*` → `.claude/_graveyard/skills/*` | D1 | `ls .claude/skills/`=48; `_graveyard/skills/`=27 | ✅ done (⚠️ DEWIACJA: `mv` symlinka, NIE `git mv` — `.claude/` gitignored; treść w `.agents/` nietknięta=D2) |
| T2 | **Adaptacja `gf-review.md`** 🔴: w sekcji override — F5A (Go)→`N/A: brak kodu Go`; F5B (React)→`N/A: vanilla JS, ADR-006`; F9 build → `pytest -m 'not e2e'` + `ruff check` + `bandit -ll` + `bash scripts/docker_smoke.sh` (zamiast `go build`/`go test -race`/`golangci-lint`); F4 → ADR-y płaskie `docs/adr/ADR-NNN`, INDEX.md (z T4). | `.claude/agents/gf-review.md` | D2 | diff pokazuje F5/F9/F4 zaadaptowane; zero `go build` w ścieżce wykonania | ✅ done |
| T3 | **Adaptacja `production-readiness`** 🟡: hard-cap „Brak RLS/tenant→max 50" → oznacz `N/A (single-tenant local, ADR-008)`; „`go build` fails→0" → „testy/import fail"; evidence-grep Go (`grep 'ENABLE ROW LEVEL'`, `go build`) → Python (`pytest`, `ruff`, `bandit`, `/api/status`). | `.claude/skills/production-readiness/SKILL.md` | D5 | diff; brak `go build`/RLS jako twardego capa | ✅ done (⚠️ DEWIACJA: plik to symlink do `.agents/`=D2; zrobiono LOKALNY override — zerwany symlink + lokalna kopia adaptowana, `.agents/` nietknięte) |
| T4 | **Scaffolding KROK 0** 🟡: utwórz `docs/blueprint/00_lessons_learned.md` (stub: link do `tom1-wiedza/error_registry.md` + agregat Lessons z RELEASE-01/WIRE-01); wygeneruj `docs/adr/INDEX.md` z `ADR-001..010`. | NEW `docs/blueprint/00_lessons_learned.md`, `docs/adr/INDEX.md` | D3 | oba pliki istnieją; KROK 0 gf-review przechodzi | ✅ done (INDEX z ADR-001..**015** — w repo jest 15, nie 10) |
| T5 | **Lista dozwolonych** 🟢: zaktualizuj `PROJECT_SKILLS.md` — jawna lista 48 skili „nasze" + nota o `_graveyard` (27 Go/React). | `PROJECT_SKILLS.md` | D4 | lista = 48; wzmianka o kwarantannie | ✅ done (root `PROJECT_SKILLS.md` tracked) |
| T6 | **Audyt agenta `audyt`** 🟢: sprawdź czy `audyt.md` woła lens Go-centryczny (gf-auditor) jako prescriptive; jeśli tak — dopisz korektę „referencje Python/Odoo". | `.claude/agents/audyt.md` | D2 | korekta lub potwierdzenie braku problemu | ✅ done (gf-auditor jest language-agnostic 6D — NIE Go-prescriptive; dopisano korektę + nota o wyniesionych skilach) |

> **TDD/kolejność /dev:** T0-guard (RED — udowodnij że refy są tylko w F5) → T4 (scaffolding, odblokowuje gf-review) → T1 (wyniesienie) → T2+T3 (adaptacja review/readiness) → T5/T6. Po T1: potwierdź `ls .claude/skills/`=48. Pełna pytest 0 failed na końcu (sanity — balast nie dotyka kodu).

---

## 🛡️ Sekcja D — Security (/sec) — PRE-ZWALIDOWANE przez /dev (czeka na pieczęć /sec)
- [x] Zero zmian w `smartmyodoo/` (kod aplikacji nietknięty) — `git diff --stat smartmyodoo/` = tylko 3 wiszące pliki WIRE-01 (dispatcher.py, tools.py, vault_auth.py), żadnego nowego z CLEAN-01.
- [x] Reversible move (nie delete) — historia zachowana. ⚠️ NIE `git mv` (`.claude/` gitignored) lecz `mv` symlinka; treść skili żyje w `.agents/skills/` (tracked-source, nietknięte). Przywracalne `mv` z powrotem (patrz `.claude/_graveyard/README.md`).
- [x] Żaden wyniesiony skill nie był importowany przez runtime Pythona — T0-guard grep `smartmyodoo/` = **0 trafień** dla wszystkich 27 nazw.
- [x] Brak nowej powierzchni ataku — zmiany tylko `.claude/` (gitignored), `docs/` (gitignored, ADR-009), `PROJECT_SKILLS.md`. Zero nowych endpointów/inputów.

## 🔬 Sekcja C — Definition of Done (/qa + /gf-review) — DO WERYFIKACJI (/dev zaznacza zweryfikowane)
- [x] US-CLEAN-1: `ls .claude/skills/` = **48**, `_graveyard/skills/` = **27** (15 Go + 12 React) — potwierdzone `wc -l`.
- [x] US-CLEAN-2: `gf-review.md` — F5A=`N/A: brak kodu Go`, F5B=`N/A: vanilla JS (ADR-006)`, F9=pytest/ruff/bandit/docker (grep: zero `go build`/`golangci-lint` w ścieżce wykonania, tylko w negacji); `production-readiness` (local override) bez `go build`/RLS-cap (Tenant lens=N/A ADR-008).
- [x] US-CLEAN-3: KROK 0 `gf-review` — 4 wymagane pliki istnieją: `review.md` (SSoT), `00_lessons_learned.md` ✅ utworzony, `error_registry.md` ✅ istniał, `INDEX.md` ✅ utworzony. gf-review nie wywali się na braku pliku.
- [x] US-CLEAN-4: T0-guard **GREEN** — zero twardych osieroconych referencji z zachowanego agenta/runtime (szczegóły Sekcja F).
- [x] Regresja: pełna `pytest -m 'not e2e'` = **323 passed / 2 skipped / 0 failed** (257s) — exact baseline.
- [ ] /sec ✅ (Sekcja D — pre-zwalidowane przez /dev, czeka pieczęć).
- [x] /audyt ✅ **APPROVE z notami** (spójność warstwy — 2026-06-23). Evidence-verified: discovery=48, graveyard=27, sum=75 (zero overlap); PROJECT_SKILLS lista 48 = `ls .claude/skills/` (diff=0 dwukierunkowo); INDEX pokrywa ADR-001..015 (15/15); guard refs = tylko soft-inventory/N/A (zero prescriptive load-directive z zachowanego agenta; `smartmyodoo/`=0); gf-review F5A/F5B=N/A + F9=pytest/ruff/bandit/docker (struktura 9 faz nienaruszona, `go build` tylko w negacji); production-readiness scoring 0-100 + 5 lenses zachowany (Tenant=N/A ADR-008). 2 dewiacje (mv symlinka, local override) SPÓJNE z D1/D2/D5 — udokumentowane w `_graveyard/README.md`. Noty (nieblokujące, CLEAN-02): `dev.md:38` używa `go-idioms` jako przykład syntaxu `Skill` (wyniesiony); `qa.md:51`/`test.md:52` stale „istnieją 1:1" (`go-testing`/`react-patterns`/`vitest-testing`). Pełny raport B½.

### Close Checklist
- [ ] Zadania Sekcji B = ✅, status → `DONE`, `closed`.
- [ ] Lessons Learned (Sekcja F).
- [ ] Zmergowane do `main`.

---

## 📚 Sekcja F — Lessons Learned
> (uzupełnia /dev + /qa po realizacji)

### /dev (CLEAN-01, 2026-06-23) — realizacja TDD T0-guard→T4→T1→T2→T3→T5→T6

- **🔑 KLUCZOWE ODKRYCIE: skile w `.claude/skills/` to SYMLINKI do `.agents/skills/`, a `.claude/` jest GITIGNORED (ADR-009).** Artefakt D1 zakładał `git mv` realnych plików — niemożliwe (nic nie śledzone; realna treść w `.agents/` = D2-nietykane). **Rozwiązanie zgodne z intencją:** `mv` *symlinka* z `.claude/skills/` do `.claude/_graveyard/skills/` — usuwa z discovery, reversible, treść w `.agents/` nietknięta. **Instynkt:** przed `git mv` w warstwie `.claude/` sprawdź `ls -l` (symlink?) i `git check-ignore` (tracked?) — TeamEngine montuje skile jako junctiony, nie kopie.
- **⚠️ DEWIACJA T3 vs D2 — production-readiness też był symlinkiem do `.agents/`.** D5 mówił „adaptuj w miejscu", ale „miejsce" = `.agents/skills/production-readiness/SKILL.md` (D2-nietykane). Edycja przez symlink pisałaby do `.agents/`. **Rozwiązanie:** zerwano symlink + zapisano LOKALNY override (`.claude/skills/production-readiness/SKILL.md` jako realny plik) — wzorzec wrapper-override jak dla agentów. `.agents/` source pozostał z oryginalnym `go build`/`ENABLE ROW LEVEL`. **Do decyzji /arch:** czy to akceptowalny wzorzec (local override file zamiast symlinka) dla skili wymagających stack-adaptacji.
- **T0-guard: rozróżnienie „twarda referencja" vs „soft inventory".** Trafienia w `.claude/agents/*.md` to wyłącznie: (a) noty korekcyjne „istnieją 1:1" (inventory nazw), (b) mapowania `@core-components→goforge-ui-atomic+atomic-design` (frontend, N/A vanilla-JS), (c) fazy F5A/F5B/F9 gf-review (oczekiwane, zaadaptowane w T2), (d) `go-idioms` jako *przykład składni* `Skill` w dev.md. ŻADNA nie jest prescriptive load-directive dla stacku Python/Odoo. `smartmyodoo/` = 0. `.agents/workflows/` = SSoT GoForge (D2). **Instynkt:** guard musi klasyfikować referencje (load-bearing vs informacyjna), nie tylko liczyć trafienia grep.
- **Stale „istnieją 1:1" po wyniesieniu.** Noty w `audyt.md`/`qa.md`/`test.md` listują m.in. `react-patterns`, `go-observability`, `multitenancy`, `go-testing` jako „istnieją 1:1" — po T1 część jest w `_graveyard` (nie w discovery). Skorygowano `audyt.md` (T6). `qa.md:51` i `test.md:52` nadal mają stale wzmianki `go-testing`/`react-patterns` w notach inventory — **nieblokujące** (to nie load-directive), ale do sprzątnięcia w przyszłym sprincie (kandydat na CLEAN-02).
- **ADR-y w repo to 15, nie 10.** Artefakt T4 mówił „ADR-001..010"; faktycznie `docs/adr/` ma ADR-001..015 (ADR-003 superseded by ADR-004). INDEX.md wygenerowano z pełnego zakresu. **Instynkt:** generuj INDEX z `ls`, nie z założonego zakresu w artefakcie.
- **`docs/adr/` i `docs/blueprint/` są gitignored (ADR-009 local-only).** Pliki T4 (`INDEX.md`, `00_lessons_learned.md`) fizycznie istnieją na dysku (gdzie KROK 0 agentów je czyta), ale nie pojawią się w `git status` ani nie wejdą do repo. To zgodne z intencją scaffoldingu runtime (D3) — bramki czytają z dysku, nie z gita.

### Handoff
> **/dev → /qa + /audyt + /sec (2026-06-23):** ✅ **CLEAN-01 zrealizowane (7/7 zadań).** Regresja `323 passed / 2 skipped / 0 failed` (baseline). Discovery: 48 skili, 27 w kwarantannie. `smartmyodoo/` nietknięte (tylko wiszące WIRE-01). **2 DEWIACJE od literalnego artefaktu (intencja zachowana) — do akceptacji /arch:** (1) `mv` symlinka zamiast `git mv` (`.claude/` gitignored); (2) production-readiness jako lokalny override-plik zamiast edycji symlinka do `.agents/` (D2). NIE commitowano, NIE mergowano. Otwarte dla następnych: /sec pieczęć (Sekcja D pre-zwalidowana), /audyt spójność, ew. CLEAN-02 (sprzątnięcie stale „istnieją 1:1" w qa.md/test.md).
> **/arch → user:** artefakt **PROPOSED**. Wymaga akceptacji zakresu. Kluczowe decyzje: D1 (kwarantanna nie delete), D2 (`.agents/` nietykane — override w wrapperze), D3 (dorobić scaffolding zamiast wyłączać bramkę). HARD STOP ADR-7: /dev nie startuje bez zatwierdzenia.
