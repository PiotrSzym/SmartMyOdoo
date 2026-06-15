"""S1.4 (dowód): db_manager NIE loguje master_pwd (response.text echo'wał sekret)."""

import logging

from smartmyodoo.swarm.db_manager import OdooDBManager


class _FakeResp:
    status_code = 500
    text = "Database duplication error: master_pwd=SUPER_SECRET_PWD invalid"


def test_clone_error_does_not_leak_master_pwd(caplog, monkeypatch):
    mgr = OdooDBManager("http://odoo", "SUPER_SECRET_PWD")
    monkeypatch.setattr(mgr.client, "post", lambda *a, **k: _FakeResp())

    with caplog.at_level(logging.ERROR):
        ok = mgr.duplicate_database("prod", "prod_scratch")

    assert ok is False
    assert "SUPER_SECRET_PWD" not in caplog.text  # sekret NIE trafił do logów
    assert "500" in caplog.text  # status owszem
