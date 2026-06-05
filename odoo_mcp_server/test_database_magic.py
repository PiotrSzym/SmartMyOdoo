import pytest
import os
import database_magic

@pytest.fixture
def mock_shadow_mode(monkeypatch, tmp_path):
    test_file = tmp_path / "test_proposals.json"
    import shadow_mode
    monkeypatch.setattr(shadow_mode, "PROPOSALS_FILE", str(test_file))
    return test_file

def test_valid_types(mock_shadow_mode):
    proposal1 = database_magic.propose_magic_fix("force_cancel_invoice", 10, "Test")
    assert proposal1["action_type"] == "magic_force_cancel_invoice"
    
    proposal2 = database_magic.propose_magic_fix("unlock_stock_move", 11, "Test")
    assert proposal2["action_type"] == "magic_unlock_stock_move"
    
    proposal3 = database_magic.propose_magic_fix("change_uom_on_product", 12, "Test")
    assert proposal3["action_type"] == "magic_change_uom_on_product"

def test_invalid_type(mock_shadow_mode):
    with pytest.raises(ValueError, match="Nieznany typ magicznej naprawy"):
        database_magic.propose_magic_fix("delete_all", 99, "Test")

def test_warning_field(mock_shadow_mode):
    proposal = database_magic.propose_magic_fix("force_cancel_invoice", 1, "Test")
    assert "system_warning" in proposal["values"]
    assert "🚨 UWAGA" in proposal["values"]["system_warning"]

def test_action_prefix(mock_shadow_mode):
    proposal = database_magic.propose_magic_fix("unlock_stock_move", 1, "Test")
    assert proposal["action_type"].startswith("magic_")
