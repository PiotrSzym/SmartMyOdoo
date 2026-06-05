import pytest
import os
import json
import shadow_mode
from shadow_mode import load_proposals, save_proposals, create_proposal

@pytest.fixture
def mock_proposals_file(tmp_path, monkeypatch):
    test_file = tmp_path / "test_proposals.json"
    monkeypatch.setattr(shadow_mode, "PROPOSALS_FILE", str(test_file))
    return test_file

def test_empty_load(mock_proposals_file):
    assert load_proposals() == []
    
    # Test loading invalid JSON
    mock_proposals_file.write_text("{invalid")
    assert load_proposals() == []

def test_create_proposal(mock_proposals_file):
    proposal = create_proposal("update", "res.partner", [1], {"name": "Test"}, "Test reason")
    assert proposal["action_type"] == "update"
    assert proposal["model_name"] == "res.partner"
    assert proposal["record_ids"] == [1]
    assert proposal["values"] == {"name": "Test"}
    assert proposal["reason"] == "Test reason"

def test_id_format(mock_proposals_file):
    proposal = create_proposal("update", "res.partner", [1], {"name": "Test"})
    assert proposal["id"].startswith("PRP-")
    assert len(proposal["id"]) == 12 # PRP- + 8 hex chars

def test_status(mock_proposals_file):
    proposal = create_proposal("create", "res.partner", [], {"name": "Test"})
    assert proposal["status"] == "pending"

def test_multi_persist(mock_proposals_file):
    create_proposal("update", "res.partner", [1], {"name": "Test1"})
    create_proposal("update", "res.partner", [2], {"name": "Test2"})
    proposals = load_proposals()
    assert len(proposals) == 2
    assert proposals[0]["record_ids"] == [1]
    assert proposals[1]["record_ids"] == [2]

def test_cleanup(mock_proposals_file):
    # Just a placeholder for any cleanup/truncation if we had one.
    # Since we don't have a clear cleanup function in shadow_mode, let's just write/read raw
    create_proposal("update", "res.partner", [1], {"name": "Test"})
    assert len(load_proposals()) == 1
    os.remove(mock_proposals_file)
    assert len(load_proposals()) == 0
