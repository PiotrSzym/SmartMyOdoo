import pytest
from unittest.mock import patch
from smartmyodoo.swarm.vault_auth import VaultAuthProvider, PipelineCredentials
from smartmyodoo.swarm.pipeline import PipelineError
from smartmyodoo.vault import vault


@patch("smartmyodoo.swarm.vault_auth.vault.get_vault_key_from_pin")
@patch("smartmyodoo.swarm.vault_auth.vault.load_vault")
def test_vault_auth_happy_path(mock_load_vault, mock_get_vk):
    mock_get_vk.return_value = b"mock_key"
    mock_load_vault.return_value = {
        "ODOO": {
            "url": "http://test:8069",
            "db": "test_db",
            "login": "admin",
            "password": "supersecret",
        },
        "OPENROUTER": {"api_key": "sk-or-v1-123"},
    }

    creds = VaultAuthProvider.authenticate("1111")
    assert isinstance(creds, PipelineCredentials)
    assert creds.odoo_url == "http://test:8069"
    assert creds.odoo_db == "test_db"
    assert creds.odoo_login == "admin"
    assert creds.odoo_password == "supersecret"
    assert creds.openrouter_key == "sk-or-v1-123"


@patch("smartmyodoo.swarm.vault_auth.vault.get_vault_key_from_pin")
def test_vault_auth_invalid_pin(mock_get_vk):
    mock_get_vk.side_effect = ValueError("Invalid PIN")

    with pytest.raises(PipelineError) as exc_info:
        VaultAuthProvider.authenticate("9999")
    assert "AUTH failed" in str(exc_info.value)


@patch("smartmyodoo.swarm.vault_auth.vault.get_vault_key_from_pin")
@patch("smartmyodoo.swarm.vault_auth.vault.load_vault")
def test_vault_auth_missing_secrets(mock_load_vault, mock_get_vk):
    mock_get_vk.return_value = b"mock_key"
    mock_load_vault.return_value = {
        "ODOO": {
            "url": "http://test:8069",
            # Brak reszty
        }
    }

    with pytest.raises(PipelineError) as exc_info:
        VaultAuthProvider.authenticate("1111")
    assert "Missing required secrets" in str(exc_info.value)


@patch("smartmyodoo.swarm.vault_auth.vault.get_vault_key_from_pin")
def test_vault_auth_vault_error(mock_get_vk):
    mock_get_vk.side_effect = vault.VaultDecryptionError("Corrupted file")

    with pytest.raises(PipelineError) as exc_info:
        VaultAuthProvider.authenticate("1111")
    assert "AUTH failed" in str(exc_info.value)
