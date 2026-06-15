"""K3 (KEY-01): logowanie czasu używa Odoo typu 'timesheet', reszta 'data' (z fallbackiem)."""

import smartmyodoo.api  # noqa: F401  — inicjuje łańcuch importów we właściwej kolejności
from smartmyodoo.api_routers.workspaces import _resolve_odoo_creds


def test_timesheet_prefers_timesheet_type():
    vault = {
        "dane": {
            "type": "odoo_data",
            "workspace_id": "7",
            "url": "DATA",
            "db": "d",
            "login": "l",
        },
        "czas": {
            "type": "odoo_timesheet",
            "workspace_id": "7",
            "url": "TIMESHEET",
            "db": "d",
            "login": "l",
        },
    }
    assert _resolve_odoo_creds(vault, "7", prefer_timesheet=True)["url"] == "TIMESHEET"
    assert _resolve_odoo_creds(vault, "7", prefer_timesheet=False)["url"] == "DATA"


def test_timesheet_falls_back_to_data_when_no_timesheet_cred():
    vault = {
        "dane": {
            "type": "odoo_data",
            "workspace_id": "7",
            "url": "DATA",
            "db": "d",
            "login": "l",
        }
    }
    assert _resolve_odoo_creds(vault, "7", prefer_timesheet=True)["url"] == "DATA"


def test_legacy_name_fallback_for_incomplete_secret():
    # niekompletny stary sekret (brak login) → resolver odrzuca → name-fallback zwraca surowy dict
    vault = {"default_ODOO": {"url": "LEGACY", "db": "d"}}
    creds = _resolve_odoo_creds(vault, "default", prefer_timesheet=False)
    assert creds["url"] == "LEGACY"
