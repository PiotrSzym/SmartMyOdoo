import pytest
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
    proposal = create_proposal(
        "update", "res.partner", [1], {"name": "Test"}, "Test reason"
    )
    assert proposal["action_type"] == "update"
    assert proposal["model_name"] == "res.partner"
    assert proposal["record_ids"] == [1]
    assert proposal["values"] == {"name": "Test"}
    assert proposal["reason"] == "Test reason"


def test_status():
    proposal = create_proposal("create", "res.partner", [], {"name": "Test"})
    assert proposal["status"] == "pending"


def test_multi_persist():
    create_proposal("create", "res.partner", [], {"name": "P1"}, workspace_id="ws_1")
    create_proposal("update", "res.partner", [1], {"name": "P2"}, workspace_id="ws_2")

    props1 = load_proposals(workspace_id="ws_1")
    props2 = load_proposals(workspace_id="ws_2")
    assert len(props1) == 1
    assert len(props2) == 1
    assert props1[0]["values"]["name"] == "P1"
    assert props2[0]["values"]["name"] == "P2"
    assert props2[0]["record_ids"] == [1]


def test_cleanup():
    create_proposal("update", "res.partner", [1], {"name": "Test"})
    assert len(load_proposals()) == 1
    # Cleanup in DB
    db = SessionLocal()
    db.query(Proposal).delete()
    db.commit()
    db.close()
    assert len(load_proposals()) == 0


def test_accept_proposal():
    prop = create_proposal("create", "res.partner", [], {"name": "Test Accept"})
    assert prop["status"] == "pending"

    shadow_mode.accept_proposal(prop["id"])
    proposals = load_proposals()
    accepted = next(p for p in proposals if p["id"] == prop["id"])
    assert accepted["status"] == "approved"


def test_reject_proposal():
    prop = create_proposal("create", "res.partner", [], {"name": "Test Reject"})
    assert prop["status"] == "pending"

    shadow_mode.reject_proposal(prop["id"])
    proposals = load_proposals()
    rejected = next(p for p in proposals if p["id"] == prop["id"])
    assert rejected["status"] == "rejected"
