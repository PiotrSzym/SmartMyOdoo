"""AZURE-01 T2 — test DOWODOWY: sekret ODOO_DATA z samym `api_key` (bez hasła)
uwierzytelnia SMO na OBU ścieżkach — chat (`_inject_odoo_creds`) i workspace
(`_resolve_odoo_creds`) — podając klucz API jako 3. argument `authenticate`.

Dowód luki (RED przed T1 na ścieżce workspace): bez przeniesienia `api_key`
w `_resolve_odoo_creds` connector dostaje pusty sekret i pada na „Missing credentials".
Po T1 (GREEN): klucz API = poświadczenie; brak hasła NIE blokuje connectu; klucz
NIE pojawia się w logach.

Wzorzec: mock `xmlrpc.client.ServerProxy` (tests/test_odoo_creds_context.py styl
ContextVar). Zero mocków udających logikę — mockujemy WYŁĄCZNIE granicę sieci (RPC).
"""

import logging

import xmlrpc.client

import smartmyodoo.api  # noqa: F401  — inicjuje łańcuch importów we właściwej kolejności

API_KEY = "odoo-apikey-SECRET-do-not-log-9f3c1"


class _FakeCommon:
    """Podszywa się pod /xmlrpc/2/common — rejestruje argumenty authenticate()."""

    def __init__(self, recorder):
        self._rec = recorder

    def authenticate(self, db, login, secret, opts):
        self._rec["authenticate"] = (db, login, secret, opts)
        return 7  # niezerowy uid = sukces

    def version(self):
        return {"server_version_info": [16, 0, 0, "final", 0]}


class _FakeModels:
    def execute_kw(self, *args, **kwargs):
        return []


def _proxy_factory(recorder):
    """Fabryka ServerProxy: /common → _FakeCommon, /object → _FakeModels.
    Rejestruje URL-e konstrukcji, by udowodnić że klucz nie trafia do transportu."""

    def _factory(url, *args, **kwargs):
        recorder.setdefault("proxy_urls", []).append(url)
        if url.rstrip("/").endswith("/common"):
            return _FakeCommon(recorder)
        return _FakeModels()

    return _factory


def _odoo_data_secret_with_apikey():
    """Sekret ODOO_DATA: ma api_key, hasło PUSTE (scenariusz docelowy AZURE-01)."""
    return {
        "gfit_key": {
            "type": "odoo_data",
            "workspace_id": "default",
            "url": "https://gfit.com.pl",
            "db": "gfitdb",
            "login": "svc_smo",
            "api_key": API_KEY,
            "password": "",
        }
    }


def _odoo_timesheet_secret_with_apikey():
    """Sekret ODOO_TIMESHEET: ma api_key, hasło PUSTE (ścieżka logowania czasu)."""
    return {
        "gfit_timesheet": {
            "type": "odoo_timesheet",
            "workspace_id": "default",
            "url": "https://gfit.com.pl",
            "db": "gfitdb",
            "login": "svc_smo",
            "api_key": API_KEY,
            "password": "",
        }
    }


def test_workspace_path_authenticates_with_api_key(monkeypatch, caplog):
    """Ścieżka workspace/timesheet: _resolve_odoo_creds → OdooProjectConnector
    → authenticate(db, login, <api_key>, {}). RED przed T1 (Missing credentials)."""
    rec = {}
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _proxy_factory(rec))

    from smartmyodoo.api_routers.workspaces import _resolve_odoo_creds
    from smartmyodoo.core.odoo_connector import OdooProjectConnector

    creds = _resolve_odoo_creds(_odoo_data_secret_with_apikey(), "default")

    with caplog.at_level(logging.DEBUG):
        OdooProjectConnector(creds)

    assert "authenticate" in rec, "connector nie uwierzytelnił się (luka T1?)"
    db, login, secret, opts = rec["authenticate"]
    assert secret == API_KEY, "3. argument authenticate MUSI być kluczem API"
    assert login == "svc_smo"
    assert db == "gfitdb"
    # Klucz NIE może wyciec do logów (Sekcja D / ART.2)
    assert API_KEY not in caplog.text
    # ani do argumentów konstrukcji ServerProxy (tylko URL)
    assert all(API_KEY not in u for u in rec.get("proxy_urls", []))


def test_chat_path_authenticates_with_api_key(monkeypatch, caplog):
    """Ścieżka chat/narzędzia: _inject_odoo_creds → set_odoo_creds (ContextVar)
    → OdooClient.connect() → authenticate(db, username, <api_key>, {})."""
    for k in ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    rec = {}
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _proxy_factory(rec))

    from smartmyodoo.api_routers.chat import _inject_odoo_creds
    from smartmyodoo.mcp.odoo_client import OdooClient, set_odoo_creds

    _inject_odoo_creds(_odoo_data_secret_with_apikey(), "default")
    try:
        client = OdooClient("default")
        with caplog.at_level(logging.DEBUG):
            client.connect()
    finally:
        set_odoo_creds(None)

    assert "authenticate" in rec
    db, username, secret, opts = rec["authenticate"]
    assert secret == API_KEY, "3. argument authenticate MUSI być kluczem API"
    assert username == "svc_smo"
    assert db == "gfitdb"
    assert API_KEY not in caplog.text
    assert all(API_KEY not in u for u in rec.get("proxy_urls", []))


def test_resolve_odoo_creds_carries_key_in_password_slot():
    """T1 jednostkowy: dict zwrócony przez _resolve_odoo_creds niesie klucz API
    w miejscu hasła (prefer api_key nad password, spójnie z chat.py:56),
    i zachowuje `login` (klucz czytany przez connector, nie `username`)."""
    from smartmyodoo.api_routers.workspaces import _resolve_odoo_creds

    creds = _resolve_odoo_creds(_odoo_data_secret_with_apikey(), "default")
    # connector czyta: credentials.get("api_key") or credentials.get("password")
    effective_secret = creds.get("api_key") or creds.get("password")
    assert effective_secret == API_KEY
    assert creds["login"] == "svc_smo"
    assert "username" not in creds  # connector czyta 'login', mapowanie musi się zgadzać


def test_password_used_when_no_api_key():
    """Regresja: sekret bez api_key (klasyczne hasło) nadal działa — nie zepsuliśmy
    ścieżki hasłowej."""
    from smartmyodoo.api_routers.workspaces import _resolve_odoo_creds

    vault = {
        "classic": {
            "type": "odoo_data",
            "workspace_id": "default",
            "url": "https://gfit.com.pl",
            "db": "gfitdb",
            "login": "svc_smo",
            "password": "plain-pass-123",
        }
    }
    creds = _resolve_odoo_creds(vault, "default")
    effective_secret = creds.get("api_key") or creds.get("password")
    assert effective_secret == "plain-pass-123"


# ── AZURE-01 Sekcja B2 (follow-up po bramkach /audyt+/sec) ───────────────────


def test_legacy_odoo_secret_carries_api_key():
    """T6 (F-1, /audyt): parytet api_key w gałęzi LEGACY resolvera.

    Sekret legacy `<ws>_ODOO` (bez pola `type`) z samym `api_key` i pustym
    `password` MUSI rozwiązywać się z kluczem w `.api_key` — parytet z nowym
    formatem (D2: „KAŻDA ścieżka akceptuje sekret z samym kluczem").
    RED przed fixem: legacy gałąź budowała `Credential` BEZ `api_key` → `None`.
    """
    from smartmyodoo.vault.resolver import to_credential

    raw = {
        "url": "https://gfit.com.pl",
        "db": "gfitdb",
        "login": "svc_smo",
        "api_key": API_KEY,
        "password": "",
    }
    cred = to_credential("default_ODOO", raw)

    assert cred is not None, "legacy _ODOO powinien się sklasyfikować jako ODOO_DATA"
    assert cred.type.value == "odoo_data"
    assert cred.workspace_id == "default"
    assert cred.login == "svc_smo"
    # Sedno T6: klucz API musi przetrwać rozwiązanie legacy (RED: None przed fixem)
    assert cred.api_key == API_KEY


def test_timesheet_path_authenticates_with_api_key(monkeypatch, caplog):
    """T7 (F-3, /audyt): ścieżka timesheet uwierzytelnia się kluczem API.

    `_resolve_odoo_creds(prefer_timesheet=True)` z sekretem `type=odoo_timesheet`
    + `api_key` (bez hasła) przenosi klucz w slot `password`
    (`cred.api_key or cred.password or ""`) → `OdooProjectConnector` woła
    `authenticate(db, login, <api_key>, {})`. Klucz nie wycieka do logów/URL-i.
    """
    rec = {}
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _proxy_factory(rec))

    from smartmyodoo.api_routers.workspaces import _resolve_odoo_creds
    from smartmyodoo.core.odoo_connector import OdooProjectConnector

    creds = _resolve_odoo_creds(
        _odoo_timesheet_secret_with_apikey(), "default", prefer_timesheet=True
    )
    # dict niesie klucz w slocie `password` (kontrakt konsumenta connectora)
    assert (creds.get("api_key") or creds.get("password")) == API_KEY
    assert creds["login"] == "svc_smo"

    with caplog.at_level(logging.DEBUG):
        OdooProjectConnector(creds)

    assert "authenticate" in rec, "connector nie uwierzytelnił się na ścieżce timesheet"
    db, login, secret, opts = rec["authenticate"]
    assert secret == API_KEY, "3. argument authenticate MUSI być kluczem API"
    assert login == "svc_smo"
    assert db == "gfitdb"
    # Klucz NIE może wyciec do logów ani do argumentów konstrukcji ServerProxy
    assert API_KEY not in caplog.text
    assert all(API_KEY not in u for u in rec.get("proxy_urls", []))
