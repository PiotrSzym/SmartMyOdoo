"""TRUST-01 T3: version-aware connector (mock XML-RPC).

Cel (US-T3, decyzje D3/D4): connector był ŚLEPY na wersję Odoo — connect()
robił tylko authenticate(). Pola hardkodowane pękają między 16/19
(np. analytic_account_id tylko v16, billing_type tylko v19).

Wymagania:
  - connect() zapisuje version_info (common.version()) i major (int).
  - fields_get cache'owany per (workspace, model) — nie odpytuje co request.
  - pole spoza wersji => FAIL LOUD (wyjątek), NIGDY ciche puste (D4).
"""

import sys
import types
from unittest.mock import MagicMock

import pytest

from smartmyodoo.mcp.odoo_client import OdooClient, set_odoo_creds


@pytest.fixture
def creds():
    set_odoo_creds(
        {
            "default": {
                "url": "https://odoo.test",
                "db": "testdb",
                "username": "u",
                "password": "p",
            }
        }
    )
    yield
    set_odoo_creds(None)


def _make_proxy_factory(version_info, fields_by_model, uid=7):
    """Buduje fabrykę ServerProxy: common (authenticate+version) i object (execute_kw)."""
    calls = {"version": 0, "fields_get": 0}

    common = MagicMock()
    common.authenticate.return_value = uid
    common.version.return_value = version_info

    obj = MagicMock()

    def execute_kw(db, uid_, pwd, model, method, args, kw=None):
        if method == "fields_get":
            calls["fields_get"] += 1
            return {f: {"type": "char"} for f in fields_by_model.get(model, [])}
        if method == "search_read":
            return [{"id": 1}]
        if method == "search_count":
            return 1
        return None

    obj.execute_kw.side_effect = execute_kw

    def factory(url):
        if url.endswith("/common"):
            # licznik version() z poziomu common
            orig = common.version
            return common
        return obj

    return factory, calls


def test_connect_sets_version_info(creds, monkeypatch):
    factory, _ = _make_proxy_factory(
        {"server_version": "19.0", "server_version_info": [19, 0, 0, "final", 0]},
        {"project.task": ["id", "name", "billing_type"]},
    )
    monkeypatch.setattr("xmlrpc.client.ServerProxy", factory)

    c = OdooClient("default")
    c.connect()

    assert c.version_info is not None
    assert c.version_info.get("server_version") == "19.0"
    assert c.major == 19


def test_fields_get_cached_per_model(creds, monkeypatch):
    factory, calls = _make_proxy_factory(
        {"server_version": "16.0", "server_version_info": [16, 0, 0, "final", 0]},
        {"project.task": ["id", "name", "analytic_account_id"]},
    )
    monkeypatch.setattr("xmlrpc.client.ServerProxy", factory)

    c = OdooClient("default")
    c.connect()

    f1 = c.get_available_fields("project.task")
    f2 = c.get_available_fields("project.task")
    assert "analytic_account_id" in f1
    assert f1 == f2
    # fields_get odpytane RAZ (cache per model), nie 2x
    assert calls["fields_get"] == 1


def test_missing_field_fails_loud(creds, monkeypatch):
    # v19 nie ma 'analytic_account_id' (to pole v16) — zapytanie o nie ma huknąć,
    # NIE zwrócić cicho pustego (D4).
    factory, _ = _make_proxy_factory(
        {"server_version": "19.0", "server_version_info": [19, 0, 0, "final", 0]},
        {"project.task": ["id", "name", "billing_type"]},
    )
    monkeypatch.setattr("xmlrpc.client.ServerProxy", factory)

    c = OdooClient("default")
    c.connect()

    from smartmyodoo.mcp.odoo_client import OdooFieldError

    with pytest.raises(OdooFieldError):
        c.validate_fields("project.task", ["id", "name", "analytic_account_id"])


def test_validate_fields_passes_for_existing(creds, monkeypatch):
    factory, _ = _make_proxy_factory(
        {"server_version": "19.0", "server_version_info": [19, 0, 0, "final", 0]},
        {"project.task": ["id", "name", "billing_type"]},
    )
    monkeypatch.setattr("xmlrpc.client.ServerProxy", factory)

    c = OdooClient("default")
    c.connect()
    # nie rzuca — wszystkie pola istnieją
    c.validate_fields("project.task", ["id", "name", "billing_type"])


def test_version_detection_non_fatal(creds, monkeypatch):
    # Gdy common.version() padnie, connect() NIE może się wywalić (auth ważniejsze).
    factory, _ = _make_proxy_factory(
        {}, {"project.task": ["id"]},
    )

    def boom():
        raise RuntimeError("no version endpoint")

    monkeypatch.setattr("xmlrpc.client.ServerProxy", factory)
    c = OdooClient("default")
    # podmień version na rzucający po zbudowaniu proxy
    import xmlrpc.client

    orig = xmlrpc.client.ServerProxy

    def patched(url):
        proxy = orig(url)
        if url.endswith("/common"):
            proxy.version.side_effect = boom
        return proxy

    monkeypatch.setattr("xmlrpc.client.ServerProxy", patched)
    assert c.connect() is True
    assert c.major is None  # nieznana wersja, ale brak crasha
