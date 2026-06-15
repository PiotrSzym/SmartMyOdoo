from unittest.mock import patch, MagicMock

import pytest

from smartmyodoo.swarm.sandbox import SandboxManager


@patch("smartmyodoo.swarm.sandbox.OdooDBManager")
def test_sandbox_enter_exit_success(mock_db_mgr_class):
    mock_db_mgr = MagicMock()
    mock_db_mgr.duplicate_database.return_value = True
    mock_db_mgr_class.return_value = mock_db_mgr

    manager = SandboxManager(odoo_url="http://test", master_password="test")
    manager.enabled = True

    scratchpad = manager.enter_sandbox("test_db")
    assert scratchpad == "test_db_agent_scratchpad"
    assert manager.active_scratchpad == "test_db_agent_scratchpad"

    manager.exit_sandbox(success=True)
    assert manager.active_scratchpad is None
    # success doesn't drop the database
    mock_db_mgr.drop_database.assert_not_called()


@patch("smartmyodoo.swarm.sandbox.OdooDBManager")
def test_sandbox_enter_exit_error(mock_db_mgr_class):
    mock_db_mgr = MagicMock()
    mock_db_mgr.duplicate_database.return_value = True
    mock_db_mgr_class.return_value = mock_db_mgr

    manager = SandboxManager(master_password="test")
    manager.enabled = True

    scratchpad = manager.enter_sandbox("test_db")
    assert scratchpad == "test_db_agent_scratchpad"

    manager.exit_sandbox(success=False)
    assert manager.active_scratchpad is None
    # error causes rollback
    mock_db_mgr.drop_database.assert_called_once_with("test_db_agent_scratchpad")


def test_is_write_tool():
    manager = SandboxManager(master_password="test")
    assert manager.is_write_tool("odoo_create") is True
    assert manager.is_write_tool("odoo_update") is True
    assert manager.is_write_tool("odoo_search") is False


def test_sandbox_fail_closed_without_master_password(monkeypatch):
    """S1.2 (dowód): brak ODOO_MASTER_PASSWORD → fail-closed, zero domyślnego 'admin'.

    PRZED naprawą: master_password='admin', enter_sandbox klonował bazę → brak wyjątku (test czerwony).
    PO naprawie: master_password=None, enter_sandbox podnosi RuntimeError (test zielony).
    """
    monkeypatch.delenv("ODOO_MASTER_PASSWORD", raising=False)
    manager = SandboxManager(odoo_url="http://test")
    manager.enabled = True

    # brak cichego fallbacku na 'admin'
    assert manager.master_password is None

    with pytest.raises(RuntimeError, match="ODOO_MASTER_PASSWORD"):
        manager.enter_sandbox("prod_db")
