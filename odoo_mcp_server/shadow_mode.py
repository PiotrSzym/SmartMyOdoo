import json
import os
import uuid
import datetime

PROPOSALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proposals.json")

def load_proposals() -> list:
    if not os.path.exists(PROPOSALS_FILE):
        return []
    with open(PROPOSALS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_proposals(proposals: list):
    with open(PROPOSALS_FILE, "w", encoding="utf-8") as f:
        json.dump(proposals, f, indent=4, ensure_ascii=False)

def create_proposal(action_type: str, model_name: str, record_ids: list, values: dict, reason: str = "") -> dict:
    """Tworzy propozycję modyfikacji w trybie Shadow Mode."""
    proposals = load_proposals()
    
    proposal = {
        "id": f"PRP-{uuid.uuid4().hex[:8].upper()}",
        "created_at": datetime.datetime.now().isoformat(),
        "status": "pending", # pending, approved, rejected
        "action_type": action_type, # update, create, delete, execute
        "model_name": model_name,
        "record_ids": record_ids,
        "values": values,
        "reason": reason
    }
    
    proposals.append(proposal)
    save_proposals(proposals)
    
    return proposal
