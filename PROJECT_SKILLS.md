# 🛠️ SmartMyOdoo — PROJECT SKILLS (allowlist)

> **Źródło prawdy „co jest nasze".** Stack = **Python/FastAPI + vanilla JS + Odoo**, LOCAL-ONLY (ADR-008), vanilla JS (ADR-006).
> **52 skile dozwolone** w discovery (`.claude/skills/`). **27 skili Go/React** wyniesionych do kwarantanny `.claude/_graveyard/skills/` (CLEAN-01, 2026-06-23 — patrz `.claude/_graveyard/README.md`).
> **Tagi:** `[#skills, #allowlist, #tooling, #clean-01]`

---

## ✅ 52 dozwolone skile (discovery)

### 🤖 Agent/LLM engineering (6)
`agent-architecture-audit`, `agent-evaluation`, `agent-harness-construction`,
`agent-introspection-debugging`, `cost-aware-llm-pipeline`, `rag-engineer`

### 🐍 Python / Backend / API (4)
`fastapi-patterns`, `python-testing`, `redis-patterns`, `mcp-server`

### 🦋 Odoo (13)
`odoo-api-expert`, `odoo-audit-history`, `odoo-business-analyst`, `odoo-crud`,
`odoo-developer`, `odoo-devops-github`, `odoo-docker-environment`, `odoo-etl-manager`,
`odoo-sh-logs`, `financial-audit`,
`odoo-mail-from-override` *(2026-08-01: zmiana adresu nadawcy maili per moduł — automat na mail.mail; live gfcrm.pl Projekty → gf-komunikacja@; rejestracja uzupełniona 2026-08-06 — wcześniej brakował w allowliście)*,
`odoo-website-embed` *(2026-08-04: osadzanie samodzielnego HTML jako strona Website + kurs eLearning z certyfikacją; sprawdzony na PROD gfcrm.pl — deck „Metodyka Projektowa", kurs 18)*,
`odoo-website-domain` *(2026-08-06: dodawanie/podpinanie domen do witryn Website — DNS SEOHOST → Cyberfolks/.htaccess → SSL → panel Odoo → website.domain → web.base.url → Azure; skodyfikowane z modułu Wiedza GF art. 3797/3552/2569/3554 + audyt live 12 witryn prod)*

> **2026-08-12 — wzbogacenie (bez zmiany liczby):** `odoo-devops-github` przepisany na pełny playbook GitHub→Odoo.sh (feature→dev→staging→prod, wersjonowanie, migracje, submoduły, backupy, upgrade, role, hard-blocks) + companion `REFERENCE.md` z cytatami (baza wiedzy myodoo.pl art. 83/85/93/103/116/219/224 scalona z oficjalną dok. Odoo.sh/GitHub). `odoo-sh-logs` doładowany o typy logów (`install/update/odoo/pip.log`) + strukturę FS builda. Kopie global + lokalna zsynchronizowane.

### 🔬 Testing / QA / E2E (5)
`e2e-testing-patterns`, `playwright-e2e`, `webapp-testing`, `test-fixing`, `systematic-debugging`

### 🔍 Review / Audit / Security (diagnostic — NIE dla /dev) (6)
`gf-review`, `gf-auditor`, `find-bugs`, `threat-hunting`, `dependency-management`, `security-audit`

### 🏭 Ops / DevOps / Release (4)
`production-readiness` *(LOCAL override — adaptowany CLEAN-01)*,
`docker-compose` *(LOCAL override 2026-07-11 — realny stack 4 serwisów SMO)*,
`github-actions-ci` *(LOCAL override 2026-07-11 — realny ci.yml RELEASE-01)*, `git-pushing`

### 🧠 Knowledge / Process / Governance (10)
`knowledge-search`, `lessons-learned-engine`,
`fireflies-transcripts` *(2026-08-07: pobieranie na żądanie transkryptów Fireflies → `Klienci\<klient>\04_Spotkania`; skrypt `scripts/fireflies_pull.py` + sekret FIREFLIES_KEY w Skarbcu + mapa `_fireflies_map.yml`)*,
`onboarding-guide` *(LOCAL override 2026-07-11 — onboarding do SMO, nie GoForge)*, `plan-routing`,
`spike`, `context-management`, `research-ops`, `software-architecture`, `verification-before-completion`

### 🛡️ Compliance / Data (2)
`gdpr-data-handling`, `gateguard`

### 🆘 Awaryjne / Edukacja (2)
`magic-fix`, `teacher`

> **Razem: 52.** (Weryfikacja: `ls -d .claude/skills/*/ | wc -l` = 52; stan 2026-08-07.)

---

## 🪦 27 skili w kwarantannie (`.claude/_graveyard/skills/`) — NIE w discovery

Balast GoForge (Go + React/Next), N/A dla stacku Python/vanilla-JS/Odoo. Przywracalne (`mv` z powrotem) — patrz `.claude/_graveyard/README.md`.

- **Go (15):** `go-audit-compliance`, `go-concurrency`, `go-ddd`, `go-idioms`, `go-migrations`, `go-observability`, `go-patterns`, `go-resilience`, `go-tenant-ops`, `go-testing`, `golangci-lint`, `buf-protobuf`, `makefile-patterns`, `multitenancy`, `plugin-architecture`
- **React/Next (12, N/A — vanilla JS ADR-006):** `atomic-design`, `goforge-ui-atomic`, `nextjs-best-practices`, `react-patterns`, `dnd-kit-patterns`, `tailwind-v4`, `vitest-testing`, `testing-library`, `vercel-composition`, `vercel-react-perf`, `zustand-state`, `zod-validation`

---

## ⚙️ Narzędzia projektowe (nie-skile)
| Nazwa | Zastosowanie |
| :--- | :--- |
| **SmartMyVault** | Zastrzyki środowiskowe (`vault.py run`), sekrety lokalne (ADR-015). |
| **/pol** | Watchdog — killowanie zapętlonych procesów / halucynacji (ART.5). |
