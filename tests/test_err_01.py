"""ERR-01: konkretne błędy Odoo zamiast „szczegóły w logach” + retry zimnego startu.

Pokrywa:
- T1: classify_odoo_error mapuje typ wyjątku na konkretny, actionable komunikat;
       żaden nie zawiera „szczegóły w logach”.
- T2: OdooClient.connect() ponawia raz przy błędzie przejściowym (staging wake).
- reguła: ERROR_REPORT_RULE w prompcie (model cytuje błąd, nie zgaduje).
"""

import socket
import xmlrpc.client

import pytest

from smartmyodoo.mcp.odoo_errors import classify_odoo_error
from smartmyodoo.mcp.odoo_client import OdooFieldError
from smartmyodoo.swarm.executor import build_system_prompt, ERROR_REPORT_RULE


# ── T1: klasyfikacja ──
def test_brak_konfiguracji():
    msg = classify_odoo_error(ValueError("Brak konfiguracji Odoo w zmiennych środowiskowych."))
    assert "Brak konfiguracji Odoo" in msg and "Skarb" in msg


def test_autoryzacja_sugeruje_staging_i_creds():
    msg = classify_odoo_error(
        PermissionError("Błąd autoryzacji do Odoo."), workspace_id="myodooTest"
    )
    assert "autoryzacji" in msg.lower()
    assert "staging" in msg.lower() and ("odśwież" in msg.lower() or "wygas" in msg.lower())
    assert "myodooTest" in msg  # nazwa przestrzeni w komunikacie


def test_timeout():
    assert "timeout" in classify_odoo_error(socket.timeout("timed out")).lower()


def test_fault_access_error():
    f = xmlrpc.client.Fault(1, "odoo.exceptions.AccessError: You are not allowed to access 'crm.lead'")
    msg = classify_odoo_error(f)
    assert "uprawnie" in msg.lower() and "AccessError" in msg


def test_fault_validation():
    f = xmlrpc.client.Fault(1, "odoo.exceptions.ValidationError: Pole wymagane")
    assert "walidacj" in classify_odoo_error(f).lower()


def test_connection_unreachable():
    assert "nieosiągalne" in classify_odoo_error(ConnectionError("refused")).lower()


def test_field_error_passthrough():
    msg = classify_odoo_error(OdooFieldError("Pola ['x'] nie istnieją w modelu 'crm.lead' (Odoo 19)."))
    assert "nie istnieją w modelu" in msg


def test_fallback_shows_type():
    msg = classify_odoo_error(RuntimeError("coś dziwnego"))
    assert "RuntimeError" in msg


def test_no_generic_log_message_anywhere():
    """Żaden sklasyfikowany błąd nie spycha usera do „szczegóły w logach”."""
    for exc in [
        ValueError("Brak konfiguracji Odoo w zmiennych środowiskowych."),
        PermissionError("Błąd autoryzacji do Odoo."),
        socket.timeout("timed out"),
        xmlrpc.client.Fault(1, "AccessError"),
        ConnectionError("refused"),
        RuntimeError("x"),
    ]:
        assert "szczegóły w logach" not in classify_odoo_error(exc).lower()


# ── reguła w prompcie ──
def test_error_report_rule_in_prompt():
    p = build_system_prompt("Bazowy").lower()
    assert ERROR_REPORT_RULE.strip()[:15].lower() in p
    assert "nie wymyślaj" in p  # anty-zgadywanie przyczyn


# ── T2: retry zimnego startu ──
def test_connect_retries_on_transient(monkeypatch):
    from smartmyodoo.mcp import odoo_client as oc

    monkeypatch.setattr(oc.time, "sleep", lambda *_: None)  # bez realnej pauzy

    class FakeCommon:
        def __init__(self):
            self.n = 0

        def authenticate(self, *a, **k):
            self.n += 1
            if self.n == 1:
                raise socket.timeout("waking up")  # zimny start
            return 42  # druga próba OK

        def version(self):
            return {"server_version": "19.0+e", "server_version_info": [19, 0]}

    fake_common = FakeCommon()

    def fake_proxy(url, *a, **k):
        return fake_common if url.endswith("/common") else object()

    monkeypatch.setattr(oc.xmlrpc.client, "ServerProxy", fake_proxy)

    client = oc.OdooClient("default")
    client.url, client.db, client.username, client.password = "http://x", "db", "u", "p"
    assert client.connect() is True
    assert client.uid == 42
    assert fake_common.n == 2  # ponowiono dokładnie raz


def test_connect_auth_fail_after_retry_raises(monkeypatch):
    from smartmyodoo.mcp import odoo_client as oc

    monkeypatch.setattr(oc.time, "sleep", lambda *_: None)

    class FakeCommon:
        def authenticate(self, *a, **k):
            return False  # stale False = złe creds (nie zimny start)

        def version(self):
            return {}

    monkeypatch.setattr(
        oc.xmlrpc.client, "ServerProxy", lambda url, *a, **k: FakeCommon()
    )
    client = oc.OdooClient("default")
    client.url, client.db, client.username, client.password = "http://x", "db", "u", "p"
    with pytest.raises(PermissionError):
        client.connect()
