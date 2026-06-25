"""WRITE-01 T1: wykonanie pojedynczej propozycji na Odoo (execute_proposal_by_id).

Domyka lukę E-W003 (execute nigdy nie wołane). Testy z MOCKIEM Odoo — nie dotykają
prawdziwej bazy ani prod Odoo. Sprawdzają mapowanie method→create/write/unlink,
idempotencję (executed) i guardy (rejected / nieznana metoda).
"""

import json
from smartmyodoo.mcp import server


class _FakeOdoo:
    def __init__(self):
        self.calls = []

    def create(self, m, vals):
        self.calls.append(("create", m, vals))

    def write(self, m, ids, vals):
        self.calls.append(("write", m, ids, vals))

    def unlink(self, m, ids):
        self.calls.append(("unlink", m, ids))


class _FakeProp:
    def __init__(self, status="approved", method="create", odoo_model="res.partner", values=None):
        self.id = "p1"
        self.status = status
        self.method = method
        self.odoo_model = odoo_model
        self.values = values if values is not None else json.dumps({"record_ids": [], "values": {}})
        self.workspace_id = "ws"


class _FakeQuery:
    def __init__(self, prop):
        self._p = prop

    def filter(self, *a, **k):
        return self

    def first(self):
        return self._p


class _FakeSession:
    def __init__(self, prop):
        self._p = prop
        self.committed = False

    def query(self, *a, **k):
        return _FakeQuery(self._p)

    def commit(self):
        self.committed = True

    def close(self):
        pass


def _wire(monkeypatch, prop):
    sess = _FakeSession(prop)
    odoo = _FakeOdoo()
    monkeypatch.setattr(server.shadow_mode, "SessionLocal", lambda: sess)
    monkeypatch.setattr(server, "get_odoo_client", lambda ws: odoo)
    return sess, odoo


def test_apply_create(monkeypatch):
    prop = _FakeProp(method="create", odoo_model="res.partner",
                     values=json.dumps({"record_ids": [], "values": {"name": "Test"}}))
    _, odoo = _wire(monkeypatch, prop)
    res = server.execute_proposal_by_id("p1", "ws")
    assert res["success"] and res["status"] == "executed"
    assert odoo.calls == [("create", "res.partner", [{"name": "Test"}])]
    assert prop.status == "executed"


def test_apply_update(monkeypatch):
    prop = _FakeProp(method="update", odoo_model="project.task",
                     values=json.dumps({"record_ids": [6706], "values": {"description": "x"}}))
    _, odoo = _wire(monkeypatch, prop)
    res = server.execute_proposal_by_id("p1", "ws")
    assert res["success"]
    assert odoo.calls == [("write", "project.task", [6706], {"description": "x"})]


def test_apply_delete(monkeypatch):
    prop = _FakeProp(method="delete", odoo_model="res.partner",
                     values=json.dumps({"record_ids": [99], "values": {}}))
    _, odoo = _wire(monkeypatch, prop)
    res = server.execute_proposal_by_id("p1", "ws")
    assert res["success"]
    assert odoo.calls == [("unlink", "res.partner", [99])]


def test_apply_idempotent_when_executed(monkeypatch):
    prop = _FakeProp(status="executed")
    _, odoo = _wire(monkeypatch, prop)
    res = server.execute_proposal_by_id("p1", "ws")
    assert res["success"] and res.get("already") is True
    assert odoo.calls == []  # nic nie wykonuje drugi raz


def test_apply_blocked_when_rejected(monkeypatch):
    prop = _FakeProp(status="rejected")
    _, odoo = _wire(monkeypatch, prop)
    res = server.execute_proposal_by_id("p1", "ws")
    assert res["success"] is False and res["error"] == "rejected"
    assert odoo.calls == []


def test_apply_unknown_method(monkeypatch):
    prop = _FakeProp(method="frobnicate")
    _, odoo = _wire(monkeypatch, prop)
    res = server.execute_proposal_by_id("p1", "ws")
    assert res["success"] is False and "unknown_method" in res["error"]
    assert odoo.calls == []
