import json
import uuid
import datetime
from smartmyodoo.core.database import SessionLocal
from smartmyodoo.core.models import Proposal

def load_proposals(workspace_id: str = "default") -> list:
    db = SessionLocal()
    try:
        records = db.query(Proposal).filter(Proposal.workspace_id == workspace_id).all()
        result = []
        for r in records:
            try:
                data = json.loads(r.plan_json)
                data["id"] = r.id
                data["status"] = r.status
                data["created_at"] = r.created_at.isoformat() if r.created_at else None
                result.append(data)
            except Exception:
                pass
        return result
    finally:
        db.close()


def create_proposal(action_type: str, model_name: str, record_ids: list, values: dict, reason: str = "", workspace_id: str = "default") -> dict:
    """Tworzy propozycję modyfikacji w trybie Shadow Mode w SQLite (uwzględnia workspace_id)."""
    proposal_data = {
        "action_type": action_type,
        "model_name": model_name,
        "record_ids": record_ids,
        "values": values,
        "reason": reason
    }
    
    db = SessionLocal()
    try:
        new_prop = Proposal(
            status="pending",
            workspace_id=workspace_id,
            plan_json=json.dumps(proposal_data, ensure_ascii=False)
        )
        db.add(new_prop)
        db.commit()
        db.refresh(new_prop)
        
        proposal_data["id"] = new_prop.id
        proposal_data["workspace_id"] = new_prop.workspace_id
        proposal_data["status"] = new_prop.status
        proposal_data["created_at"] = new_prop.created_at.isoformat() if new_prop.created_at else datetime.datetime.now().isoformat()
        return proposal_data
    finally:
        db.close()

def accept_proposal(proposal_id: int) -> bool:
    """Zmienia status propozycji na 'approved'."""
    db = SessionLocal()
    try:
        prop = db.query(Proposal).filter(Proposal.id == proposal_id).first()
        if prop:
            prop.status = "approved"
            db.commit()
            return True
        return False
    finally:
        db.close()

def reject_proposal(proposal_id: int) -> bool:
    """Zmienia status propozycji na 'rejected'."""
    db = SessionLocal()
    try:
        prop = db.query(Proposal).filter(Proposal.id == proposal_id).first()
        if prop:
            prop.status = "rejected"
            db.commit()
            return True
        return False
    finally:
        db.close()
