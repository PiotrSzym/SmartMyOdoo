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


def test_tool_path_shares_one_odoo_client_module(monkeypatch):
    """KEY-02-3 regresja: narzędzia czatu (mcp.server) MUSZĄ używać tego samego
    obiektu modułu odoo_client co chat.set_odoo_creds — inaczej ContextVar (creds
    ze Skarbca) nie dociera do narzędzi. Wcześniej server importował przez sys.path
    ('odoo_client'), tworząc DRUGI moduł z własną, pustą ContextVar."""
    for k in ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"]:
        monkeypatch.delenv(k, raising=False)
    import smartmyodoo.mcp.odoo_client as pkgmod
    from smartmyodoo.mcp import server

    assert server.get_odoo_client is pkgmod.get_odoo_client

    set_odoo_creds(
        {
            "default": {
                "url": "https://vault",
                "db": "vdb",
                "username": "vu",
                "password": "vp",
            }
        }
    )
    try:
        c = server.get_odoo_client("default")
        assert c.url == "https://vault" and c.db == "vdb"
    finally:
        set_odoo_creds(None)


def test_get_odoo_client_default_not_stale_singleton(monkeypatch):
    """Fabryka 'default' MUSI budować świeży klient (czyta bieżącą ContextVar),
    a nie zwracać singletona z czasu importu (puste creds)."""
    for k in ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"]:
        monkeypatch.delenv(k, raising=False)
    from smartmyodoo.mcp.odoo_client import get_odoo_client

    set_odoo_creds(
        {"default": {"url": "u1", "db": "d1", "username": "x", "password": "p"}}
    )
    try:
        assert get_odoo_client("default").url == "u1"
    finally:
        set_odoo_creds(None)


def test_search_records_anonymizes_values_not_serialized_json():
    """PII regresja: anonimizacja musi działać na WARTOŚCIACH pól, nie na zserializowanym
    JSON (Presidio na blobie JSON psuł strukturę → json.loads padał, count=None)."""
    src = (
        Path(__file__).resolve().parents[1] / "smartmyodoo" / "mcp" / "server.py"
    ).read_text(encoding="utf-8")
    # nie wolno anonimizować całego result_str
    assert "anonymize(\n                result_str" not in src
    assert ".anonymize(result_str" not in src
    # zwracamy strukturę bezpośrednio, anonimizacja per wartość string
    assert 'return {"records": records, "count": len(records)}' in src
