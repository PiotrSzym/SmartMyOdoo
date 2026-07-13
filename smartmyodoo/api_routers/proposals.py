"""S3.1: domena `proposals` wydzielona z api.py (God Module) jako APIRouter.

Zachowanie bez zmian — te same ścieżki (`/api/proposals`, `/{id}/approve`, `/{id}/reject`),
ta sama zależność `require_auth`. `require_auth` importowany z `smartmyodoo.api` (late-resolved:
api.py dołącza ten router na końcu, gdy require_auth jest już zdefiniowane).
"""

import json
from typing import Optional, Tuple

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from smartmyodoo.core.database import get_db
from smartmyodoo.core import models as db_models
from smartmyodoo.core.lock import proposal_lock
from smartmyodoo.api_deps import require_auth, get_auth_key
# FIX-04 T2 (A-2/D3): reużywamy WSPÓLNEGO limitera prób logowania (bez osobnego licznika).
from smartmyodoo.api_routers.auth import _auth_limiter

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


class ApplyProposalRequest(BaseModel):
    """FIX-04 T2 (A-2): świeży PIN (step-up) wymagany do zapisu na LIVE Odoo."""

    pin: str = ""


@router.get("")
async def get_proposals(
    workspace_id: Optional[str] = None,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    query = db.query(db_models.Proposal)
    if workspace_id:
        query = query.filter(db_models.Proposal.workspace_id == workspace_id)
    proposals = query.all()

    res = []
    for p in proposals:
        res.append(
            {
                "id": p.id,
                "workspace_id": p.workspace_id,
                "odoo_model": p.odoo_model,
                "method": p.method,
                "values": json.loads(str(p.values)) if p.values else {},
                "reason": p.reason,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else "",
            }
        )
    return res


@router.post("/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    # S5.2: distributed lock + idempotencja — równoległe approve tej samej propozycji
    # serializują się, a przejście pending→approved (i ew. egzekucja) zachodzi DOKŁADNIE raz.
    with proposal_lock.acquire(f"proposal:approve:{proposal_id}"):
        prop = (
            db.query(db_models.Proposal)
            .filter(db_models.Proposal.id == proposal_id)
            .first()
        )
        if not prop:
            raise HTTPException(status_code=404, detail="Proposal not found")
        already = str(prop.status) == "approved"
        if not already:
            prop.status = "approved"  # type: ignore
            db.commit()
        return {"success": True, "status": "approved", "already": already}


@router.post("/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    prop = (
        db.query(db_models.Proposal)
        .filter(db_models.Proposal.id == proposal_id)
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Proposal not found")
    prop.status = "rejected"  # type: ignore
    db.commit()
    return {"success": True, "status": "rejected"}


@router.post("/{proposal_id}/apply")
async def apply_proposal(
    proposal_id: str,
    body: ApplyProposalRequest,
    request: Request,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """WRITE-01 T1: STEP-UP APPLY — wykonuje propozycję na LIVE Odoo.

    Domyka lukę E-W003 (execute nigdy nie wołane). FIX-04 T2 (A-2/D3): oprócz tokena
    sesji (`require_auth`) wymagany jest ŚWIEŻY PIN w body, walidowany SERWEROWO przeciw
    temu samemu źródłu co login (`get_auth_key`) — nie ufamy wyłącznie bramce klienckiej.
    Zły/brak PIN → 403 + audit_log `proposal_apply_denied` (ochrona limiterem prób).
    Tryb 🔴 + PIN = jawna autoryzacja człowieka (D5 — z pominięciem sandboxa). Auto-approve
    z pending → execute. Każda akcja (sukces/błąd) → audit_log (ADR-013/D4).
    """
    from smartmyodoo.mcp.server import execute_proposal_by_id

    with proposal_lock.acquire(f"proposal:apply:{proposal_id}"):
        prop = (
            db.query(db_models.Proposal)
            .filter(db_models.Proposal.id == proposal_id)
            .first()
        )
        if not prop:
            raise HTTPException(status_code=404, detail="Proposal not found")
        ws = str(prop.workspace_id)

        # ── FIX-04 T2 (A-2/D3): serwerowa walidacja PIN (step-up) ──
        # Świeży PIN z body — NIE z nagłówka sesji. To samo źródło co login (get_auth_key:
        # master lub PIN). Odmowa audytowana; brute-force ograniczony wspólnym limiterem.
        client = request.client.host if request.client else "unknown"
        rl_key = f"apply-pin:{client}"
        if _auth_limiter.is_locked(rl_key):
            raise HTTPException(
                status_code=429,
                detail="Zbyt wiele nieudanych prób PIN. Spróbuj ponownie później.",
            )
        pin_vk, _pin_role = get_auth_key(body.pin)
        if not pin_vk:
            _auth_limiter.record_failure(rl_key)
            # Audyt odmowy — BEZ echa PIN (tylko meta). ADR-011: zero danych wrażliwych.
            db.add(
                db_models.AuditLog(
                    workspace_id=ws,
                    action="proposal_apply_denied",
                    details=f"id={proposal_id} reason=bad_pin",
                )
            )
            db.commit()
            raise HTTPException(
                status_code=403, detail="Nieprawidłowy PIN — zapis wstrzymany."
            )
        _auth_limiter.reset(rl_key)

        if str(prop.status) == "rejected":
            raise HTTPException(status_code=409, detail="Proposal already rejected")
        if str(prop.status) == "pending":
            prop.status = "approved"  # type: ignore
            db.commit()

        # WRITE-03 T1: wstrzyknij poświadczenia Odoo ze Skarbca dla TEJ przestrzeni
        # PRZED zapisem — inaczej execute_proposal_by_id → get_odoo_client → „Brak
        # konfiguracji Odoo” → 500 (apply z UI nie działał od WRITE-01). Czat robił to
        # przez _inject_odoo_creds; tu replikujemy tę samą bramę KEY-02-3 (ADR-007).
        try:
            from smartmyodoo.vault import vault as _vault
            from smartmyodoo.api_routers.chat import _inject_odoo_creds

            _inject_odoo_creds(_vault.load_vault(auth_data[0]), ws)
        except Exception as e:  # noqa: BLE001 — brak credów → execute zwróci błąd, audytowany niżej
            import logging

            logging.getLogger(__name__).warning(
                "WRITE-03: nie udało się wstrzyknąć credów Odoo dla %s: %s", ws, e
            )

        res = execute_proposal_by_id(proposal_id, ws)

        # Audyt (sukces ORAZ błąd) — ADR-013 / D4. Bez wartości PII (tylko meta).
        db.add(
            db_models.AuditLog(
                workspace_id=ws,
                action="proposal_apply",
                details=(
                    f"id={proposal_id} model={prop.odoo_model} method={prop.method} "
                    f"ok={res.get('success')} {res.get('error', '')}".strip()
                ),
            )
        )
        db.commit()

        if not res.get("success"):
            raise HTTPException(
                status_code=500, detail=f"Apply failed: {res.get('error')}"
            )
        return {
            "success": True,
            "status": "executed",
            "already": bool(res.get("already", False)),
        }
