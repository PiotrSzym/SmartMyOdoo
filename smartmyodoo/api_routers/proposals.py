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
    prop = (
        db.query(db_models.Proposal)
        .filter(db_models.Proposal.id == proposal_id)
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Proposal not found")
    prop.status = "approved"  # type: ignore
    db.commit()
    return {"success": True, "status": "approved"}


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
