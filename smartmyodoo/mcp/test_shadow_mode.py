import pytest
import os
import json
import shadow_mode
from shadow_mode import load_proposals, create_proposal
from smartmyodoo.core.database import Base, engine, SessionLocal
from smartmyodoo.core.models import Proposal

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_empty_load():
    assert load_proposals() == []

def test_create_proposal():
    proposal = create_proposal("update", "res.partner", [1], {"name": "Test"}, "Test reason")
    assert proposal["action_type"] == "update"
    assert proposal["model_name"] == "res.partner"
    assert proposal["record_ids"] == [1]
    assert proposal["values"] == {"name": "Test"}
    assert proposal["reason"] == "Test reason"

def test_status():
    proposal = create_proposal("create", "res.partner", [], {"name": "Test"})
    assert proposal["status"] == "pending"

def test_multi_persist():
    create_proposal("update", "res.partner", [1], {"name": "Test1"})
    create_proposal("update", "res.partner", [2], {"name": "Test2"})
    proposals = load_proposals()
    assert len(proposals) == 2
    assert proposals[0]["record_ids"] == [1]
    assert proposals[1]["record_ids"] == [2]

def test_cleanup():
    create_proposal("update", "res.partner", [1], {"name": "Test"})
    assert len(load_proposals()) == 1
    # Cleanup in DB
    db = SessionLocal()
    db.query(Proposal).delete()
    db.commit()
    db.close()
    assert len(load_proposals()) == 0
