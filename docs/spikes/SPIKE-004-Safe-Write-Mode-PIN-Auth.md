---
spike_id: "SPIKE-004"
temat: "Safe Write Mode z PIN-Step-Up Auth do Odoo"
data: "2026-06-25"
konsument: "/arch"
autor: "/spike"
model: "claude-haiku-4-5"
bounded_context: "Chat Interface + Shadow Mode + Odoo Write Pipeline"
status: "ready"
---

# 🕵️ SPIKE-004: Safe Write Mode z PIN-Step-Up Auth do Odoo

> **Dla:** `/arch` | **Data:** 2026-06-25
> **Cel MVP:** Bezpieczny zapisy z czata na Odoo: domyślnie tryb READ-ONLY (zielony); świadome przełączenie na EDIT (czerwony); każdy zapis wymaga PIN-a (step-up auth); wdrażając go odpalić `execute_approved_proposals()` na prod.

---

## 1. Scope

**In scope:**
- UI: toggle (read-only ↔ edit mode) w górnym pasku czata
- Backend: `require_auth` dependency waliduje Bearer=PIN + master
- Shadow Mode: propozycje (create/update/delete) → status pending
- Approve endpoint: `POST /api/proposals/{id}/approve` zmienia status → approved
- Execute endpoint: `execute_approved_proposals()` dotarwa na live Odoo
- Sandbox: `SandboxManager` izoluje zapisy (fail-closed)
- Audit: propozycje logują się w SQLite, PII anon + RODO compliance

**Out of scope:**
- WebSocket auto-refresh propozycji (manualny F5 lub polling)
- Distributed approval workflow (multi-user review) — later phase
- Webhook notifications poza lokalnym API
- Magic Fix (propose_magic_fix tool) — istniejący, ale nie scaling tego
- Revert mechanism (approved → pending) — one-way dla MVP

---

## 2. Kontekst Systemu (Boundaries)

| Wymiar | Wartość |
|--------|---------|
| **Moduł** | Chat Interface (UI) + MCP Server (backend) |
| **Backend entry point** | `smartmyodoo/api_routers/proposals.py:50` (approve endpoint) |
| **Backend executor** | `smartmyodoo/mcp/server.py:330-370` (`execute_approved_proposals()`) |
| **Shadow Mode DB** | SQLite — tabela `proposals` (status: pending/approved/executed/rejected) |
| **Sandbox (isolate)** | `smartmyodoo/swarm/sandbox.py:21-95` (`SandboxManager`) |
| **Auth layer** | `smartmyodoo/api_deps.py:38-47` (`require_auth` + Bearer validation) |
| **UI card** | `smartmyodoo/ui/js/components/chat.js:289-399` (proposal card render) |
| **Powiązane moduły** | Vault (PIN storage), PII middleware (anonymization), workspace |

---

## 3. Gotowe Klocki (Re-use First)

### Backend
| Klocek | Ścieżka | Co robi | Status |
|--------|---------|---------|--------|
| `require_auth` | `api_deps.py:38-47` | Waliduje Bearer (PIN lub master), zwraca (vault_key, rola, hasło) | Active ✅ |
| `shadow_mode.create_proposal()` | `mcp/shadow_mode.py:38-82` | Tworzy propozycję w SQLite (CREATE/UPDATE/DELETE) | Active ✅ |
| `shadow_mode.accept_proposal()` | `mcp/shadow_mode.py:85-96` | Zmienia status pending→approved | Active ✅ |
| `execute_approved_proposals()` | `mcp/server.py:330-370` | Iteruje approved, łączy się z live Odoo, wykonuje. GREP: brak wołań poza def | **🔴 LUKA: NIEUŻYWANY — brak endpointu/triggera** |
| `SandboxManager` | `swarm/sandbox.py:21-95` | Fail-closed: bez ODOO_MASTER_PASSWORD throws RuntimeError | Active ✅ |
| `proposal_lock` | `core/lock.py` | Distributed lock (S5.2) zapobiega race condition na approve | Active ✅ |

### Frontend
| Komponent | Ścieżka | Status |
|-----------|---------|--------|
| Shadow Mode Proposal Card | `ui/js/components/chat.js:289-399` | Renderuje propozycję z przyciskami Approve/Reject | Active ✅ |
| API: GET `/api/proposals` | `api_routers/proposals.py:22-47` | Pobiera listę propozycji | Active ✅ |
| API: POST `/api/proposals/{id}/approve` | `api_routers/proposals.py:50-71` | Zatwierdzenie (zmiana status) | Active ✅ |

### Infra / Env
| Zmienna | Znaczenie | Domyślnie |
|---------|-----------|----------|
| `ODOO_MASTER_PASSWORD` | Master password do klonowania bazy (sandbox) | (brak = fail-closed) |
| `SANDBOX_ENABLED` | Włączenie sandboxa | `"true"` |
| `CHAT_HISTORY_TURNS` | Ile tur czata do bufferu LLM | `6` |

---

## 4. Twarde Ograniczenia (ADR & Golden Rules)

| ADR / GR | Reguła | Impact na ten temat |
|----------|--------|---------------------|
| **ADR-005** | SQLite as Single Persistence Layer | Propozycje MUSZĄ być w SQLite (nie JSON files). Zmiga race-condition przy Multi-Workspace. |
| **ADR-008** | Local-Only Architecture (No Cloud) | Sekwencja PIN+execute NIE wysyła danych do chmury — tylko na lokalny/self-hosted Odoo. |
| **ADR-010** | Schema Migrations (Alembic) | Tabela `proposals` zmigrowana już. Dodanie `edit_mode_enabled` boolena musi mieć nową migrację. |
| **ADR-013** | Local Data Retention & GDPR | Propozycje (pending/approved/executed/rejected) podlegają retencji 30 dni. Workspace purge = cascading DELETE propozycji. |
| **ART.10** | Zabezpieczone ORM | Wszystkie zapisy na `Proposal` model przez SQLAlchemy ORM, zero raw SQL dla ShadowMode. |
| **ART.21.6** | Architecture Graph Gate | Moduł nie-greenfield (Shadow Mode istnieje). Godchecker: check God Nodes w mcp/server.py (ponad 25 edges?). |

---

## 5. Pola Minowe (Lessons Learned)

| ID | Pattern / Błąd | Instrukcja dla /arch |
|----|----------------|----------------------|
| **E-W001** | Shadow Mode: propozycje NAS NOT ŁĄCZYĆ SIĘ Z LIVE ODOO | Każdy zapis musi przejść 2 fazy: 1) create_proposal (lokalnie), 2) approve + execute_approved (gdy user clicnie). NIE robić tego w jednym kroku (brak rollback). |
| **E-W002** | Sandbox fail-closed: brak ODOO_MASTER_PASSWORD = RuntimeError (nie ignorować) | Jeśli user zapomni ustawić env, sandbox powinien BLOKOWAĆ operacje write, nie wykonywać z default hasłem. Walidacja na startup. |
| **E-W003** | 🔴 LUKA: Approve endpoint zmienia status ALE `execute_approved_proposals()` nigdy się nie wołuje | `approve_proposal()` zmienia status pending→approved. Ale nikt nie wołuje `execute_approved_proposals()` (GREP: 0 callsites poza def). To jest KLUCZOWA LUKA. /arch musi zdecydować: (1) endpoint RESTful POST /api/proposals/execute, (2) MCP tool (agent wołuje), (3) background job, czy (4) manualny CLI trigger. |
| **INS-009** | Pre-commit hook CRLF w WSL | Jeśli tworzyć migracje bazy — użyj `git commit --no-verify` na WSL (hook się zawiera CRLF). |

---

## 6. Pigułka Kontekstowa (Key Types & Contracts)

```python
# smartmyodoo/core/models.py — Proposal ORM model
class Proposal(Base):
    id: str              # UUID skrót (8 chars)
    workspace_id: str    # multi-tenant key
    odoo_model: str      # model name ('sale.order', itp.)
    method: str          # 'create' | 'update' | 'delete'
    values: str          # JSON dict {record_ids, values}
    reason: str          # user intent (free text, anonimizable)
    status: str          # 'pending' | 'approved' | 'executed' | 'rejected'
    created_at: datetime # timestamp

# FastAPI request/response
@router.post("/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),  # (vault_key, role, pwd)
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    # S5.2: distributed lock + idempotencja
    # Returns: {"success": True, "status": "approved", "already": bool}

# MCP Tool (no dependency on FastAPI, standalone)
@mcp.tool()
def execute_approved_proposals(workspace_id: str = "default") -> str:
    # Zwraca: "\n".join([f"Sukces: Propozycja {id}", "Błąd: ..."])
```

```javascript
// UI: propozycja w czacie
if (!isUser && msg.actionType === 'SHADOW_PROPOSAL' && msg.proposalData) {
    // Renderuj kartę z przyciskami: [Approve] [Reject]
    // onClick → POST /api/proposals/{id}/approve (with Bearer token = PIN)
}
```

---

## 7. Pytania Otwarte dla /arch

- [ ] **Q1:** Czy edit-mode toggle wymaga persystencji per-workspace (user preferences)? Czy reset po refresh jest OK?
- [ ] **Q2:** Jak triggerować `execute_approved_proposals()` — czy endpoint RESTful `POST /api/proposals/execute` czy tylko manualna procedura (CLI)?
- [ ] **Q3:** Czy proposal card powinien się auto-refresh (WebSocket/polling) czy manualny F5? Wpływ na user experience vs complexity.
- [ ] **Q4:** Czy audyt wykonanych zmian (approved → executed) powinien trafiać do `audit_log` czy osobna tabela `proposal_executions`?
- [ ] **Q5:** Czy wycofanie approved propozycji (approve → pending) powinno być możliwe czy status jest one-way (pending→approved→executed)?

---

## 6b. Architektura Grafu (Graphify) — dla L2 /arch (ART.21.6)

| Metryka | Wartość | Sygnał dla /arch |
|---------|---------|------------------|
| God Nodes (>25 edges) dotykane | `SandboxManager` (33 edges), współpraża z `SkillExecutor` (64), `SkillConfig` (69) | 🔴 SandboxManager = God Node. Nie zwiększać mu wagi; issue to brak triggerowania execute, nie sandbox. Fail-closed chroni. |
| Cohesion `mcp/server.py` | ~0.09 (niska, typowa dla swarm) | Moduł słabo spójny (MCP tools + Odoo client + PII middleware mieszane). Czy odseparować `execute` do osobnego service? |
| Blast radius `approve` endpoint | 2-3 edges (`Proposal` status-write → index/GET ops) | Nisko-risk. Approve endpoint JEST OK; problem to brak executora. |
| Import cycles | Zero (graphify clean, 2026-06-23) | api_deps→vault (OK), routery→api_deps late. Zero cykli. |
| **KLUCZOWA LUKA** | `execute_approved_proposals()` NIGDY się nie wołuje (GREP: 0 callsites) | Brak endpointu/triggera. Proposal tworzy się (OK), approve zmienia status (OK), ale NIKOMU nie wiadomo kiedy/jak executive. /arch decyduje o triggering mechanism. |

**Rekon Status:** Graphify 2026-06-23 (świeży). Moduł istniejący (Shadow Mode ~3 lat, execute~1 rok, nieużywany). Metryka: SandboxManager God Node ale bezpieczny (fail-closed). Mega-luka: LUKA E-W003 (brak wołania execute).

---

_Wygenerowano przez `/spike` (Haiku 4.5) | Tool calls: 18 | Linie: 190 | Graphify rekon: Graphify 2026-06-23_
