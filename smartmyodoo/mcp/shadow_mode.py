import json
import datetime
import uuid
from smartmyodoo.core.database import SessionLocal
from smartmyodoo.core.models import Proposal


def load_proposals(workspace_id: str = "default") -> list:
    db = SessionLocal()
    try:
        records = db.query(Proposal).filter(Proposal.workspace_id == workspace_id).all()
        result = []
        for r in records:
            try:
                val_data = json.loads(str(r.values)) if r.values else {}
                record_ids = val_data.get("record_ids", [])
                values = val_data.get("values", {})

                data = {
                    "id": r.id,
                    "workspace_id": r.workspace_id,
                    "action_type": r.method,
                    "model_name": r.odoo_model,
                    "record_ids": record_ids,
                    "values": values,
                    "reason": r.reason,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                result.append(data)
            except Exception:
                pass
        return result
    finally:
        db.close()


def create_proposal(
    action_type: str,
    model_name: str,
    record_ids: list,
    values: dict,
    reason: str = "",
    workspace_id: str = "default",
) -> dict:
    """Tworzy propozycję modyfikacji w trybie Shadow Mode w SQLite (uwzględnia workspace_id)."""
    proposal_id = str(uuid.uuid4())[:8]
    val_payload = {"record_ids": record_ids, "values": values}

    db = SessionLocal()
    try:
        new_prop = Proposal(
            id=proposal_id,
            status="pending",
            workspace_id=workspace_id,
            odoo_model=model_name,
            method=action_type,
            values=json.dumps(val_payload, ensure_ascii=False),
            reason=reason,
        )
        db.add(new_prop)
        db.commit()
        db.refresh(new_prop)

        proposal_data = {
            "id": new_prop.id,
            "workspace_id": new_prop.workspace_id,
            "action_type": new_prop.method,
            "model_name": new_prop.odoo_model,
            "record_ids": record_ids,
            "values": values,
            "reason": new_prop.reason,
            "status": new_prop.status,
            "created_at": (
                new_prop.created_at.isoformat()
                if new_prop.created_at
                else datetime.datetime.now().isoformat()
            ),
        }
        return proposal_data
    finally:
        db.close()


def accept_proposal(proposal_id: str) -> bool:
    """Zmienia status propozycji na 'approved'."""
    db = SessionLocal()
    try:
        prop = db.query(Proposal).filter(Proposal.id == proposal_id).first()
        if prop:
            prop.status = "approved"  # type: ignore
            db.commit()
            return True
        return False
    finally:
        db.close()


def reject_proposal(proposal_id: str) -> bool:
    """Zmienia status propozycji na 'rejected'."""
    db = SessionLocal()
    try:
        prop = db.query(Proposal).filter(Proposal.id == proposal_id).first()
        if prop:
            prop.status = "rejected"  # type: ignore
            db.commit()
            return True
        return False
    finally:
        db.close()
