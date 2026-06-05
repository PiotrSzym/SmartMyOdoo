# 🏛️ EPIC: HUB-01 — Centrum Zarządzania SmartMyOdoo

> **Właściciel:** /arch | **Priorytet:** P0 (Krytyczny)
> **Data Utworzenia:** 2026-06-05 | **Bazuje na:** Audyt Architektoniczny F7

---

## 📌 Definicja Epica

### Cel strategiczny
Przekształcenie strony SmartMyOdoo Hub (`http://localhost:8000`) z czystego "Sejfu na hasła" w **pełnoprawne Centrum Zarządzania** — z wbudowanym Czatem AI, routowaniem intencji, integracją ze Skarbcem i podglądem propozycji Shadow Mode.

### Wizja końcowa (North Star)
Użytkownik wchodzi na `http://localhost:8000`, loguje się, wybiera Przestrzeń Roboczą (np. "Production"), przechodzi do zakładki "Czat", wpisuje polecenie ("Dodaj leada dla firmy ACME z tagiem VIP"), a system:
1. Klasyfikuje intencję (Dispatcher → Persona DBA)
2. Wyciąga kredencjale Odoo ze Skarbca dla wybranej przestrzeni
3. Tworzy propozycję Shadow Mode (CREATE na `crm.lead`)
4. Wyświetla kartę propozycji w UI z przyciskami Approve/Reject

### Decyzje architektoniczne
- **Wtyczka OWL w Odoo** → odłożona na Roadmapę (nie blokuje tego Epica)
- **Frontend** → Vanilla JS (rozbudowa istniejącego Micro-SPA)
- **Backend** → FastAPI na porcie 8000 (rozbudowa istniejącego `api.py`)
- **AI** → Dispatcher (heurystyczny fallback) + opcjonalnie OpenRouter LLM

---

## 🗺️ MASTER PROGRESS BAR

| Sprint | Nazwa | Target | Status |
|--------|-------|--------|--------|
| **HUB-S1** | Chat UI na Hubie | 2026-06-06 | ✅ DONE |
| **HUB-S2** | Backend Mózgu (Dispatcher Live) | 2026-06-07 | ✅ DONE |
| **HUB-S3** | Kontekst Workspace + Shadow Mode UI | 2026-06-08 | ✅ DONE |

**Total Completion:** 3/3 Sprintów (100%) 🏆

---

## 📋 Sprint Registry

| ID | Topic | Arch Plan Path | Status |
|----|-------|----------------|--------|
| HUB-S1 | Chat UI Frontend | `docs/sprints/2026-06-05_HUB-S1_chat_ui_sprint.md` | ✅ DONE |
| HUB-S2 | Dispatcher Integration | `docs/sprints/2026-06-05_HUB-S2_dispatcher_live_sprint.md` | ✅ DONE |
| HUB-S3 | Workspace Context + Shadow Mode | `docs/sprints/2026-06-05_HUB-S3_workspace_shadow_sprint.md` | ✅ DONE |

---

## 🔗 Zależności i Odłożone

### Odłożone na Roadmapę (nie blokują Epica)
- `custom_addons/smart_chat/` — Wtyczka OWL w Odoo (osobny Epic w przyszłości)
- `swarm/brain/` — Shared Brain RAG (podpięcie po Sprint 2)
- `mcp/server.py` — MCP Server stdio (podpięcie po Sprint 3)

### Wymagania wejściowe (spełnione)
- ✅ Vault API działa (`/api/status`, `/api/auth`, `/api/secrets`)
- ✅ Dispatcher napisany i przetestowany (`tests/swarm/test_dispatcher.py`)
- ✅ Modele Pydantic gotowe (`ChatRequest`, `ChatResponse`)
- ✅ OdooClient z fabryką workspace (`mcp/odoo_client.py`)
