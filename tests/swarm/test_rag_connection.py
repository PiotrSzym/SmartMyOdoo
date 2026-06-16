"""Regresja: pusta (ale realna) baza LanceDB NIE może być raportowana jako 'degraded'.

Bug: `degraded`/guardy używały truthiness (`not self._table`) — pusta tabela (len==0)
była mylona z brakiem połączenia (tryb Mock). Powinno być `is None`.
Pomijany, gdy zależności RAG (lancedb/sentence-transformers) nie są zainstalowane.
"""

import pytest

lancedb = pytest.importorskip("lancedb")  # skip gdy brak zależności
pytest.importorskip("sentence_transformers")


def test_empty_real_db_is_not_degraded(tmp_path):
    from smartmyodoo.swarm.brain.lancedb_client import LanceDBClient

    client = LanceDBClient(db_path=str(tmp_path / "lancedb_test"))
    # realna baza + model → NIE degraded, nawet gdy tabela pusta (0 wierszy)
    if client._table is None or client._model is None:
        pytest.skip("model/baza niedostępne w tym środowisku (offline)")
    assert client.degraded is False
    # pusta baza: search zwraca [] (brak wiedzy), bez crasha i bez fabrykacji
    assert client.search("cokolwiek", top_k=3) == []


def test_degraded_uses_is_none_not_truthiness():
    """Statyczna gwarancja: kod sprawdza `is None`, nie `not self._table`."""
    import pathlib

    src = (
        pathlib.Path(__file__).resolve().parents[2]
        / "smartmyodoo"
        / "swarm"
        / "brain"
        / "lancedb_client.py"
    ).read_text(encoding="utf-8")
    assert "self._table is None or self._model is None" in src
    assert "not self._table or not self._model" not in src
