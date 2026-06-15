# 📚 Dokumentacja SmartMyOdoo — Mapa (klikalna)

Centralny indeks. Linki **klikalne** (działają na GitHubie i w edytorze).
🟢 = widoczne w repo · 🔴 = **lokalne** (gitignored, tylko na dysku — patrz „Dokumenty lokalne").

---

## 🚀 Start tutaj
| Dokument | Co to |
|---|---|
| 🟢 [CHANGELOG](../CHANGELOG.md) | Co się zmieniło (FIX-01: audyt+hardening, F7-03) |
| 🟢 [Roadmap](blueprint/tom2-architektura/roadmap.md) | Co kiedy dostarczamy |
| 🟢 [README projektu](../README.md) | Opis, uruchomienie, bezpieczeństwo |

## 🏛️ Architektura & Design
| Dokument | Co to |
|---|---|
| 🟢 [DESIGN — Rejestr kluczy + Routing modeli LLM](architecture/DESIGN-credentials-and-model-routing.md) | 3 typy kluczy (odoo_data/odoo_timesheet/llm_provider) + wybór modelu (tani↔drogi) |
| 🟢 [Mapa zmian UI — K6](architecture/UI-K6-change-map.md) | gdzie w panelu: dropdown Typ (Skarbiec), nowa zakładka „Modele", badge w Czacie |
| 🟢 [ADR-005 — Agent Integrations](architecture/ADR-005_agent_integrations.md) | Decyzja: integracje agentów |
| 🔴 [HLD-TECHNICAL](blueprint/tom2-architektura/HLD-TECHNICAL.md) | High-Level Design techniczny (C1-C3, FSM, dispatcher, role) — *lokalny* |
| 🔴 [HLD-BUSINESS](blueprint/tom2-architektura/HLD-BUSINESS.md) | Jak działa produkt (biznes, koszty, FAQ) — *lokalny* |

## 🛠️ Przewodniki (Guides)
| Dokument | Co to |
|---|---|
| 🟢 [Odoo: Docker / Edycje / Hosting](guides/odoo_docker_environment.md) | Stawianie Odoo, wersje 16/18/19, Community vs Enterprise, SaaS/sh/OnPrem, pułapki |

## 🏃 Sprinty — aktualne
| Dokument | Status |
|---|---|
| 🟢 [EPIC-FIX-01 — Naprawa i Weryfikacja](sprints/2026-06-15_EPIC-FIX-01_naprawa_weryfikacja.md) | ✅ zakończony (S1+S2) |
| 🟢 [SPRINT-FIX-02 — Struktura i Patterny](sprints/2026-06-15_SPRINT-FIX-02_struktura_patterny.md) | 🏗️ w toku (S3.1 routery) |
| 🟢 [SPRINT-KEY-01 — Rejestr kluczy + Routing modeli](sprints/2026-06-15_SPRINT-KEY-01_credentials_model_routing.md) | ✅ K1-K6 dostarczone (typowany rejestr + routing + UI Modele) |
| 🟢 [SPRINT-F7-03 — Advanced Features (Redis Queue)](sprints/2026-06-08_SPRINT-F7-03_advanced_features.md) | ✅ |
| 🟢 [Wszystkie sprinty →](sprints/) | ~50 plików (historia F2-F7, HUB, QA, UX) |

## 🔐 Dokumenty lokalne (gitignored — tylko na dysku)
Nie ma ich na GitHubie (polityka: wiedza operacyjna/wrażliwa zostaje lokalnie):
- **HLD** — `docs/blueprint/tom2-architektura/HLD-TECHNICAL.md`, `HLD-BUSINESS.md`
- **Blueprint Tom 1-2** — `docs/blueprint/tom1-wiedza/` (master_knowledge_map, error_registry, user_stories), `tom2-architektura/` (TECH_STACK, agent_decision_protocol, intent_taxonomy…)
- **ADR (14)** — `docs/adr/ADR-001…014` (Dual-Auth, Exception-Handling, Schema-Migrations, GDPR…)
- **TeamEngine** — `.agents/` (skille agentów, `AUDIT_REPORT.md`, `ARCH_AUDIT.md`, `SKILL_GAP_MAP.md`)

> Chcesz któryś z lokalnych „wynieść" do repo (jak zrobiliśmy z kompendium Docker)? Powiedz — przeniosę do `docs/guides` lub `docs/architecture`.

---
*Indeks utrzymywany ręcznie — przy dodawaniu dokumentu dopisz tu link.*
