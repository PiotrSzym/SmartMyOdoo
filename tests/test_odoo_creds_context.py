"""KEY-02-3 / ADR-007: OdooClient bierze poświadczenia ze Skarbca (ContextVar), nie z ENV."""

from pathlib import Path

from smartmyodoo.mcp.odoo_client import OdooClient, set_odoo_creds


def test_context_creds_take_precedence(monkeypatch):
    # ENV ustawione, ale kontekst (Skarbiec) ma wygrać
    monkeypatch.setenv("ODOO_URL", "http://env-url")
    monkeypatch.setenv("ODOO_DB", "env_db")
    monkeypatch.setenv("ODOO_USERNAME", "env_user")
    monkeypatch.setenv("ODOO_PASSWORD", "env_pass")
    set_odoo_creds(
        {
            "default": {
                "url": "https://vault-url",
                "db": "vault_db",
                "username": "vault_user",
                "password": "vault_pass",
            }
        }
    )
    try:
        c = OdooClient("default")
        assert c.url == "https://vault-url"
        assert c.db == "vault_db"
        assert c.username == "vault_user"
        assert c.password == "vault_pass"
    finally:
        set_odoo_creds(None)


def test_env_fallback_without_context(monkeypatch):
    set_odoo_creds(None)
    monkeypatch.setenv("ODOO_URL", "http://env-url")
    monkeypatch.setenv("ODOO_DB", "env_db")
    monkeypatch.setenv("ODOO_USERNAME", "env_user")
    monkeypatch.setenv("ODOO_PASSWORD", "env_pass")
    c = OdooClient("default")
    assert c.url == "http://env-url" and c.db == "env_db"


def test_per_workspace_creds(monkeypatch):
    for k in ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"]:
        monkeypatch.delenv(k, raising=False)
    set_odoo_creds({"7": {"url": "u7", "db": "d7", "username": "x", "password": "p"}})
    try:
        assert OdooClient("7").url == "u7"
        # workspace bez wpisu → brak (None), nie cudze dane
        assert OdooClient("nieistnieje").url is None
    finally:
        set_odoo_creds(None)


def test_chat_injects_odoo_creds():
    src = (
        Path(__file__).resolve().parents[1] / "smartmyodoo" / "api_routers" / "chat.py"
    ).read_text(encoding="utf-8")
    assert "_inject_odoo_creds(" in src
    assert "set_odoo_creds(" in src
