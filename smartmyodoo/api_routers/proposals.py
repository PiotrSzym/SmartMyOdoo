"""S3.1: domena `proposals` wydzielona z api.py (God Module) jako APIRouter.

Zachowanie bez zmian — te same ścieżki (`/api/proposals`, `/{id}/approve`, `/{id}/reject`),
ta sama zależność `require_auth`. `require_auth` importowany z `smartmyodoo.api` (late-resolved:
api.py dołącza ten router na końcu, gdy require_auth jest już zdefiniowane).
"""

import json
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from smartmyodoo.core.database import get_db
from smartmyodoo.core import models as db_models
from smartmyodoo.core.lock import proposal_lock
from smartmyodoo.api_deps import require_auth

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


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
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """WRITE-01 T1: STEP-UP APPLY — wykonuje propozycję na LIVE Odoo.

    Domyka lukę E-W003 (execute nigdy nie wołane). PIN = `require_auth` (bramka
    step-up; tryb 🔴 + PIN = jawna autoryzacja człowieka, D5 — z pominięciem sandboxa).
    Auto-approve z pending → execute. Każda akcja (sukces/błąd) → audit_log (ADR-013/D4).
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
        if str(prop.status) == "rejected":
            raise HTTPException(status_code=409, detail="Proposal already rejected")
        if str(prop.status) == "pending":
            prop.status = "approved"  # type: ignore
            db.commit()

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
