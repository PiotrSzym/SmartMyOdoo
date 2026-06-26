"""MEM-01: lekka pamięć historii (SQLite FTS5) — przypominanie chatów i sprintów.

Testy są LEKKIE (bez ML, bez torcha) — to cała idea: pamięć działa wszędzie, gdzie
jest sqlite z FTS5 (Python wbudowany), także na Py3.14 i u każdego, kto sklonuje repo.
"""

import sqlite3

import pytest

from smartmyodoo.core import memory_search as ms


@pytest.fixture
def db(tmp_path):
    """Tymczasowa baza z tabelą chat_messages + kilkoma wiadomościami."""
    path = str(tmp_path / "t.db")
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, workspace_id TEXT, "
        "session_id TEXT, role TEXT, content TEXT, metadata_json TEXT, created_at TEXT)"
    )
    rows = [
        ("default", "s1", "user", "crm szansa traktory widzisz?", "2026-06-25 20:30"),
        ("default", "s1", "assistant", "Zmieniłem nazwę na Traktory 200", "2026-06-25 20:58"),
        ("myodooTest", "s2", "user", "jak naprawić błąd autoryzacji do odoo", "2026-06-26 08:21"),
    ]
    con.executemany(
        "INSERT INTO chat_messages(workspace_id,session_id,role,content,created_at) "
        "VALUES (?,?,?,?,?)",
        rows,
    )
    con.commit()
    con.close()
    return path


def test_fts_query_sanitizes_special_chars():
    # cudzysłowy/gwiazdki/operatory nie mogą wysadzić składni FTS ani wstrzyknąć
    q = ms._fts_query('traktory" OR 1=1 -- *:')
    assert '"traktory"' in q
    assert "1=1" not in q  # samotne '1','=' odfiltrowane (tokeny ≥2 znaki słowne)
    assert q.count('"') % 2 == 0  # cudzysłowy zbalansowane


def test_fts_query_empty():
    assert ms._fts_query("") == ""
    assert ms._fts_query("...  !! ?") == ""


def test_reindex_and_search_chat(db):
    hits = ms.search_memory("traktory", limit=5, db_path=db)
    assert hits, "powinien znaleźć rozmowę o traktory"
    assert any(h["source"] == "chat" for h in hits)
    assert any("traktor" in (h.get("snip", "")).lower() for h in hits)


def test_search_respects_workspace_filter(db):
    # Izolacja dotyczy CZATÓW (prywatne per przestrzeń); sprinty/wiedza są globalne.
    # 'traktory' jest w czatach workspace 'default' — skanując myodooTest, ŻADEN
    # CHAT o traktory nie może wyciec (sprinty globalne wzmiankujące traktory są OK).
    hits = ms.search_memory("traktory", limit=8, workspace_id="myodooTest", db_path=db)
    assert not any(h["source"] == "chat" for h in hits), "czat z obcej przestrzeni wyciekł"
    # a w 'default' ten czat JEST widoczny
    hits_def = ms.search_memory("traktory", limit=8, workspace_id="default", db_path=db)
    assert any(h["source"] == "chat" for h in hits_def)


def test_search_includes_sprints(db):
    # sprinty czytane z repo (docs/sprints/*.md) — szukamy hasła z realnego sprintu
    hits = ms.search_memory("shadow mode propozycja", limit=8, db_path=db)
    assert any(h["source"] == "sprint" for h in hits), "powinien sięgnąć do sprintów"


def test_format_hits_empty():
    assert "Brak trafień" in ms.format_hits([])


def test_search_history_tool(db, monkeypatch):
    # tool używa domyślnej bazy → wskaż na tymczasową przez DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    from smartmyodoo.swarm.tools import TOOL_REGISTRY

    out = TOOL_REGISTRY["search_history"]["callable"](query="traktory")
    assert "traktor" in out.lower()
    assert "pamięci" in out.lower() or "rozmowa" in out.lower()
