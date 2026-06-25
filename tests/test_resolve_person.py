"""TRUST-04 T1: serwerowe rozpoznanie osoby (resolve_person_records).

/qa LIVE: „dla piotr sz" trafiało w złego Piotra, bo LLM widzi zamaskowane nazwiska.
resolve_person szuka SERWEROWO po realnych nazwach w res.users i zwraca REALNE uid
(do filtra) + ZAMASKOWANE nazwy (deanonymize pokaże je userowi przy liście wyboru).
"""

from smartmyodoo.mcp import server


class _FakeOdoo:
    def __init__(self, rows):
        self._rows = rows

    def search_read(self, model, domain, fields, limit):
        assert model == "res.users"
        return self._rows


def test_single_match_returns_real_uid(monkeypatch):
    monkeypatch.setattr(server, "get_odoo_client", lambda ws: _FakeOdoo([{"id": 42, "name": "Piotr Szymełyniec"}]))
    monkeypatch.setattr(server, "is_pii_enabled", lambda ws: False)
    out = server.resolve_person_records("piotr sz", "myodooTest")
    assert out["count"] == 1
    assert out["users"][0]["uid"] == 42


def test_multi_match(monkeypatch):
    monkeypatch.setattr(server, "get_odoo_client", lambda ws: _FakeOdoo([
        {"id": 42, "name": "Piotr Szymełyniec"}, {"id": 101, "name": "Piotr Kalita"}
    ]))
    monkeypatch.setattr(server, "is_pii_enabled", lambda ws: False)
    out = server.resolve_person_records("piotr", "ws")
    assert out["count"] == 2
    assert {u["uid"] for u in out["users"]} == {42, 101}


def test_empty_query():
    assert server.resolve_person_records("", "ws")["count"] == 0
    assert server.resolve_person_records("   ", "ws")["count"] == 0


def test_uid_real_but_name_masked(monkeypatch):
    """Bezpieczeństwo (D4): uid REALNE (do filtra), nazwa ZAMASKOWANA (do chmury)."""
    class _Pii:
        def anonymize(self, t, workspace_id="default"):
            return "<PERSON_1>"

    monkeypatch.setattr(server, "get_odoo_client", lambda ws: _FakeOdoo([{"id": 42, "name": "Piotr Szymełyniec"}]))
    monkeypatch.setattr(server, "is_pii_enabled", lambda ws: True)
    monkeypatch.setattr(server, "get_pii_middleware", lambda: _Pii())
    out = server.resolve_person_records("piotr", "ws")
    assert out["users"][0]["uid"] == 42          # uid prawdziwe
    assert out["users"][0]["name"] == "<PERSON_1>"  # nazwa zamaskowana
    assert "login" not in out["users"][0]         # e-mail nie wychodzi do chmury
