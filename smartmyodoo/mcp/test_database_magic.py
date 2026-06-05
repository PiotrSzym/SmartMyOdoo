import pytest
import os
import database_magic

from smartmyodoo.core.database import Base, engine, SessionLocal

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_valid_types():
    proposal1 = database_magic.propose_magic_fix("force_cancel_invoice", 10, "Test")
    assert proposal1["action_type"] == "magic_force_cancel_invoice"
    
    proposal2 = database_magic.propose_magic_fix("unlock_stock_move", 11, "Test")
    assert proposal2["action_type"] == "magic_unlock_stock_move"
    
    proposal3 = database_magic.propose_magic_fix("change_uom_on_product", 12, "Test")
    assert proposal3["action_type"] == "magic_change_uom_on_product"

def test_invalid_type():
    with pytest.raises(ValueError, match="Nieznany typ magicznej naprawy"):
        database_magic.propose_magic_fix("delete_all", 99, "Test")

def test_warning_field():
    proposal = database_magic.propose_magic_fix("force_cancel_invoice", 1, "Test")
    assert "system_warning" in proposal["values"]
    assert "🚨 UWAGA" in proposal["values"]["system_warning"]

def test_action_prefix():
    proposal = database_magic.propose_magic_fix("unlock_stock_move", 1, "Test")
    assert proposal["action_type"].startswith("magic_")
