from unittest.mock import patch, MagicMock
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

    manager = SandboxManager()
    manager.enabled = True

    scratchpad = manager.enter_sandbox("test_db")
    assert scratchpad == "test_db_agent_scratchpad"

    manager.exit_sandbox(success=False)
    assert manager.active_scratchpad is None
    # error causes rollback
    mock_db_mgr.drop_database.assert_called_once_with("test_db_agent_scratchpad")


def test_is_write_tool():
    manager = SandboxManager()
    assert manager.is_write_tool("odoo_create") is True
    assert manager.is_write_tool("odoo_update") is True
    assert manager.is_write_tool("odoo_search") is False
