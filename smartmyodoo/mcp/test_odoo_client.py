import pytest
from unittest.mock import MagicMock, patch
import os
import odoo_client

@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("ODOO_URL", raising=False)
    monkeypatch.delenv("ODOO_DB", raising=False)
    monkeypatch.delenv("ODOO_USERNAME", raising=False)
    monkeypatch.delenv("ODOO_PASSWORD", raising=False)

@pytest.fixture
def valid_env(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://test")
    monkeypatch.setenv("ODOO_DB", "test_db")
    monkeypatch.setenv("ODOO_USERNAME", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "admin")

def test_missing_env(clean_env):
    client = odoo_client.OdooClient()
    with pytest.raises(ValueError, match="Brak konfiguracji Odoo"):
        client.connect()

@patch('xmlrpc.client.ServerProxy')
def test_bad_creds(mock_server_proxy, valid_env):
    client = odoo_client.OdooClient()
    mock_common = MagicMock()
    mock_common.authenticate.return_value = False
    mock_server_proxy.return_value = mock_common
    
    with pytest.raises(PermissionError, match="Błąd autoryzacji do Odoo"):
        client.connect()

@patch('xmlrpc.client.ServerProxy')
def test_search_read_mock(mock_server_proxy, valid_env):
    client = odoo_client.OdooClient()
    
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 1
    
    mock_models = MagicMock()
    mock_models.execute_kw.return_value = [{"id": 1, "name": "Test"}]
    
    mock_server_proxy.side_effect = [mock_common, mock_models]
    
    client.connect()
    records = client.search_read('res.partner', [])
    assert len(records) == 1
    assert records[0]["name"] == "Test"

@patch('xmlrpc.client.ServerProxy')
def test_domain_pass(mock_server_proxy, valid_env):
    client = odoo_client.OdooClient()
    
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 1
    
    mock_models = MagicMock()
    mock_models.execute_kw.return_value = []
    
    mock_server_proxy.side_effect = [mock_common, mock_models]
    
def test_workspace_isolation(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://global")
    monkeypatch.setenv("PROJECT_HUB_WS1_ODOO_URL", "http://ws1")
    monkeypatch.setenv("PROJECT_HUB_WS1_ODOO_DB", "ws1_db")
    
    # Domyślny fallback
    client_default = odoo_client.OdooClient()
    assert client_default.url == "http://global"
    
    # Konkretny workspace
    client_ws1 = odoo_client.OdooClient("ws1")
    assert client_ws1.url == "http://ws1"
    assert client_ws1.db == "ws1_db"
    
    # Brak specyficznego - fallback
    client_ws2 = odoo_client.OdooClient("ws2")
    assert client_ws2.url == "http://global"

@patch('xmlrpc.client.ServerProxy')
def test_search_read_limit(mock_server_proxy, valid_env):
    client = odoo_client.OdooClient()
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 1
    mock_models = MagicMock()
    mock_models.execute_kw.return_value = []
    
    mock_server_proxy.side_effect = [mock_common, mock_models]
    
    client.connect()
    domain = [("name", "=", "X")]
    client.search_read('res.partner', domain, fields=['id'], limit=5)
    
    # Assert that execute_kw was called with correct arguments
    mock_models.execute_kw.assert_called_with(
        "test_db", 1, "admin",
        "res.partner", "search_read", [domain],
        {"fields": ["id"], "limit": 5}
    )

@patch('xmlrpc.client.ServerProxy')
def test_fields_get(mock_server_proxy, valid_env):
    client = odoo_client.OdooClient()
    
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 1
    
    mock_models = MagicMock()
    mock_models.execute_kw.return_value = {"name": {"type": "char", "string": "Name"}}
    
    mock_server_proxy.side_effect = [mock_common, mock_models]
    
    client.connect()
    fields = client.get_model_fields('res.partner')
    
    assert "name" in fields
    assert fields["name"]["type"] == "char"

@patch('xmlrpc.client.ServerProxy')
def test_auto_connect(mock_server_proxy, valid_env):
    client = odoo_client.OdooClient()
    assert client.uid is None
    
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 1
    
    mock_models = MagicMock()
    mock_models.execute_kw.return_value = []
    
    mock_server_proxy.side_effect = [mock_common, mock_models]
    
    client.search_read('res.partner', [])
    assert client.uid == 1

@patch('xmlrpc.client.ServerProxy')
def test_create_record(mock_server_proxy, valid_env):
    client = odoo_client.OdooClient()
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 1
    mock_models = MagicMock()
    mock_models.execute_kw.return_value = 42  # New record ID
    mock_server_proxy.side_effect = [mock_common, mock_models]

    client.connect()
    new_id = client.create('res.partner', [{'name': 'New Partner'}])
    
    assert new_id == 42
    mock_models.execute_kw.assert_called_with(
        "test_db", 1, "admin",
        "res.partner", "create", [[{'name': 'New Partner'}]], {}
    )

@patch('xmlrpc.client.ServerProxy')
def test_write_record(mock_server_proxy, valid_env):
    client = odoo_client.OdooClient()
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 1
    mock_models = MagicMock()
    mock_models.execute_kw.return_value = True
    mock_server_proxy.side_effect = [mock_common, mock_models]

    client.connect()
    result = client.write('res.partner', [42], {'name': 'Updated Partner'})
    
    assert result is True
    mock_models.execute_kw.assert_called_with(
        "test_db", 1, "admin",
        "res.partner", "write", [[42], {'name': 'Updated Partner'}], {}
    )

@patch('xmlrpc.client.ServerProxy')
def test_unlink_record(mock_server_proxy, valid_env):
    client = odoo_client.OdooClient()
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 1
    mock_models = MagicMock()
    mock_models.execute_kw.return_value = True
    mock_server_proxy.side_effect = [mock_common, mock_models]

    client.connect()
    result = client.unlink('res.partner', [42])
    
    assert result is True
    mock_models.execute_kw.assert_called_with(
        "test_db", 1, "admin",
        "res.partner", "unlink", [[42]], {}
    )
